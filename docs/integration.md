# Integrating the week grid

There are three ways to use this project from somewhere else: host the page, embed the page
in another site, or read the data yourself. All three rely on the two files in `web/`:

| File | What it is |
|---|---|
| `web/index.html` | The page. One self-contained file with no dependencies, which loads `weeks.json` from next to itself. |
| `web/weeks.json` | The main data: one record per season-week, plus source and attribution info. |
| `web/details.json` | Detail-view data: votes, what was different, episodes, and player stats. Loaded only when a detail view is opened. |

Keeping `weeks.json` up to date is covered at the end.

## 1. Host the page

Any static host works. Serve `index.html`, `weeks.json` and `details.json` from the same folder over HTTP.
Opening the file directly (`file://`) won't work, because the browser blocks it from
loading `weeks.json`.

**GitHub Pages.** The simplest way is to publish the `web/` folder with a Pages workflow:

1. In the repo, open **Settings → Pages** and set **Source** to **GitHub Actions**.
2. Add `.github/workflows/pages.yml`:

   ```yaml
   name: Publish page
   on:
     push:
       branches: [main]
       paths: [web/**]
     # Commits made by the fetch workflow don't trigger push events,
     # so also redeploy whenever a fetch run finishes.
     workflow_run:
       workflows: ["Fetch Wikipedia pages"]
       types: [completed]
       branches: [main]
     workflow_dispatch:
   permissions:
     pages: write
     id-token: write
   jobs:
     deploy:
       runs-on: ubuntu-latest
       environment: github-pages
       steps:
         - uses: actions/checkout@v4
           with:
             ref: main
         - uses: actions/upload-pages-artifact@v3
           with:
             path: web
         - uses: actions/deploy-pages@v4
   ```

3. The page is then at `https://<user>.github.io/BigBrotherDataFromWiki/`.

Change `main` to whichever branch you publish from.

**Any other static host** (Netlify, Cloudflare Pages, S3, your own server): upload
`web/index.html`, `web/weeks.json` and `web/details.json` together.

**Locally:** `python -m http.server -d web`, then open http://localhost:8000.

## 2. Embed it in another page

Add `?embed=1` to hide the page's own title and intro, so it sits inside your layout:

```html
<iframe
  src="https://<user>.github.io/BigBrotherDataFromWiki/?embed=1"
  title="Big Brother week-by-week grid"
  style="width: 100%; height: 560px; border: 0;"
  loading="lazy"></iframe>
```

- **Height.** About 560px fits all eight seasons with the legend. The grid scrolls
  sideways inside the frame on narrow screens.
- **Theme.** The page follows the viewer's light/dark setting. The dark theme is a navy
  board styled to sit next to Taran's stock-watch graphics. Add `&theme=dark` (or
  `&theme=light`) to pin one, e.g. `?embed=1&theme=dark` for a stream overlay.
- **Deep links.** Every view has its own link, so an iframe can open straight into
  one: `?embed=1#week=26/Week%2010` (a week's details), `?embed=1#players=28` (a
  season's players), or `?embed=1#player=26/Angela` (one player).
- **Attribution.** The Wikipedia credit line stays visible in embed mode. It's needed
  for the CC BY-SA license, so don't hide it.

## 3. Use the data directly

Read `weeks.json` from wherever you host it, or straight from the repo:

```
https://raw.githubusercontent.com/christopherbholland/BigBrotherDataFromWiki/<branch>/web/weeks.json
```

(The raw URL only works without a login if the repo is public.)

The file has this shape:

```jsonc
{
  "generated_at": "2026-09-22T18:20:46+00:00",
  "license": "Wikipedia content, CC BY-SA 4.0",
  "sources": [
    { "season": 26, "title": "Big Brother 26 (American season)",
      "url": "https://en.wikipedia.org/wiki/…", "revid": 1234, "fetched_at": "…",
      "permalink": "https://en.wikipedia.org/w/index.php?oldid=1234" }
  ],
  "weeks": [
    {
      "season": 26, "week": 10, "week_label": "Week 10",
      "status": "ok",                  // "ok" | "note" | "error"
      "note": "Double eviction",       // why it isn't plain; null for an ordinary week
      "rounds": [
        {
          "sub_label": "Day 67",       // null for a one-round week
          "hoh": ["Makensy"],          // every name field is a list
          "nominees_initial": ["Angela", "Kimo"],
          "veto_winners": ["Makensy"],
          "nominees_final": ["Angela", "Leah"],
          "evicted": "Leah",
          "tally": { "type": "vote", "votes_to_evict": 4, "votes_cast": 4 },
          // or { "type": "sole_vote", "by": "Makensy" }
          "extras": { "AI Arena winner": ["Kimo"] }   // twist rows, keyed by table label
        }
      ],
      "raw": null,                     // for note/error weeks: the week's table text
      "footnotes": ["c"]               // Wikipedia footnote markers in the week's cells
    }
  ]
}
```

Things to know:

- **`rounds` can be empty or partial.** A `note` week may leave out rounds it can't
  model: a twist, a week still airing, or a Finale column. `note` explains why, and
  `raw` has the table text.
- **`raw` shape.** `{columns: [...], rows: [{label, cells: [...]}]}`, with one cell per
  sub-column.
- **Week keys.** `week` is the number from the table header; `week_label` is the header
  text as shown.
- **Attribution.** If you publish anything built on this data, credit Wikipedia under
  CC BY-SA 4.0 and link the source pages. They're in `sources`, with `permalink` pointing
  at the exact revision used.

### details.json

```jsonc
{
  "generated_at": "…", "license": "Wikipedia content, CC BY-SA 4.0",
  "weeks": {
    "26|Week 4": {                                 // "<season>|<week_label>"
      "rounds": [{                                 // same order as weeks.json rounds
        "sub_label": null,
        "votes": [{ "voter": "Makensy", "vote": "Cedric" }],
        "by_nominee": [{ "nominee": "Cedric", "voters": ["Makensy", "…"] }],
        "not_voting": [{ "voter": "Quinn", "reason": "Head of Household" }],
        "veto": {                                  // null when there was no veto
          "used": true, "on": ["Tucker"], "replacements": ["Rubina"],
          "twist_saved": ["Makensy"]               // left the block through a twist row instead
        }
      }],
      "comps": [                                   // from the episode summaries
        { "kind": "hoh", "name": "Eye Candy", "winner": "Makensy", "round": 1,
          "source": "In the \"Eye Candy\" Head of Household competition, Makensy emerged as the winner." },
        { "kind": "hoh", "name": "Bad A.I", "winner": null, "round": null, "source": "…" }
      ],
      "veto_notes": ["At the Veto Meeting, Makensy … used the Veto on Kimo."],
      "special": {
        "items": ["AI Arena winner: Makensy"],     // twist rows and unusual outcomes
        "notes": [{ "label": "b", "text": "Quinn activated the Deepfake HoH, …" }]
      },
      "episodes": [{
        "number_overall": "909", "number": "12", "title": "Episode 12",
        "days": "Days 24–25", "air_date": "2024-08-11", "air_date_text": "August 11, 2024",
        "viewers_millions": 2.2, "summary": "…"
      }]
    }
  },
  "players": [{
    "season": 26, "name": "Angela", "result": "Evicted (Day 73)",  // null while still in the game
    "hoh": ["Week 1", "Week 4"], "veto": ["Week 9"],
    "nominated": ["Week 2", "…"], "on_block": ["…"], "evicted": "Week 10 (Day 73)",
    "votes_against": [{ "week": "Week 2", "voters": ["Kenney"] }],
    "votes_cast": [{ "week": "Week 3", "vote": "Kenney", "with_house": true }],
    "twist": [{ "week": "…", "label": "AI Arena winner" }]
  }]
}
```

- **Week names inside `players`.** A round of a two-round week is written as
  `"Week 10 (Day 73)"`.
- **What the player stats count.** They cover only the modeled rounds; twist rounds that
  appear only as notes aren't counted.
- **`special.notes`.** Wikipedia's footnote text, quoted as written.
- **`veto`.** Worked out from the nominations before and after the veto. The table
  doesn't state who the veto was used on, but it shows who came off the block and who
  replaced them.
- **`comps`.** Competition names found in the episode summaries. A competition has a
  `winner` and `round` only when that round's HOH or veto winner is named in the same or
  the next sentence. Unmatched names (often the next week's HOH, which starts on the live
  show) have `winner: null`. `source` is the sentence the name came from.
- **`episodes`.** From the season page's episode table, grouped by the week headings
  already in that table.

Example: every HOH in BB26.

```js
const data = await (await fetch("weeks.json")).json();
const hohs = data.weeks
  .filter(w => w.season === 26)
  .flatMap(w => w.rounds.map(r => `${w.week_label}: ${r.hoh.join(" & ")}`));
```

## Keeping it up to date

The **Fetch Wikipedia pages** GitHub Action refetches the pages. If any page changed, it
rebuilds `web/weeks.json`, `web/details.json` and `report.txt` and commits them. To run it from a phone or
browser:

1. Open the repo's **Actions** tab and choose **Fetch Wikipedia pages**. (GitHub only
   shows the **Run workflow** button once the workflow file is on the repo's default
   branch. Until then, it runs when `seasons.yaml` or the workflow file changes.)
2. Tap **Run workflow**. Pick the branch, and optionally enter season numbers (e.g. `28`).
   Leave it blank to fetch all seasons.

If you host with the Pages workflow above, it redeploys after every fetch run.

After a refresh, read `report.txt` for new `note`/`error` weeks. The snapshot tests
(`tests/snapshots/`) will fail on any week whose data changed. That's expected after new
episodes: review the diff, then accept it with
`UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py`.

To add a season, add a line to `seasons.yaml` and push. The workflow runs automatically
when that file changes.
