# BigBrotherDataFromWiki

A week-by-week grid of US Big Brother seasons 21–28. Each cell is one week of one season.
Hovering shows that week's HOH, noms, veto winner(s), final noms, who was evicted, and the
vote tally. The season currently airing (BB28) is on top. The data comes from the "Voting history" table on each season's
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

- **Hosting, embedding, or using the data elsewhere:** see
  [`docs/integration.md`](docs/integration.md).
- **Implementation choices and what the real tables showed:** see
  [`docs/implementation-notes.md`](docs/implementation-notes.md).

## Screenshots

These show the real data: all eight seasons as fetched from Wikipedia on 2026-09-22.

**A double eviction.** BB26 Week 10's two rounds are stacked in both the cell and the
tooltip:

![Light-mode grid of BB21–BB28 with the BB26 Week 10 double-eviction tooltip](docs/screenshots/grid-double-eviction.png)

**Two rounds that aren't a double eviction.** BB24 Week 7 was the split house, with
separate "Inside" and "Outside" evictions. Both are modeled, and the note names the
columns instead of calling it a double eviction. Dark mode:

![Dark-mode grid with the BB24 Week 7 "Two rounds: Inside / Outside" tooltip](docs/screenshots/grid-split-house-dark.png)

**A twist week.** Weeks marked `!` aren't fully modeled. The tooltip gives the reason and
the week's table text as Wikipedia shows it. In BB21 Week 3 the regular eviction is
modeled, and the Camp Comeback column (Cliff winning re-entry) is flagged:

![Light-mode grid with the BB21 Week 3 note tooltip and raw table text](docs/screenshots/grid-note.png)

**Phone.** The grid scrolls sideways with the season labels pinned. Tapping a cell opens
its details just below it. BB26 Week 3 had two veto winners and the AI Arena twist:

<img src="docs/screenshots/mobile-week.png" alt="Phone-width view with the BB26 Week 3 tooltip" width="390">

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

## Integrating

The page is one static HTML file plus `weeks.json`, so it can go anywhere:

- **Host it** on GitHub Pages or any static host. Serve `web/` over HTTP.
- **Embed it** in another site with an iframe; `?embed=1` hides the page's title:
  ```html
  <iframe src="https://<user>.github.io/BigBrotherDataFromWiki/?embed=1"
          title="Big Brother week-by-week grid"
          style="width:100%;height:560px;border:0" loading="lazy"></iframe>
  ```
- **Use the data**: `web/weeks.json` has one record per season-week, with every field
  documented.
- **Keep it fresh** by running the **Fetch Wikipedia pages** action. It refetches the
  pages, rebuilds `weeks.json`, and commits the changes.

Step-by-step instructions, including a ready-made GitHub Pages workflow and the full data
format, are in [`docs/integration.md`](docs/integration.md).

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
