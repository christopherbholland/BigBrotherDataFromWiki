"""Season list and shared paths."""
from pathlib import Path
from urllib.parse import quote

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


def season_numbers(spec):
    """Season numbers from seasons.yaml's `seasons`: "21-28", 26, or a list of those."""
    items = spec if isinstance(spec, list) else [spec]
    out = set()
    for item in items:
        if isinstance(item, int):
            out.add(item)
            continue
        first, sep, last = str(item).partition("-")
        if not (first.strip().isdigit() and (not sep or last.strip().isdigit())):
            raise ValueError(f"seasons.yaml: can't read season {item!r}; use a number or a range like 21-28")
        out.update(range(int(first), int(last if sep else first) + 1))
    return sorted(out)


def _titles(config, wiki):
    """{season: page title} for one wiki: the title pattern for each season, then its exceptions.

    A season can be left out of one wiki with an exception of null.
    """
    pattern = (config.get("titles") or {}).get(wiki)
    exceptions = {int(k): v for k, v in ((config.get("exceptions") or {}).get(wiki) or {}).items()}
    out = {}
    for n in season_numbers(config["seasons"]):
        title = exceptions[n] if n in exceptions else (pattern.format(n=n) if pattern else None)
        if title:
            out[n] = title
    return out


def load_seasons(path=SEASONS_FILE):
    """Return {season_number: Wikipedia page title}, sorted by season."""
    return _titles(_load(path), "wikipedia")


def load_fandom_seasons(path=SEASONS_FILE):
    """Return {season_number: Big Brother Wiki page title}, sorted by season."""
    return _titles(_load(path), "fandom")


def page_url(title):
    return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")


def page_permalink(revid):
    return f"https://en.wikipedia.org/w/index.php?oldid={revid}"


def fandom_url(title):
    # "?" and "#" occur in titles ("What Did They Just Do?") and must be escaped.
    return f"{FANDOM_BASE}/wiki/" + quote(title.replace(" ", "_"), safe="/:,()'!&$*+;=@")


def fandom_permalink(revid):
    return f"{FANDOM_BASE}/?oldid={revid}"
