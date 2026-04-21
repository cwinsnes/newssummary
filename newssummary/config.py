import yaml
from pathlib import Path
from typing import cast


class ConfigError(Exception):
    pass


ENGLISH_CATEGORY_KEYWORDS = {
    "Politics": {
        "parliament", "government", "minister", "president", "election", "vote", "bill", "law",
        "policy", "constitutional", "political", "democracy", "senate", "congress", "mp", "cabinet"
    },
    "Society & Justice": {
        "court", "police", "crime", "justice", "prison", "investigation", "lawsuit", "judge",
        "assault", "victim", "abuse", "rights", "protest", "strike", "activism", "incident", "arrest"
    },
    "Sports": {
        "football", "soccer", "match", "win", "player", "tournament", "cup", "league", "olympics",
        "nba", "golf", "tennis", "snooker", "cricket", "rugby", "athletics", "goal", "stadium", "racing"
    },
    "Business & Economy": {
        "economy", "market", "stock", "bank", "company", "startup", "investment", "inflation",
        "finance", "trade", "billion", "million", "dollar", "pound", "profit", "shares", "industry"
    },
    "Technology & Science": {
        "technology", "software", "ai", "artificial", "space", "nasa", "digital", "internet", 
        "computer", "robot", "robotics", "programming", "developer", "silicon", "innovation", "tech"
    },
    "Lifestyle & Culture": {
        "movie", "film", "music", "singer", "actor", "art", "theatre", "culture", "celebrity",
        "tv", "oscar", "festival", "hollywood", "album", "concert", "fashion", "travel", "food", "style"
    },
    "Health": {
        "medical", "hospital", "disease", "health", "doctor", "virus", "patient", "medicine",
        "vaccine", "cancer", "surgery", "clinic", "mental"
    },
    "Environment": {
        "climate", "environment", "nature", "sea", "ocean", "animal", "pollution", "recycling",
        "earth", "energy", "carbon", "warming", "wildlife", "green"
    }
}


def load_config(config_path: Path = Path("config.yaml")) -> list[dict[str, str]]:
    with config_path.open() as f:
        return cast(list[dict[str, str]], yaml.safe_load(f))
