# BigBrotherDataFromWiki

A week-by-week grid of US Big Brother seasons 21–28. Each cell is one week of one season.
Hovering shows that week's HOH, noms, veto winner(s), final noms, who was evicted, and the
vote tally. The season currently airing (BB28) is on top. The grid comes from the "Voting history" table on each season's
Wikipedia page. The detail views add data from the fan-run
[Big Brother Wiki](https://bigbrother.fandom.com/) (Fandom): every competition's name,
weekly Have-Nots, houseguest bios and season facts. It's also used to cross-check Wikipedia.

```
Wikipedia API ---------> fetch -> cache/        -> grid builder -> interpreter -> validator/exporter
Big Brother Wiki API --> fetch -> cache/fandom/ -> fandom reader --------------> merge (details.json)
                                                -> web/weeks.json, details.json, report.txt -> web/index.html
```

| Step | Module | Knows about |
|---|---|---|
| 1. Fetcher | `bbgrid/fetch.py` | the MediaWiki API, for both wikis (the only network code) |
| 2. Grid builder | `bbgrid/grid.py` | HTML only: finds the table, expands rowspan/colspan |
| 3. Interpreter | `bbgrid/interpret.py` | Big Brother only: row labels, weeks, rounds, statuses |
| 4. Validator + exporter | `bbgrid/validate.py`, `bbgrid/export.py` | checks each round, writes the outputs |
| 5. Web page | `web/index.html` | static page that reads `weeks.json` |
| Big Brother Wiki reader | `bbgrid/fandom.py`, `bbgrid/wikitext.py` | the wiki's tables and infoboxes |
| Merge | `bbgrid/enrich.py` | matching the two wikis' names; adds to `details.json`, cross-checks |

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

**Competitions** name every HOH and veto competition (210 of 213 rounds) from the Big
Brother Wiki's Competition History, with the recurring format where the wiki gives one
(e.g. "Bad AI", format: Knockout). The same table lists the week's other competitions:
AI Arena, Block Buster, Safety Suite, final HOH parts and so on. Episode summaries fill in
the few names the wiki doesn't have. **Have-Nots** lists each week's Have-Nots, with who
picked them where the wiki says. **Sources disagree** appears only when the wiki's Game
History differs from Wikipedia on that week's HOH, nominations, veto winner or veto use.

**Players**: a table for each season showing HOHs, vetoes, twist wins, noms, final noms,
votes against, and votes cast (with how many went with the house). Click a player for a
week-by-week timeline that names the competitions they won and says whether they were
saved by the veto or by a twist. From the Big Brother Wiki it adds each player's full
name, age at the premiere, hometown, occupation, alliances and Have-Not weeks. The table
also gets a line of season facts: premiere, days, cast size, prize and host.

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

python -m bbgrid fetch            # fetch all seasons in seasons.yaml into cache/, from both wikis
                                  # (or run the "Fetch wiki pages" GitHub Action)
python -m bbgrid inspect 21 26    # print table headers and row-label mapping (for checking)
python -m bbgrid build            # cache/ -> web/weeks.json, web/details.json, report.txt
python -m bbgrid refresh 28       # refetch one season, then build
python -m bbgrid proofread        # web/*.json -> proofread.xlsx, a sheet for checking every fact
python -m bbgrid inspect-fandom 26  # what was read from the cached Big Brother Wiki page

python -m http.server -d web      # then open http://localhost:8000
pytest
```

`report.txt` lists every week that isn't `ok`. It's the main acceptance check. A "Big Brother
Wiki" block near the top lists anything that didn't line up: disagreements with Wikipedia,
houseguests with no wiki page, and names the reader couldn't match.

To add a season, add a line to each list in `seasons.yaml`: the Wikipedia article under
`seasons`, and the Big Brother Wiki page (e.g. `Big Brother 29 (US)`) under `fandom`.

## Integrating

The page is one static HTML file plus `weeks.json`, so it can go anywhere:

- **Host it** on GitHub Pages: `.github/workflows/pages.yml` publishes `web/`, so you can use it from a phone. See the integration guide for setup.
- **Embed it** in another site with an iframe; `?embed=1` hides the page's title:
  ```html
  <iframe src="https://<user>.github.io/BigBrotherDataFromWiki/?embed=1"
          title="Big Brother week-by-week grid"
          style="width:100%;height:560px;border:0" loading="lazy"></iframe>
  ```
- **Use the data**: `web/weeks.json` has one record per season-week, with every field
  documented.
- **Keep it fresh** by running the **Fetch wiki pages** action. It refetches the
  pages from both wikis, rebuilds `weeks.json` and `details.json`, and commits the changes.

Step-by-step instructions, including GitHub Pages setup and the full data
format, are in [`docs/integration.md`](docs/integration.md).

## Tests

- `tests/test_grid.py`: grid builder on small synthetic tables (rowspan, colspan, both).
- `tests/test_interpret.py`: interpreter and validator on
  `tests/fixtures/synthetic_season.html`. That table is **synthetic**: the houseguests and
  events are made up. It copies the structure the design doc describes for BB26.
- `tests/test_details.py`: votes, what was different, player stats, footnote text and
  episode parsing.
- `tests/test_fandom.py`, `tests/test_wikitext.py`: the Big Brother Wiki reader and
  merge on `tests/fixtures/fandom_season.html`, a **synthetic** page (made-up houseguests)
  that copies the real pages' structure; name matching; the cross-check.
- `tests/test_fandom_snapshots.py`: one snapshot per cached Big Brother Wiki season
  (`tests/snapshots/fandom_bbNN.json`), updated the same way as below.
- `tests/test_snapshots.py`: one snapshot per cached season in `tests/snapshots/`. A season
  with no cache file is skipped. The first run writes the snapshot. After an intended
  change, update with `UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py`.

## Attribution

The grid's data comes from Wikipedia under CC BY-SA 4.0. The detail views also use the
Big Brother Wiki (bigbrother.fandom.com) under CC BY-SA 3.0. The page credits each source
article on both wikis and links to the exact revision used.
