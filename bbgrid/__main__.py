"""Command line entry point.

  python -m bbgrid fetch [SEASON ...]           refetch Wikipedia and Big Brother Wiki pages into cache/
                                                (all seasons if none given)
  python -m bbgrid build                        cache/ -> web/weeks.json, web/details.json, report.txt
  python -m bbgrid refresh SEASON ...           fetch the given seasons, then build
  python -m bbgrid proofread                    web/*.json -> proofread.xlsx (a sheet to check every fact)
  python -m bbgrid inspect [SEASON ...]         print each cached table's headers and row labels
  python -m bbgrid inspect-fandom [SEASON ...]  summarize what was read from each cached Big Brother Wiki page
"""
import argparse
import sys
from collections import Counter

from .config import load_fandom_seasons, load_seasons
from .export import run
from .fandom import parse_season as parse_fandom_season
from .fetch import fetch_fandom_season, fetch_season, load_cached, load_fandom_cached
from .grid import build_grid
from .interpret import classify_rows, label_columns, week_columns


def cmd_fetch(seasons):
    """Fetch both wikis. A Big Brother Wiki failure is reported but doesn't stop the run."""
    fandom = load_fandom_seasons()
    failed = []
    for season, title in seasons.items():
        meta = fetch_season(season, title)
        print(f"BB{season}: fetched {title!r} rev {meta['revid']}")
        if season not in fandom:
            continue
        try:
            meta = fetch_fandom_season(season, fandom[season])
        except Exception as e:  # the Wikipedia data is still worth building
            failed.append(season)
            print(f"::warning::BB{season}: Big Brother Wiki fetch failed: {type(e).__name__}: {e}")
            continue
        missing = f", missing {meta['missing_pages']}" if meta["missing_pages"] else ""
        print(f"BB{season}: fetched {fandom[season]!r} (Big Brother Wiki) rev {meta['revid']}, "
              f"{meta['houseguest_pages']} houseguest pages{missing}")
    return failed


def cmd_inspect_fandom(seasons):
    fandom = load_fandom_seasons()
    for season in seasons:
        cached = load_fandom_cached(season) if season in fandom else None
        if cached is None:
            print(f"BB{season}: Big Brother Wiki page not cached\n")
            continue
        data = parse_fandom_season(cached, season)
        info = data["info"] or {}
        print(f"BB{season}: {fandom[season]!r} rev {cached['meta'].get('revid')}, premiere {info.get('premiere')}")
        print(f"  roster ({len(data['roster'])}): " + ", ".join(f"{short} = {title}" for title, short in data["roster"]))
        print(f"  bios: {len(data['bios'])}; competitions: {len(data['competitions'])}; "
              f"game history rows: {len(data['game'])}; Have-Not weeks: {sorted(data['have_nots']['weeks'])}")
        kinds = Counter(c["type"] for c in data["competitions"])
        print("  competition types: " + ", ".join(f"{k} ({n})" for k, n in kinds.items()) + "\n")


def cmd_build():
    _, report = run()
    print(report.splitlines()[0])
    print("wrote web/weeks.json, web/details.json and report.txt")


def cmd_proofread():
    from .proofread import build as build_sheet  # openpyxl is only needed here
    out, counts = build_sheet()
    print(f"wrote {out.name}: " + ", ".join(f"{n} {k}" for k, n in counts.items()))


def cmd_inspect(seasons):
    for season in seasons:
        cached = load_cached(season)
        if cached is None:
            print(f"BB{season}: not cached\n")
            continue
        grid = build_grid(cached[0])
        label_cols = label_columns(grid)
        print(f"BB{season}: caption={grid.caption!r} width={grid.width} header_rows={len(grid.header_rows)}")
        for week_label, subs in week_columns(grid, label_cols):
            print(f"  {week_label}: " + ", ".join(repr(s) for s, _ in subs))
        rows = classify_rows(grid, label_cols)
        for kind, key, label, _ in rows:
            if kind != "vote":
                print(f"  [{kind:8}] {label}" + (f" -> {key}" if kind == "field" else ""))
        votes = [label for kind, _, label, _ in rows if kind == "vote"]
        print(f"  [vote    ] {len(votes)} rows: {', '.join(votes)}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m bbgrid", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["fetch", "build", "refresh", "proofread", "inspect", "inspect-fandom"])
    parser.add_argument("seasons", nargs="*", type=int, help="season numbers from seasons.yaml (default: all)")
    args = parser.parse_args(argv)
    all_seasons = load_seasons()
    unknown = [s for s in args.seasons if s not in all_seasons]
    if unknown:
        parser.error(f"seasons not in seasons.yaml: {unknown}")
    if args.command == "refresh" and not args.seasons:
        parser.error("refresh needs at least one season, e.g. `refresh 28`")
    chosen = {s: all_seasons[s] for s in args.seasons} or all_seasons

    commands = {
        "fetch": lambda: cmd_fetch(chosen),
        "build": cmd_build,
        "refresh": lambda: (cmd_fetch(chosen), cmd_build()),
        "proofread": cmd_proofread,
        "inspect": lambda: cmd_inspect(chosen),
        "inspect-fandom": lambda: cmd_inspect_fandom(chosen),
    }
    commands[args.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
