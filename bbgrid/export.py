"""Step 4b: run the pipeline over the cache and write weeks.json + report.txt."""
import json
from datetime import datetime, timezone

from .config import CACHE_DIR, FANDOM_CACHE_DIR, WEB_DIR, load_fandom_seasons, load_seasons, page_url
from .fetch import load_cached, load_fandom_cached
from .details import players, week_details
from .enrich import enrich_season
from .fandom import parse_season as parse_fandom_season
from .episodes import episodes_by_week
from .grid import build_episode_grid, build_grid
from .interpret import houseguests, interpret
from .validate import validate_week


def finalize(record):
    """Drop interpreter-internal keys; keep raw text only for note/error weeks."""
    raw = record.pop("_raw", None)
    record["raw"] = raw if record["status"] != "ok" else None
    for rnd in record["rounds"]:
        rnd.pop("_vote_cells", None)
        rnd.pop("_voters", None)
    return record


def process_season(season, html):
    """Return the finished week records for one season's cached HTML."""
    return process_season_full(season, html)["weeks"]


def process_season_full(season, html):
    """Week records plus the detail-view data for one season.

    Returns {"weeks", "details", "players", "unmatched"}; see details.py.
    """
    grid = build_grid(html)
    records = interpret(grid, season)
    for record in records:
        validate_week(record)
    # Details need the interpreter's internal keys, so build them before finalize().
    detail = week_details(records, grid.notes, episodes_by_week(build_episode_grid(html)))
    people, unmatched = players(season, records, houseguests(grid))
    return {
        "weeks": [finalize(r) for r in records],
        "details": detail,
        "players": people,
        "unmatched": unmatched,
    }


LICENSE = ("Wikipedia content, CC BY-SA 4.0; "
           "Big Brother Wiki (bigbrother.fandom.com) content, CC BY-SA 3.0")


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


def run(seasons=None, cache_dir=CACHE_DIR, out_dir=WEB_DIR, fandom_seasons=None, fandom_dir=FANDOM_CACHE_DIR):
    seasons = seasons or load_seasons()
    fandom_seasons = load_fandom_seasons() if fandom_seasons is None else fandom_seasons
    sources, weeks, season_errors = [], [], []
    details, people, unmatched = {}, [], []
    for season, title in seasons.items():
        cached = load_cached(season, cache_dir)
        source = {"season": season, "title": title, "url": page_url(title)}
        if cached is None:
            season_errors.append((season, "not in cache (run `python -m bbgrid fetch`)"))
            sources.append({**source, "error": "not fetched"})
            continue
        html, meta = cached
        source.update(revid=meta.get("revid"), fetched_at=meta.get("fetched_at"))
        if meta.get("revid"):
            source["permalink"] = f"https://en.wikipedia.org/w/index.php?oldid={meta['revid']}"
        try:
            result = process_season_full(season, html)
            weeks.extend(result["weeks"])
            details.update(result["details"])
            people.extend(result["players"])
            unmatched.extend((season, name) for name in result["unmatched"])
        except Exception as e:  # a whole-season failure is reported, not fatal
            season_errors.append((season, f"{type(e).__name__}: {e}"))
            source["error"] = str(e)
        sources.append(source)

    seasons_info, fandom_lines = add_fandom(
        {s: t for s, t in fandom_seasons.items() if s in seasons}, fandom_dir,
        sources, weeks, details, people, season_errors)

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "license": LICENSE,
        "sources": sources,
        "weeks": weeks,
    }
    (out_dir / "weeks.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # Detail views load this separately, so the main grid stays light.
    detail_doc = {"generated_at": doc["generated_at"], "license": doc["license"],
                  "seasons": {str(k): v for k, v in sorted(seasons_info.items())},
                  "weeks": details, "players": people}
    (out_dir / "details.json").write_text(json.dumps(detail_doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                                          encoding="utf-8")
    report = make_report(weeks, season_errors, unmatched, fandom_lines)
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
