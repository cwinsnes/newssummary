import feedparser
import trafilatura
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import cast, List
from newssummary.cache import disk_cache
from newssummary.models import Article, NewsSource, FeedResult, FeedEntry, Settings, ScrapedEntry


@disk_cache
def fetch_article_text(url: str) -> tuple[int, str]:
    downloaded = trafilatura.fetch_url(url)

    content = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        include_links=False,
        include_images=False,
        fast=True,
    )
    num_paragraphs = len(content.split("\n")) if content else 0

    return num_paragraphs, content or ""


def clean_title(title: str) -> str:
    # Remove multiple newlines and spaces
    title = re.sub(r"\s+", " ", title).strip()
    # Remove common prefixes like "JUST NU:", "Analys:", etc.
    title = re.sub(
        r"^(JUST NU|ANALYS|KOMMENTAR|REPORTAGE|DEBATT|INTERVJU|PODD|TV|VIDEO)[:\s]+",
        "",
        title,
        flags=re.IGNORECASE,
    )
    # Remove timestamps like "08:49"
    title = re.sub(r"^\d{1,2}:\d{2}\s*", "", title)
    # Remove duration like "(39:08)"
    title = re.sub(r"\s*\(\d{1,2}:\d{2}\)$", "", title)
    return title.strip()


def discover_links(url: str) -> List[FeedEntry]:
    # 1. Try to find actual feeds
    from trafilatura.feeds import find_feed_urls

    feed_urls = find_feed_urls(url)
    if feed_urls:
        for feed_url in feed_urls:
            res = feedparser.parse(feed_url)
            if res.entries:
                return res.entries

    # 2. Scrape the page for links
    html = trafilatura.fetch_url(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    entries: List[FeedEntry] = []
    seen_urls = set()

    # Common junk patterns
    junk_words = {
        "privacy",
        "contact",
        "about",
        "terms",
        "cookies",
        "subscribe",
        "login",
        "register",
        "search",
        "faq",
        "advertis",
    }

    for a in soup.find_all("a", href=True):
        link = urljoin(url, a["href"])
        text = a.get_text(" ", strip=True)  # Use space separator for nested tags

        if link in seen_urls:
            continue

        # Heuristics:
        # - Link text has at least 4 words
        # - No junk words in text or URL
        if (
            len(text.split()) >= 4
            and not any(word in text.lower() for word in junk_words)
            and not any(word in link.lower() for word in junk_words)
        ):
            title = clean_title(text)
            if (
                len(title.split()) >= 3
            ):  # Ensure we still have a decent title after cleaning
                entries.append(ScrapedEntry(title=title, link=link))
                seen_urls.add(link)

    print(f"Discovered {len(entries)} potential articles via scraping.")
    return entries


def scrape_with_selectors(source: NewsSource) -> List[FeedEntry]:
    html = trafilatura.fetch_url(source.url)
    if not html or not source.selectors:
        return []

    soup = BeautifulSoup(html, "html.parser")
    entries: List[FeedEntry] = []
    
    for item in soup.select(source.selectors.item):
        title_el = item.select_one(source.selectors.title)
        link_el = item.select_one(source.selectors.link)
        
        if title_el and link_el and link_el.get("href"):
            title = clean_title(title_el.get_text(" ", strip=True))
            link = urljoin(source.url, link_el["href"])
            entries.append(ScrapedEntry(title=title, link=link))
            
    print(f"Scraped {len(entries)} articles using manual selectors for {source.name}.")
    return entries


def fetch_articles(source: NewsSource, settings: Settings) -> List[Article]:
    # 0. Manual selectors take precedence if provided
    if source.selectors:
        entries = scrape_with_selectors(source)
    else:
        result = cast(FeedResult, feedparser.parse(source.url))
        entries = result.entries

    if not entries:
        print(f"No direct RSS found for {source.url}, trying automatic discovery...")
        entries = discover_links(source.url)

    if not isinstance(entries, list) or not entries:
        return []

    valid_entries = []
    seen_urls = set()
    for entry in entries:
        if entry.link in seen_urls:
            continue
        try:
            if entry.published_parsed and entry.published_parsed < (
                datetime.now() - timedelta(days=1)
            ).timetuple():
                continue
        except Exception:
            pass  # If published_parsed is missing or malformed, we still want to process it
        valid_entries.append(entry)
        seen_urls.add(entry.link)

    articles: List[Article] = []

    def process_entry(entry: FeedEntry) -> Article | None:
        _, article_text = fetch_article_text(entry.link)
        if article_text:
            return Article(
                title=entry.title,
                url=entry.link,
                raw_text=article_text,
                language=source.language,
                source_name=source.name,
                settings=settings,
            )
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(process_entry, valid_entries)
        for art in results:
            if art:
                articles.append(art)

    return articles
