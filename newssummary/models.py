import time
from dataclasses import dataclass, field
from functools import cached_property
from typing import List, Protocol, Self, Set, Optional
from .config import ConfigError, Settings
from . import nlp


class FeedEntry(Protocol):
    title: str
    link: str
    published_parsed: time.struct_time


class FeedResult(Protocol):
    entries: List[FeedEntry]


@dataclass
class ScrapedEntry:
    title: str
    link: str
    published_parsed: time.struct_time | None = None


@dataclass
class Selectors:
    item: str
    title: str
    link: str

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> Self:
        return cls(
            item=data["item"],
            title=data["title"],
            link=data["link"],
        )


@dataclass
class NewsSource:
    name: str
    url: str
    language: str
    selectors: Optional[Selectors] = None

    @classmethod
    def from_yaml(cls, data: dict[str, any]) -> Self:
        try:
            selectors = None
            if "selectors" in data:
                selectors = Selectors.from_dict(data["selectors"])

            return cls(
                name=data["source"],
                url=data["url"],
                language=data["language"],
                selectors=selectors,
            )
        except KeyError as e:
            raise ConfigError(f"Missing required field in config: {e}")


@dataclass
class Article:
    title: str
    url: str
    raw_text: str
    language: str
    source_name: str = "Unknown"
    settings: Settings = field(default_factory=Settings)

    def __bool__(self) -> bool:
        return bool(self.raw_text.strip())

    @cached_property
    def summary(self) -> str:
        return nlp.summarize(self.raw_text, self.language, self.settings.summary_length)

    @cached_property
    def reading_time(self) -> int:
        words = len(self.raw_text.split())
        return max(1, round(words / self.settings.reading_speed_wpm))

    @cached_property
    def title_keywords(self) -> Set[str]:
        return nlp.extract_keywords_from_text(self.title, self.language)

    @cached_property
    def english_title_keywords(self) -> Set[str]:
        if self.language.lower() == "english":
            return self.title_keywords

        # Translate the whole title for context-aware keyword translation
        translated_title = nlp._translate_text_blob(self.title, self.language)
        if not translated_title:
            return self.title_keywords

        return nlp.extract_keywords_from_text(translated_title, "english")

    @cached_property
    def english_keywords(self) -> Set[str]:
        return nlp.get_english_keywords(self.title, self.summary, self.language)

    @cached_property
    def keywords(self) -> Set[str]:
        return nlp.get_keywords(
            self.title, self.summary, self.language, self.english_keywords
        )

    @cached_property
    def category(self) -> str:
        return nlp.get_category(self.english_keywords, self.english_title_keywords)
