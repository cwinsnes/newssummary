import feedparser
import trafilatura
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import cast, List
from newssummary.cache import disk_cache
from newssummary.models import Article, NewsSource, FeedResult, FeedEntry, Settings


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


def fetch_articles(source: NewsSource, settings: Settings) -> List[Article]:
    result = cast(FeedResult, feedparser.parse(source.url))
    entries = result.entries
    if not isinstance(entries, list):
        return []

    valid_entries = []
    seen_urls = set()
    for entry in entries:
        if entry.link in seen_urls:
            continue
        try:
            if (
                entry.published_parsed
                < (datetime.now() - timedelta(days=1)).timetuple()
            ):
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
