"""Season list and shared paths."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
SEASONS_FILE = ROOT / "seasons.yaml"
WEB_DIR = ROOT / "web"


def load_seasons(path=SEASONS_FILE):
    """Return {season_number: page_title}, sorted by season."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {int(k): v for k, v in sorted(data["seasons"].items())}


def page_url(title):
    return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
