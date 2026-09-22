"""Step 1: fetch pages from the MediaWiki API into cache/.

This is the only module that touches the network. Everything downstream reads
cache/ only; refetching is an explicit command (`python -m bbgrid fetch`).

Two wikis, both MediaWiki:
  Wikipedia          cache/bbNN.html + bbNN.meta.json (the grid's source)
  Big Brother Wiki   cache/fandom/bbNN.html, .wikitext, .meta.json, and
                     .houseguests.json (the lead section of each houseguest's page)
"""
import json
import time
from datetime import datetime, timezone

import requests

from .config import CACHE_DIR, FANDOM_CACHE_DIR

API_URL = "https://en.wikipedia.org/w/api.php"
FANDOM_API_URL = "https://bigbrother.fandom.com/api.php"
USER_AGENT = (
    "BigBrotherWeekGrid/0.1 "
    "(https://github.com/christopherbholland/BigBrotherDataFromWiki; batch visualization pipeline)"
)
TITLES_PER_QUERY = 50  # the API's limit for revision content of several pages
PAUSE = 0.5  # seconds between Fandom requests, to stay polite


def cache_paths(season, cache_dir=CACHE_DIR):
    return cache_dir / f"bb{season}.html", cache_dir / f"bb{season}.meta.json"


def _api(session, url, params):
    resp = session.get(
        url,
        params={**params, "format": "json", "formatversion": "2"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("info", data["error"]))
    return data


def fetch_page(title, session=None, api_url=API_URL, wikitext=False):
    """Return (html, revid), or (html, revid, wikitext) when wikitext=True."""
    session = session or requests.Session()
    prop = "text|revid" + ("|wikitext" if wikitext else "")
    try:
        data = _api(session, api_url, {"action": "parse", "page": title, "prop": prop, "redirects": "1"})
    except RuntimeError as e:
        raise RuntimeError(f"{title}: {e}") from None
    parse = data["parse"]
    if wikitext:
        return parse["text"], parse["revid"], parse["wikitext"]
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


# --- Big Brother Wiki (Fandom) ---------------------------------------------

def fandom_paths(season, cache_dir=FANDOM_CACHE_DIR):
    base = cache_dir / f"bb{season}"
    return {
        "html": base.with_suffix(".html"),
        "wikitext": base.with_suffix(".wikitext"),
        "meta": base.with_suffix(".meta.json"),
        "houseguests": base.with_suffix(".houseguests.json"),
    }


def lead_section(wikitext):
    """Everything before the first section heading: the infobox and opening paragraph."""
    for i, line in enumerate(wikitext.split("\n")):
        if line.startswith("==") and line.rstrip().endswith("=="):
            return "\n".join(wikitext.split("\n")[:i]).rstrip() + "\n"
    return wikitext


def fetch_leads(titles, session=None, api_url=FANDOM_API_URL):
    """{title: {"revid", "lead"}} for each page, following redirects.

    A title that doesn't exist is left out; the caller reports it.
    """
    session = session or requests.Session()
    out = {}
    titles = sorted(set(titles))
    for i in range(0, len(titles), TITLES_PER_QUERY):
        chunk = titles[i:i + TITLES_PER_QUERY]
        data = _api(session, api_url, {
            "action": "query", "titles": "|".join(chunk), "redirects": "1",
            "prop": "revisions", "rvprop": "content|ids", "rvslots": "main",
        })["query"]
        # Report results under the title that was asked for.
        asked = {t: t for t in chunk}
        for step in ("normalized", "redirects"):
            for m in data.get(step, []):
                for k, v in list(asked.items()):
                    if v == m["from"]:
                        asked[k] = m["to"]
        by_title = {p["title"]: p for p in data.get("pages", []) if p.get("revisions")}
        for want, got in asked.items():
            page = by_title.get(got)
            if page:
                rev = page["revisions"][0]
                out[want] = {"title": got, "revid": rev["revid"], "lead": lead_section(rev["slots"]["main"]["content"])}
        time.sleep(PAUSE)
    return out


def fetch_fandom_season(season, title, cache_dir=FANDOM_CACHE_DIR, session=None):
    """Fetch a season's Big Brother Wiki page, then its houseguests' pages."""
    from .fandom import houseguest_links  # parsing lives in fandom.py

    session = session or requests.Session()
    html, revid, wikitext = fetch_page(title, session=session, api_url=FANDOM_API_URL, wikitext=True)
    time.sleep(PAUSE)
    links = houseguest_links(html)
    leads = fetch_leads([t for t, _ in links], session=session)
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = fandom_paths(season, cache_dir)
    paths["html"].write_text(html, encoding="utf-8")
    paths["wikitext"].write_text(wikitext, encoding="utf-8")
    paths["houseguests"].write_text(json.dumps(leads, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                                    encoding="utf-8")
    meta = {
        "season": season,
        "title": title,
        "revid": revid,
        "houseguest_pages": len(leads),
        "missing_pages": sorted(t for t, _ in links if t not in leads),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    paths["meta"].write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def load_fandom_cached(season, cache_dir=FANDOM_CACHE_DIR):
    """Return {"html", "wikitext", "houseguests", "meta"}, or None if the season isn't cached."""
    paths = fandom_paths(season, cache_dir)
    if not paths["html"].exists():
        return None

    def read(key, default):
        p = paths[key]
        return p.read_text(encoding="utf-8") if p.exists() else default
    return {
        "html": read("html", ""),
        "wikitext": read("wikitext", ""),
        "houseguests": json.loads(read("houseguests", "{}")),
        "meta": json.loads(read("meta", "{}")),
    }
