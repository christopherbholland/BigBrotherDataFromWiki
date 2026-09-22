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

To retake them after a style change, run `python scripts/screenshots.py` (needs
`pip install playwright` and `playwright install chromium`).

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

**Phone.** The grid scrolls sideways with the season labels pinned. Tapping a week opens
its details (see below).

<img src="docs/screenshots/mobile-week.png" alt="Phone-width view of the grid, BB28 on top" width="390">

## Detail views

The main cards stay short. More detail sits behind two options:

**Click or tap a week** to open its details:
- **Competitions**: the names of the HOH and veto competitions (e.g. "Eye Candy",
  "OTEV the Psychic Salamander", "The Wall"), taken from the episode summaries and tied
  to each round's winner. The summaries name them in about three weeks out of four.
- **Veto**: what was done with it (not used, used on whom, who was named as the
  replacement, or who came off the block through a twist instead), plus the episode
  summaries' own lines about the veto meeting.
- **Votes to evict**: each nominee with the houseguests who voted to evict them, plus
  who didn't vote and why (HOH, nominated, not eligible).
- **What was different**: the week's twist rows (e.g. "AI Arena winner: Makensy"),
  anything unusual about the eviction, and the explanatory notes Wikipedia attaches to
  that week, quoted as written.
- **Episodes**: that week's episodes from the season's episode table, with days, air
  date, viewers, and each episode's summary (tap to expand).

![Week details for BB26 Week 4: competitions, veto, votes and the Deepfake HoH twist](docs/screenshots/details-week.png)

**Players**: a table for each season showing HOHs, vetoes, twist wins, noms, final noms,
votes against, and votes cast (with how many went with the house). Click a player for a
week-by-week timeline that names the competitions they won and says whether they were
saved by the veto or by a twist.

![Players view for BB28 in dark mode](docs/screenshots/players-dark.png)

![Angela's BB26 timeline](docs/screenshots/details-player.png)

On a phone, details open as a bottom sheet:

<img src="docs/screenshots/mobile-details.png" alt="BB26 Week 10 details on a phone" width="390">

Every view has its own link, e.g. `#week=26/Week%204`, `#players=28` or
`#player=26/Angela`, so it can be shared or embedded directly. The detail data lives in
`web/details.json`, which loads only when a detail view is first opened.

## Usage

```sh
pip install -r requirements.txt

python -m bbgrid fetch            # fetch all seasons in seasons.yaml into cache/
                                  # (or run the "Fetch Wikipedia pages" GitHub Action)
python -m bbgrid inspect 21 26    # print table headers and row-label mapping (for checking)
python -m bbgrid build            # cache/ -> web/weeks.json, web/details.json, report.txt
python -m bbgrid refresh 28       # refetch one season, then build

python -m http.server -d web      # then open http://localhost:8000
pytest
```

`report.txt` lists every week that isn't `ok`. It's the main acceptance check.

To add a season, add a line to `seasons.yaml`.

## Integrating

The page is one static HTML file plus `weeks.json`, so it can go anywhere:

- **Host it** on Cloudflare Pages (free, works with a private repo): connect the repo and
  set the build output directory to `web`. It redeploys on every push, so you can use it
  from a phone. See the integration guide for setup.
- **Embed it** in another site with an iframe; `?embed=1` hides the page's title:
  ```html
  <iframe src="https://<project-name>.pages.dev/?embed=1"
          title="Big Brother week-by-week grid"
          style="width:100%;height:560px;border:0" loading="lazy"></iframe>
  ```
- **Use the data**: `web/weeks.json` has one record per season-week, with every field
  documented.
- **Keep it fresh** by running the **Fetch Wikipedia pages** action. It refetches the
  pages, rebuilds `weeks.json`, and commits the changes.

Step-by-step instructions, including Cloudflare Pages setup and the full data
format, are in [`docs/integration.md`](docs/integration.md).

## Tests

- `tests/test_grid.py`: grid builder on small synthetic tables (rowspan, colspan, both).
- `tests/test_interpret.py`: interpreter and validator on
  `tests/fixtures/synthetic_season.html`. That table is **synthetic**: the houseguests and
  events are made up. It copies the structure the design doc describes for BB26.
- `tests/test_details.py`: votes, what was different, player stats, footnote text and
  episode parsing.
- `tests/test_snapshots.py`: one snapshot per cached season in `tests/snapshots/`. A season
  with no cache file is skipped. The first run writes the snapshot. After an intended
  change, update with `UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py`.

## Attribution

The data comes from Wikipedia under CC BY-SA 4.0. The page credits each source article
and links to the exact revision used.
