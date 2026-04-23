from dataclasses import dataclass
import yaml
from pathlib import Path
from typing import cast, Dict, Any, List


class ConfigError(Exception):
    pass


@dataclass
class Settings:
    summary_length: str = "medium"
    reading_speed_wpm: int = 200

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        return cls(
            summary_length=data.get("summary_length", "medium"),
            reading_speed_wpm=data.get("reading_speed_wpm", 200),
        )


ENGLISH_CATEGORY_KEYWORDS = {
    "Politics": {
        "parliament",
        "government",
        "minister",
        "president",
        "election",
        "vote",
        "bill",
        "law",
        "policy",
        "constitutional",
        "political",
        "democracy",
        "senate",
        "congress",
        "mp",
        "cabinet",
    },
    "Society & Justice": {
        "court",
        "police",
        "crime",
        "justice",
        "prison",
        "investigation",
        "lawsuit",
        "judge",
        "assault",
        "victim",
        "abuse",
        "rights",
        "protest",
        "strike",
        "activism",
        "incident",
        "arrest",
    },
    "Sports": {
        "football",
        "soccer",
        "match",
        "win",
        "player",
        "tournament",
        "cup",
        "league",
        "olympics",
        "nba",
        "golf",
        "tennis",
        "snooker",
        "cricket",
        "rugby",
        "athletics",
        "goal",
        "stadium",
        "racing",
    },
    "Business & Economy": {
        "economy",
        "market",
        "stock",
        "bank",
        "company",
        "startup",
        "investment",
        "inflation",
        "finance",
        "trade",
        "billion",
        "million",
        "dollar",
        "pound",
        "profit",
        "shares",
        "industry",
    },
    "Technology & Science": {
        "technology",
        "software",
        "ai",
        "artificial",
        "space",
        "nasa",
        "digital",
        "internet",
        "computer",
        "robot",
        "robotics",
        "programming",
        "developer",
        "silicon",
        "innovation",
        "tech",
    },
    "Lifestyle & Culture": {
        "movie",
        "film",
        "music",
        "singer",
        "actor",
        "art",
        "theatre",
        "culture",
        "celebrity",
        "tv",
        "oscar",
        "festival",
        "hollywood",
        "album",
        "concert",
        "fashion",
        "travel",
        "food",
        "style",
    },
    "Health": {
        "medical",
        "hospital",
        "disease",
        "health",
        "doctor",
        "virus",
        "patient",
        "medicine",
        "vaccine",
        "cancer",
        "surgery",
        "clinic",
        "mental",
    },
    "Environment": {
        "climate",
        "environment",
        "nature",
        "sea",
        "ocean",
        "animal",
        "pollution",
        "recycling",
        "earth",
        "energy",
        "carbon",
        "warming",
        "wildlife",
        "green",
    },
}


def load_config(
    config_path: Path = Path("config.yaml"),
) -> tuple[Settings, List[Dict[str, str]]]:
    with config_path.open() as f:
        data = yaml.safe_load(f)

    if isinstance(data, list):
        # Backward compatibility: only sources list
        return Settings(), cast(List[Dict[str, str]], data)

    settings = Settings.from_dict(data.get("settings", {}))
    sources = cast(List[Dict[str, str]], data.get("sources", []))
    return settings, sources
