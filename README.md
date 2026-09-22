# BigBrotherDataFromWiki

A week-by-week grid of US Big Brother seasons 21–28. Each cell is one week of one season.
Hovering shows that week's HOH, nominees, veto winner(s), final nominees, who was evicted,
and the vote tally. The data comes from the "Voting history" table on each season's
Wikipedia page.

```
Wikipedia API -> fetch -> cache/ -> grid builder -> interpreter -> validator/exporter
              -> web/weeks.json + report.txt -> web/index.html
```

| Step | Module | Knows about |
|---|---|---|
| 1. Fetcher | `bbgrid/fetch.py` | the MediaWiki API (the only network code) |
| 2. Grid builder | `bbgrid/grid.py` | HTML only: finds the table, expands rowspan/colspan |
| 3. Interpreter | `bbgrid/interpret.py` | Big Brother only: row labels, weeks, rounds, statuses |
| 4. Validator + exporter | `bbgrid/validate.py`, `bbgrid/export.py` | checks each round, writes the outputs |
| 5. Web page | `web/index.html` | static page that reads `weeks.json` |

Implementation choices and open assumptions are in `docs/implementation-notes.md`.

## Screenshots

These use the real data: all eight seasons as fetched on 2026-09-22.

Hovering over BB26 Week 10 shows the double eviction's two rounds stacked:

![Light-mode grid of BB21–BB28 with the BB26 Week 10 double-eviction tooltip](docs/screenshots/grid-double-eviction.png)

A `note` week (marked `!`) shows why it isn't fully modeled, plus that week's raw table
text. This is BB21 Week 3, where the second column is the Camp Comeback re-entry. Dark mode:

![Dark-mode grid with the BB21 Week 3 note tooltip](docs/screenshots/grid-note-dark.png)

At phone width the grid scrolls sideways and tapping a cell pins its details. This is
BB26 Week 4, with two HOHs and the AI Arena twist row:

![Phone-width view with the BB26 Week 4 tooltip](docs/screenshots/mobile-week.png)

## Usage

```sh
pip install -r requirements.txt

python -m bbgrid fetch            # fetch all seasons in seasons.yaml into cache/
                                  # (or run the "Fetch Wikipedia pages" GitHub Action)
python -m bbgrid inspect 21 26    # print table headers and row-label mapping (for checking)
python -m bbgrid build            # cache/ -> web/weeks.json + report.txt
python -m bbgrid refresh 28       # refetch one season, then build

python -m http.server -d web      # then open http://localhost:8000
pytest
```

`report.txt` lists every week that isn't `ok`. It's the main acceptance check.

To add a season, add a line to `seasons.yaml`.

## Tests

- `tests/test_grid.py`: grid builder on small synthetic tables (rowspan, colspan, both).
- `tests/test_interpret.py`: interpreter and validator on
  `tests/fixtures/synthetic_season.html`. That table is **synthetic**: the houseguests and
  events are made up. It copies the structure the design doc describes for BB26.
- `tests/test_snapshots.py`: one snapshot per cached season in `tests/snapshots/`. A season
  with no cache file is skipped. The first run writes the snapshot. After an intended
  change, update with `UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py`.

## Attribution

The data comes from Wikipedia under CC BY-SA 4.0. The page credits each source article
and links to the exact revision used.
