"""Season list and shared paths."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
FANDOM_CACHE_DIR = CACHE_DIR / "fandom"
SEASONS_FILE = ROOT / "seasons.yaml"
WEB_DIR = ROOT / "web"

FANDOM_BASE = "https://bigbrother.fandom.com"


def _load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seasons(path=SEASONS_FILE):
    """Return {season_number: Wikipedia page title}, sorted by season."""
    return {int(k): v for k, v in sorted(_load(path)["seasons"].items())}


def load_fandom_seasons(path=SEASONS_FILE):
    """Return {season_number: Big Brother Wiki page title}; empty if the file has no fandom list."""
    return {int(k): v for k, v in sorted((_load(path).get("fandom") or {}).items())}


def page_url(title):
    return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")


def fandom_url(title):
    return f"{FANDOM_BASE}/wiki/" + title.replace(" ", "_")


def fandom_permalink(revid):
    return f"{FANDOM_BASE}/?oldid={revid}"
