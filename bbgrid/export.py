"""Step 4b: run the pipeline over the cache and write weeks.json, details.json and report.txt.

run() is the whole build; the functions it calls can be used on their own
(process_season_full for one season's HTML, make_report for the report text).
"""
import json

from .afh import afh, check as check_afh
from .cast import bios
from .comps import CATEGORIES, CATEGORY_HELP, categorize, explains
from .config import (CACHE_DIR, FANDOM_CACHE_DIR, WEB_DIR, fandom_url, load_fandom_seasons, load_seasons,
                     page_permalink, page_url)
from .details import finale, players, week_details
from .enrich import enrich_season
from .episodes import episodes_by_week
from .fandom import parse_season as parse_fandom_season
from .fetch import load_cached, load_fandom_cached
from .grid import build_episode_grid, build_grid
from .interpret import houseguests, interpret
from .util import utc_now
from .validate import validate_week

# Written to weeks.json and details.json as "schema_version". Raised whenever a
# field is removed, renamed or changes meaning; adding a field doesn't change it.
SCHEMA_VERSION = 1

# See DATA_LICENSE.md. Big Brother Wiki text is CC BY-SA 3.0, whose adaptations may use 4.0.
LICENSE = ("CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/): adapted from Wikipedia "
           "(CC BY-SA 4.0) and the Big Brother Wiki, bigbrother.fandom.com (CC BY-SA 3.0); sources "
           "and revisions are listed in each file. Houseguest photos are CBS promotional images, "
           "linked from the Big Brother Wiki and not covered by this license.")

# Keys the interpreter adds to each round for the validator and details.py only.
INTERNAL_ROUND_KEYS = ("_vote_cells", "_voters", "_col")


def finalize(record):
    """Drop interpreter-internal keys; keep raw text only for note/error weeks."""
    raw = record.pop("_raw", None)
    record.pop("_finale", None)
    record["raw"] = raw if record["status"] != "ok" else None
    for rnd in record["rounds"]:
        for key in INTERNAL_ROUND_KEYS:
            rnd.pop(key, None)
    return record


def process_season(season, html):
    """Return the finished week records for one season's cached HTML."""
    return process_season_full(season, html)["weeks"]


def process_season_full(season, html):
    """Week records plus the detail-view data for one season.

    Returns {"weeks", "details", "players", "unmatched", "finale", "afh"}; see
    details.py and afh.py. Each player also gets "bio" from the cast table (see
    cast.py), or None.
    """
    grid = build_grid(html)
    records = interpret(grid, season)
    for record in records:
        validate_week(record)
    # Details need the interpreter's internal keys, so build them before finalize().
    episodes = episodes_by_week(build_episode_grid(html))
    detail = week_details(records, grid.notes, episodes)
    people, unmatched = players(season, records, houseguests(grid))
    # The season's last Finale column holds the jury vote.
    final = next((f for f in map(finale, reversed(records)) if f), None)
    # Age, occupation and hometown from the season's cast table.
    cast = bios(html, [p["name"] for p in people])
    for p in people:
        p["bio"] = cast.get(p["name"])
    favorite = afh(html, [(p["name"], (p["bio"] or {}).get("full_name")) for p in people],
                   [ep for eps in episodes.values() for ep in eps])
    return {
        "weeks": [finalize(r) for r in records],
        "details": detail,
        "players": people,
        "unmatched": unmatched,
        "finale": final,
        "afh": favorite,
    }


def _first_day(day):
    """The first day of a "Day" cell ("24", "31-32") as a number, for sorting; 0 if blank."""
    first = (day or "").split("-")[0]
    return int(first) if first.isdigit() else 0


def comp_index(details):
    """Categorize every HOH and veto competition in place; return the format index.

    Returns {format: {"url", "description", "category", "about", "plays": [...]}}, each play being
    {"season", "week", "kind", "name", "winners", "day", "category", "about"},
    oldest first. Competitions with no format are categorized but not indexed.
    """
    plays = []
    for key, d in details.items():
        season, week = key.split("|", 1)
        for c in (d.get("fandom") or {}).get("comps", []):
            if c["kind"] in ("hoh", "veto"):
                plays.append((int(season), week, c))
    categorize([c for _, _, c in plays])
    index = {}
    for season, week, c in plays:
        if not c["format"]:
            continue
        entry = index.setdefault(c["format"], {"url": fandom_url(c["format"]), "description": None, "plays": []})
        entry["description"] = entry["description"] or c.get("format_description")
        entry["plays"].append({"season": season, "week": week, "kind": c["kind"], "name": c["name"],
                               "winners": c["winners"], "day": c["day"], "category": c["category"],
                               "about": c["about"]})
    for entry in index.values():
        entry["plays"].sort(key=lambda p: (p["season"], _first_day(p["day"])))
        cats = [p["category"] for p in entry["plays"] if p["category"]]
        entry["category"] = max(set(cats), key=cats.count) if cats else None
        # The newest description that says how it's played, else the newest one.
        about = [p for p in entry["plays"] if p["about"]]
        best = ([p for p in about if explains(p["about"])] or about)[-1:]
        entry["about"] = {"text": best[0]["about"], "season": best[0]["season"], "week": best[0]["week"]} if best else None
    return dict(sorted(index.items(), key=lambda kv: kv[0].casefold()))


def photo_index(people):
    """{"28": {"Dee": headshot URL}}: each houseguest's Big Brother Wiki headshot,
    keyed by season and Wikipedia name, so the grid can show faces without details.json."""
    out = {}
    for p in people:
        url = (p.get("fandom") or {}).get("photo")
        if url:
            out.setdefault(str(p["season"]), {})[p["name"]] = url
    return dict(sorted(out.items(), key=lambda kv: -int(kv[0])))


def add_fandom(fandom_seasons, fandom_dir, sources, weeks, details, people, season_errors):
    """Merge each cached Big Brother Wiki season into details and players.

    Returns ({season: season info}, report lines). A season that isn't cached
    or fails to parse is reported; the Wikipedia data is unaffected.
    """
    seasons_info, lines = {}, []
    by_season = {s["season"]: s for s in sources}
    for season, title in fandom_seasons.items():
        if season not in by_season or "error" in by_season[season]:
            continue
        cached = load_fandom_cached(season, fandom_dir)
        if cached is None:
            lines.append(f"BB{season}: Big Brother Wiki page not in cache (run `python -m bbgrid fetch`)")
            continue
        try:
            data = parse_fandom_season(cached, season)
            info, report = enrich_season(season, data, {"title": title, **cached["meta"]},
                                         weeks, details, people)
        except Exception as e:  # Fandom problems never stop the Wikipedia build
            season_errors.append((season, f"Big Brother Wiki: {type(e).__name__}: {e}"))
            continue
        seasons_info[season] = info
        by_season[season]["fandom"] = {k: info[k] for k in ("title", "url", "revid", "permalink", "fetched_at")}
        lines.extend(report)
    return seasons_info, lines


def add_wikipedia(seasons, cache_dir):
    """Run the grid pipeline over each cached Wikipedia page.

    Returns {"sources", "weeks", "details", "players", "finales", "afh", "unmatched",
    "season_errors"}; finales and afh are by season as a string, afh None where the
    page names no favorite. A season that isn't cached or fails to parse is reported,
    not fatal.
    """
    out = {"sources": [], "weeks": [], "details": {}, "players": [], "finales": {}, "afh": {}, "unmatched": [],
           "season_errors": []}
    for season, title in seasons.items():
        cached = load_cached(season, cache_dir)
        source = {"season": season, "title": title, "url": page_url(title)}
        if cached is None:
            out["season_errors"].append((season, "not in cache (run `python -m bbgrid fetch`)"))
            out["sources"].append({**source, "error": "not fetched"})
            continue
        html, meta = cached
        source.update(revid=meta.get("revid"), fetched_at=meta.get("fetched_at"))
        if meta.get("revid"):
            source["permalink"] = page_permalink(meta["revid"])
        try:
            result = process_season_full(season, html)
            out["weeks"].extend(result["weeks"])
            out["details"].update(result["details"])
            out["players"].extend(result["players"])
            if result["finale"]:
                out["finales"][str(season)] = result["finale"]
            out["afh"][str(season)] = result["afh"]
            out["unmatched"].extend((season, name) for name in result["unmatched"])
        except Exception as e:  # a whole-season failure is reported, not fatal
            out["season_errors"].append((season, f"{type(e).__name__}: {e}"))
            source["error"] = str(e)
        out["sources"].append(source)
    return out


def add_afh(afh_by_season, finales, people):
    """Check each season's America's Favorite HouseGuest against the Big Brother Wiki's
    prize lists (people must have "fandom" by now; see add_fandom).

    Returns (the seasons that name a favorite, newest first; report lines).
    """
    named, lines = {}, []
    for season, result in afh_by_season.items():
        decided = (finales.get(season) or {}).get("decided", False)
        lines.extend(check_afh(season, result, [p for p in people if str(p["season"]) == season], decided))
        if result is not None:
            named[season] = result
    return dict(sorted(named.items(), key=lambda kv: -int(kv[0]))), lines


def write_json(path, doc, compact=False):
    """weeks.json is indented so its diffs are readable; details.json is compact to stay small."""
    text = json.dumps(doc, ensure_ascii=False, **({"separators": (",", ":")} if compact else {"indent": 1}))
    path.write_text(text + "\n", encoding="utf-8")


def run(seasons=None, cache_dir=CACHE_DIR, out_dir=WEB_DIR, fandom_seasons=None, fandom_dir=FANDOM_CACHE_DIR):
    """Build everything from the cache: out_dir/weeks.json, out_dir/details.json and
    report.txt beside out_dir. Returns (the weeks.json document, the report text)."""
    seasons = seasons or load_seasons()
    fandom_seasons = load_fandom_seasons() if fandom_seasons is None else fandom_seasons
    wiki = add_wikipedia(seasons, cache_dir)
    seasons_info, fandom_lines = add_fandom(
        {s: t for s, t in fandom_seasons.items() if s in seasons}, fandom_dir,
        wiki["sources"], wiki["weeks"], wiki["details"], wiki["players"], wiki["season_errors"])

    favorites, afh_lines = add_afh(wiki["afh"], wiki["finales"], wiki["players"])

    out_dir.mkdir(parents=True, exist_ok=True)
    header = {"schema_version": SCHEMA_VERSION, "generated_at": utc_now(), "license": LICENSE}
    doc = {**header, "sources": wiki["sources"], "weeks": wiki["weeks"], "photos": photo_index(wiki["players"])}
    write_json(out_dir / "weeks.json", doc)
    # Detail views load this separately, so the main grid stays light.
    formats = comp_index(wiki["details"])
    write_json(out_dir / "details.json", {
        **header,
        "seasons": {str(k): v for k, v in sorted(seasons_info.items())},
        "categories": [{"name": c, "help": CATEGORY_HELP[c]} for c in CATEGORIES],
        "formats": formats, "weeks": wiki["details"], "players": wiki["players"], "finales": wiki["finales"],
        "afh": favorites,
    }, compact=True)
    report = make_report(wiki["weeks"], wiki["season_errors"], wiki["unmatched"], fandom_lines + afh_lines)
    (out_dir.parent / "report.txt").write_text(report, encoding="utf-8")
    return doc, report


def make_report(weeks, season_errors, unmatched=(), fandom_lines=()):
    lines = []
    counts = {"ok": 0, "note": 0, "error": 0}
    for w in weeks:
        counts[w["status"]] += 1
    lines.append(f"{len(weeks)} weeks: {counts['ok']} ok, {counts['note']} note, {counts['error']} error")
    for season, msg in season_errors:
        lines.append(f"BB{season}: SEASON ERROR: {msg}")
    for season, name in unmatched:
        lines.append(f"BB{season}: name in a summary cell matches no houseguest row: {name!r}")
    if fandom_lines:
        lines.append("")
        lines.append(f"Big Brother Wiki (Fandom): {len(fandom_lines)} to check")
        lines.extend("  " + line for line in fandom_lines)
    lines.append("")
    for w in weeks:
        if w["status"] == "ok":
            continue
        lines.append(f"BB{w['season']} {w['week_label']}: {w['status'].upper()}: {w['note']}")
        if w["raw"]:
            lines.append("    columns: " + " | ".join(w["raw"]["columns"]))
            for row in w["raw"]["rows"]:
                cells = " | ".join(c.replace("\n", " / ") for c in row["cells"])
                lines.append(f"    {row['label']}: {cells}")
    return "\n".join(lines) + "\n"
