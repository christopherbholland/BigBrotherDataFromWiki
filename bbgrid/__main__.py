"""Command line entry point.

  python -m bbgrid fetch [SEASON ...]    refetch pages into cache/ (all seasons if none given)
  python -m bbgrid build                 cache/ -> web/weeks.json + report.txt
  python -m bbgrid inspect [SEASON ...]  print each cached table's headers and row labels
  python -m bbgrid refresh SEASON ...    fetch the given seasons, then build
  python -m bbgrid proofread             web/*.json -> proofread.xlsx (a sheet to check every fact)
"""
import argparse
import sys

from .config import load_seasons
from .export import run
from .fetch import fetch_season, load_cached
from .grid import build_grid
from .interpret import classify_rows, label_columns, week_columns


def cmd_fetch(seasons):
    for season, title in seasons.items():
        meta = fetch_season(season, title)
        print(f"BB{season}: fetched {title!r} rev {meta['revid']}")


def cmd_build():
    _, report = run()
    print(report.splitlines()[0])
    print("wrote web/weeks.json and report.txt")


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
    parser = argparse.ArgumentParser(prog="bbgrid")
    parser.add_argument("command", choices=["fetch", "build", "inspect", "refresh", "proofread"])
    parser.add_argument("seasons", nargs="*", type=int)
    args = parser.parse_args(argv)
    all_seasons = load_seasons()
    unknown = [s for s in args.seasons if s not in all_seasons]
    if unknown:
        parser.error(f"seasons not in seasons.yaml: {unknown}")
    chosen = {s: all_seasons[s] for s in args.seasons} or all_seasons

    if args.command == "fetch":
        cmd_fetch(chosen)
    elif args.command == "build":
        cmd_build()
    elif args.command == "inspect":
        cmd_inspect(chosen)
    elif args.command == "proofread":
        from .proofread import build as build_sheet
        out, counts = build_sheet()
        print(f"wrote {out.name}: " + ", ".join(f"{n} {k}" for k, n in counts.items()))
    elif args.command == "refresh":
        if not args.seasons:
            parser.error("refresh needs at least one season, e.g. `refresh 28`")
        cmd_fetch(chosen)
        cmd_build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
