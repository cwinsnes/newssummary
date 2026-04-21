import logging
from typing import Any, Dict, Set, cast

import argostranslate.package
import argostranslate.translate
from sumy.nlp.stemmers import Stemmer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.utils import get_stop_words

from newssummary.config import ENGLISH_CATEGORY_KEYWORDS
from newssummary.cache import disk_cache

# Map full language names from config/sumy to ISO 639-1 codes for Argos Translate
LANGUAGE_MAPPING = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "swedish": "sv",
    "italian": "it",
    "portuguese": "pt",
    "chinese": "zh",
    "russian": "ru",
    "japanese": "ja",
}

def _ensure_argos_package(from_code: str, to_code: str):
    """
    Ensures that the required Argos Translate package is installed.
    """
    from_code = from_code.lower()
    to_code = to_code.lower()

    # Check if already installed
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = next(filter(lambda x: x.code == from_code, installed_languages), None)
    to_lang = next(filter(lambda x: x.code == to_code, installed_languages), None)

    if from_lang and to_lang:
        translation = from_lang.get_translation(to_lang)
        if translation:
            return

    # If not installed, update index and download
    logging.info(f"Installing Argos Translate package for {from_code} -> {to_code}...")
    try:
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()
        package_to_install = next(
            filter(
                lambda x: x.from_code == from_code and x.to_code == to_code,
                available_packages,
            ),
            None
        )
        if package_to_install:
            argostranslate.package.install_from_path(package_to_install.download())
            logging.info(f"Successfully installed translation package.")
        else:
            logging.warning(f"No Argos Translate package found for {from_code} -> {to_code}")
    except Exception as e:
        logging.error(f"Failed to install Argos Translate package: {e}")

@disk_cache
def _translate_text_blob(text: str, from_language: str) -> str:
    """
    Translates a full string of text using Argos Translate.
    """
    if not text.strip():
        return ""

    from_code = LANGUAGE_MAPPING.get(from_language.lower(), from_language.lower()[:2])
    to_code = "en"

    if from_code == to_code:
        return text

    try:
        _ensure_argos_package(from_code, to_code)
        return argostranslate.translate.translate(text, from_code, to_code)
    except Exception as e:
        print(f"Warning: Failed to translate text blob from {from_language}: {e}")
        return ""

@disk_cache
def _translate_keywords(words_to_translate: list[str], from_language: str) -> list[str]:
    """
    Specifically cache the translation of keywords using offline Argos Translate.
    """
    if not words_to_translate:
        return []

    from_code = LANGUAGE_MAPPING.get(from_language.lower(), from_language.lower()[:2])
    to_code = "en"

    if from_code == to_code:
        return words_to_translate

    try:
        _ensure_argos_package(from_code, to_code)
        text_to_translate = " | ".join(words_to_translate)
        result = argostranslate.translate.translate(text_to_translate, from_code, to_code)
        if result:
            return [w.strip().lower() for w in result.split("|")]
    except Exception as e:
        print(f"Warning: Failed to translate keywords from {from_language} using Argos: {e}")

    return []

@disk_cache
def extract_keywords_from_text(text: str, language: str) -> Set[str]:
    """
    Extracts stemmed keywords from a specific string.
    """
    if not text:
        return set()

    tokenizer = Tokenizer(language)
    stemmer = Stemmer(language)
    try:
        stop_words = set(get_stop_words(language))
    except Exception:
        stop_words = set()

    raw_words = tokenizer.to_words(text.lower())
    return {
        stemmer(w) for w in raw_words if len(w) >= 3 and w not in stop_words
    }

@disk_cache
def summarize(text: str, language: str) -> str:
    if not text.strip():
        return ""

    parser = PlaintextParser.from_string(text, Tokenizer(language))
    total_sentences = len(parser.document.sentences)

    # Smart summarization: adjust ratio based on content length
    num_sentences = total_sentences if total_sentences <= 5 else 4
    summarizer = TextRankSummarizer()
    summary_sentences = summarizer(parser.document, sentences_count=num_sentences)
    return " ".join(str(sentence) for sentence in summary_sentences)

@disk_cache
def get_english_keywords(title: str, summary: str, language: str) -> Set[str]:
    # Extract keywords using language-specific tokenizer, stop words, and stemmer
    tokenizer = Tokenizer(language)
    stemmer = Stemmer(language)

    try:
        stop_words = set(get_stop_words(language))
    except Exception:
        try:
            stop_words = set(get_stop_words("english"))
        except Exception:
            stop_words = set()

    text = f"{title} {summary}".lower()
    raw_words = tokenizer.to_words(text)

    # Original language stemmed keywords
    original_keywords = {
        stemmer(w) for w in raw_words if len(w) >= 3 and w not in stop_words
    }

    if language.lower() == "english":
        return original_keywords

    # Translate keywords to English to enable grouping and categorization across languages
    words_to_translate = sorted(list(original_keywords), key=len, reverse=True)[:40]
    english_words = _translate_keywords(words_to_translate, language)

    if english_words:
        en_stemmer = Stemmer("english")
        en_keywords = {en_stemmer(w) for w in english_words}
        # For English-translated keywords, we also keep proper nouns from original
        return en_keywords.union({w for w in original_keywords if w[0].isupper()})

    return original_keywords

def get_keywords(
    title: str, summary: str, language: str, en_keywords: Set[str]
) -> Set[str]:
    tokenizer = Tokenizer(language)
    stemmer = Stemmer(language)
    try:
        stop_words = set(get_stop_words(language))
    except Exception:
        stop_words = set()

    text = f"{title} {summary}".lower()
    raw_words = tokenizer.to_words(text)
    original_keywords = {
        stemmer(w) for w in raw_words if len(w) >= 3 and w not in stop_words
    }

    if language.lower() == "english":
        return original_keywords

    return original_keywords.union(en_keywords)

@disk_cache
def get_category(en_keywords: Set[str]) -> str:
    en_stemmer = Stemmer("english")

    scores: Dict[str, int] = {}
    for cat, keywords in ENGLISH_CATEGORY_KEYWORDS.items():
        # Stem category keywords for better matching
        stemmed_cat_keywords = {en_stemmer(w) for w in keywords}
        score = len(en_keywords.intersection(stemmed_cat_keywords))
        if score > 0:
            scores[cat] = score

    if not scores:
        return "World News"

    return max(scores, key=cast(Any, scores.get))
