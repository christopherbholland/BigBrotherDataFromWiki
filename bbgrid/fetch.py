"""Step 1: fetch rendered page HTML from the MediaWiki parse API into cache/.

This is the only module that touches the network. Everything downstream reads
cache/ only; refetching is an explicit command (`python -m bbgrid fetch`).
"""
import json
from datetime import datetime, timezone

import requests

from .config import CACHE_DIR

API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = (
    "BigBrotherWeekGrid/0.1 "
    "(https://github.com/christopherbholland/BigBrotherDataFromWiki; batch visualization pipeline)"
)


def cache_paths(season, cache_dir=CACHE_DIR):
    return cache_dir / f"bb{season}.html", cache_dir / f"bb{season}.meta.json"


def fetch_page(title, session=None):
    """Return (html, revid) for a page title."""
    session = session or requests.Session()
    resp = session.get(
        API_URL,
        params={
            "action": "parse",
            "page": title,
            "prop": "text|revid",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"{title}: {data['error'].get('info', data['error'])}")
    parse = data["parse"]
    return parse["text"], parse["revid"]


def fetch_season(season, title, cache_dir=CACHE_DIR, session=None):
    html, revid = fetch_page(title, session=session)
    cache_dir.mkdir(parents=True, exist_ok=True)
    html_path, meta_path = cache_paths(season, cache_dir)
    html_path.write_text(html, encoding="utf-8")
    meta = {
        "season": season,
        "title": title,
        "revid": revid,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def load_cached(season, cache_dir=CACHE_DIR):
    """Return (html, meta) from the cache, or None if the season isn't cached."""
    html_path, meta_path = cache_paths(season, cache_dir)
    if not html_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return html_path.read_text(encoding="utf-8"), meta
