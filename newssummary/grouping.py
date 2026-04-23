import collections
from typing import List, Set, Dict
from newssummary.models import Article
from newssummary.nlp import Tokenizer, extract_keywords_from_text


def _get_sentences(text: str, language: str) -> List[str]:
    """Simple sentence splitter using sumy's tokenizer logic."""
    try:
        tokenizer = Tokenizer(language)
        return [s.strip() for s in tokenizer.to_sentences(text) if len(s.strip()) > 20]
    except Exception:
        # Fallback to simple split if language is unknown
        return [s.strip() for s in text.split(".") if len(s.strip()) > 20]


def group_articles(
    articles: List[Article], threshold: float = 0.15
) -> List[List[Article]]:
    """
    Cluster articles using Title-Weighted Jaccard similarity and boilerplate phrase detection.
    """
    if not articles:
        return []

    # 1. Identify Global Boilerplate Phrases
    # We look for identical sentences across different articles
    sentence_counts: Dict[str, int] = collections.defaultdict(int)
    for art in articles:
        sentences = set(_get_sentences(art.summary, art.language))
        for s in sentences:
            sentence_counts[s] += 1

    # Sentences that appear in more than 2 articles are likely boilerplate
    boilerplate_phrases = {s for s, count in sentence_counts.items() if count > 2}

    # 2. Extract Boilerplate Keywords to ignore
    noise_keywords: Set[str] = set()
    for art in articles:
        sentences = _get_sentences(art.summary, art.language)
        for s in sentences:
            if s in boilerplate_phrases:
                # We identify which keywords came from these noise phrases
                noise_keywords.update(extract_keywords_from_text(s, art.language))

    clusters: List[List[Article]] = []

    for article in articles:
        found_cluster = False

        # Filter noise from the current article's keywords
        # We use English keywords for cross-language comparison
        art_title_keys = article.english_title_keywords
        art_all_keys = article.english_keywords - noise_keywords

        for cluster in clusters:
            rep = cluster[0]
            rep_title_keys = rep.english_title_keywords
            rep_all_keys = rep.english_keywords - noise_keywords

            # Calculate Weighted Similarity
            # Title overlap is a strong signal (weight = 5)
            title_intersection = art_title_keys.intersection(rep_title_keys)
            title_union = art_title_keys.union(rep_title_keys)

            # Smart Substring Match for Titles (e.g., Swedish compounds)
            # If no exact match, check if one word is a substring of another
            title_match_count = len(title_intersection)
            if title_match_count == 0:
                for ak in art_title_keys:
                    for rk in rep_title_keys:
                        if (len(ak) > 4 and ak in rk) or (len(rk) > 4 and rk in ak):
                            title_match_count = 0.5
                            break
                    if title_match_count > 0:
                        break

            # Content overlap is a weak signal (weight = 1)
            content_intersection = art_all_keys.intersection(rep_all_keys)
            content_union = art_all_keys.union(rep_all_keys)

            # Weighted Jaccard
            weighted_intersection = (title_match_count * 5) + len(content_intersection)
            weighted_union = (len(title_union) * 5) + len(content_union)

            similarity = weighted_intersection / weighted_union if weighted_union else 0

            # Prerequisite: Unless similarity is very high, they MUST share at least a partial title match
            # This prevents boilerplate-only groupings.
            if similarity >= threshold:
                if title_match_count > 0 or similarity > 0.4:
                    cluster.append(article)
                    found_cluster = True
                    break

        if not found_cluster:
            clusters.append([article])

    return clusters
