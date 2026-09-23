# Adding every season

The project covers BB21–BB28 today. It's set up so that adding older seasons (BB1–BB20),
or new ones as they air, is a config change followed by a check of what comes out. This page
says what's ready and what to look at when you do it.

## The change

In `seasons.yaml`, widen the range:

```yaml
seasons: "1-28"
```

Page titles come from the patterns under `titles`, so nothing else is needed while the
wikis keep naming pages "Big Brother N (American season)" and "Big Brother N (US)". If a
page is ever named differently, add it under `exceptions`. `null` leaves a season out of
one wiki, e.g. to build a season from Wikipedia alone.

Then run the **Fetch wiki pages** action (it runs by itself when `seasons.yaml` changes),
or locally:

```sh
python -m bbgrid fetch 1 2 3 ...   # or `fetch` for everything
python -m bbgrid build
pytest                              # writes a snapshot for each new season on the first run
```

To try a few seasons first, use a list: `seasons: ["18-20", "21-28"]`.

## What's already ready

- **One season can't break the others.** A season whose page fails to parse is listed
  as a `SEASON ERROR` in `report.txt` and in the page footer ("Missing: …"). The other
  seasons still build, and a Big Brother Wiki failure never stops the Wikipedia data.
- **Weeks that don't fit the usual HOH → noms → veto → eviction shape** become `note`
  weeks: the grid shows the folded yellow corner, the tooltip gives the reason, and the
  week's table text is kept in `raw`. They're listed in `report.txt`.
- **The page.** The grid adds a row per season with the newest on top. With more than
  10 seasons, the Players and Comps views pick a season from a drop-down instead of a row
  of buttons. `?seasons=26-28` (or `21,26`, or `1-5,28`) limits the page to some seasons,
  e.g. to keep an embed short. This was checked with a stand-in 28-season data file.
- **Tests.** The snapshot tests cover every season in `seasons.yaml` and write a
  snapshot for a new one on the first run.
- **Build time.** About 1 second per season.

## What to check

These haven't been tried on the real older pages yet (they couldn't be fetched when this
was written), so expect some of them to need work:

1. **Early formats.** BB1 had no Head of Household or veto: the public voted houseguests
   out. BB2 added the HOH, and the Power of Veto arrived in BB3. Those weeks won't match
   the row labels in `bbgrid/interpret.py` (`TOP_FIELDS`). Expect them as `note` or
   `error` weeks, not wrong data. Run `python -m bbgrid inspect 1 2 3` to see each
   table's rows and how they were read, and add patterns if the tables are regular enough.
2. **Older Wikipedia tables.** Row labels, footnotes and episode tables vary more in
   older articles. Compare `report.txt` before and after, and skim `proofread.xlsx`.
3. **Big Brother Wiki pages.** Older season pages may lack the Competition History,
   Have-Not or Game History sections. Those parts come out empty and the Wikipedia data is
   unaffected. `python -m bbgrid inspect-fandom 5` shows what was read.
4. **Name matching.** `report.txt`'s "Big Brother Wiki" block lists houseguests the two
   wikis name differently. Returning players (All-Stars seasons) are the likely cases.
5. **`details.json` size.** It's about 0.9 MB for 8 seasons, so about 3 MB for 28. The
   page loads it the first time a detail view opens, so the grid itself isn't slowed. If
   that first open feels slow on phones, split it into one file per season
   (`details/26.json`) and load the season being viewed. Most of that change is in
   `loadDetails()` in `web/index.html` and `run()` in `bbgrid/export.py`. The format index
   (`formats`) spans seasons, so it would stay in one shared file.
6. **The daily fetch.** It fetches every season each day and only commits when a page
   changed. With 28 seasons that's about 110 API requests a day (four per season). If that ever
   seems too many, have the scheduled run fetch only the airing season. The workflow
   already takes a season list.

## Other versions of the show

Celebrity Big Brother and other countries' seasons reuse season numbers, so they'd need
their own `seasons.yaml`, cache folder and output. That's a bigger change than this page
covers.
