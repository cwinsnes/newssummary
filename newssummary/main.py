import collections
from typing import List

from newssummary.config import load_config
from newssummary.fetcher import fetch_articles
from newssummary.grouping import group_articles
from newssummary.models import Article, NewsSource
from newssummary.generator import generate_digest


def main() -> None:
    config_data = load_config()
    sources = [NewsSource.from_yaml(item) for item in config_data]
    all_articles: List[Article] = []

    for source in sources:
        print(f"Fetching from {source.name}...")
        all_articles.extend(fetch_articles(source))

    if not all_articles:
        print("No recent articles found.")
        return

    # 1. Fine-grained clustering
    clusters = group_articles(all_articles)

    # 2. Separate into Elevated Topics (size > 1) and Standalone Articles
    elevated_topics = [c for c in clusters if len(c) > 1]
    standalone_articles = [c[0] for c in clusters if len(c) == 1]

    # 3. Group standalones by broad category
    broad_groups = collections.defaultdict(list)
    for art in standalone_articles:
        broad_groups[art.category].append(art)

    # Generate HTML Digest
    index_path = generate_digest(all_articles, elevated_topics, broad_groups)
    
    print(f"\n{'#'*80}")
    print(f"### DIGEST GENERATED SUCCESSFULLY")
    print(f"{'#'*80}")
    print(f"View your news here: file://{index_path.absolute()}")
    print(f"{'#'*80}\n")


if __name__ == "__main__":
    main()
