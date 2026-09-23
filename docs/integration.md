# Integrating the week grid

There are three ways to use this project from somewhere else: host the page, embed the page
in another site, or read the data yourself. All three rely on the two files in `web/`:

| File | What it is |
|---|---|
| `web/index.html` | The page. One self-contained file with no dependencies, which loads `weeks.json` from next to itself. |
| `web/weeks.json` | The main data: one record per season-week, plus source and attribution info. |
| `web/details.json` | Detail-view data: votes, what was different, episodes, player stats, and the Big Brother Wiki additions (competitions, Have-Nots, bios, season facts). Loaded only when a detail view is opened. |

Keeping `weeks.json` up to date is covered at the end.

## 1. Host the page

Any static host works. Serve `index.html`, `weeks.json` and `details.json` from the same folder over HTTP.
Opening the file directly (`file://`) won't work, because the browser blocks it from
loading `weeks.json`.

**GitHub Pages.** The repo includes `.github/workflows/pages.yml`, which publishes the
`web/` folder. It runs on every push to `main` that changes `web/`, after every run of the
fetch workflow, and by hand from the Actions tab. To turn it on:

1. Make sure Pages is available for the repo. It's free on public repos. A private repo
   needs a paid plan (GitHub Pro or above). Either way, the published site itself is public.
2. In the repo, open **Settings → Pages** and set **Source** to **GitHub Actions**.
3. Merge to `main`, or run **Publish page** from the Actions tab.
4. The page is then at <https://christopherbholland.github.io/BigBrotherDataFromWiki/>
   (on a fork, `https://<user>.github.io/BigBrotherDataFromWiki/`).

**Staying current.** The fetch workflow runs every day at 14:00 UTC. When a Wikipedia page
has changed, it commits the new data, and the Pages workflow republishes. You can also run
**Fetch wiki pages** by hand from the Actions tab, including from the GitHub mobile app.

**On your phone.** Open the Pages address in Safari or Chrome. To open it like an app
(full screen, no browser bar), use **Share → Add to Home Screen** in Safari, or **⋮ → Add
to Home screen** in Chrome.

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
- **Only some seasons.** `&seasons=26-28` (or `21,26`, or `21-23,28`) shows just those
  seasons, e.g. `?embed=1&seasons=27-28` for a short embed. It also limits the Players and
  Comps season pickers.
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
  "schema_version": 1,                 // see "Versioning" below
  "generated_at": "2026-09-22T18:20:46+00:00",
  "license": "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/): adapted from Wikipedia (CC BY-SA 4.0) and the Big Brother Wiki, … Houseguest photos are CBS promotional images, … not covered by this license.",
  "sources": [
    { "season": 26, "title": "Big Brother 26 (American season)",
      "url": "https://en.wikipedia.org/wiki/…", "revid": 1234, "fetched_at": "…",
      "permalink": "https://en.wikipedia.org/w/index.php?oldid=1234",
      "fandom": { "title": "Big Brother 26 (US)", "url": "https://bigbrother.fandom.com/wiki/…",
                  "revid": 674463, "permalink": "https://bigbrother.fandom.com/?oldid=674463", "fetched_at": "…" } }
  ],
  "weeks": [
    {
      "season": 26, "week": 10, "week_label": "Week 10",
      "status": "ok",                  // "ok" | "note" | "error"
      "note": "Double eviction",       // why it isn't plain; null for an ordinary week.
                                       // "Two evictions" when both rounds are ordinary weeks
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
          "extras": { "AI Arena winner": ["Kimo"] },  // twist rows, keyed by table label
          "double_eviction": false     // true for a round played in one night (see below)
        }
      ],
      "raw": null,                     // for note/error weeks: the week's table text
      "footnotes": ["c"]               // Wikipedia footnote markers in the week's cells
    }
  ],
  "photos": {                          // each houseguest's headshot, by season and Wikipedia name
    "26": { "Angela": "https://static.wikia.nocookie.net/bigbrother/images/2/27/US26_Small_Angela.jpg/revision/latest?cb=20240715171442" }
  }
}
```

Things to know:

- **`rounds` can be empty or partial.** A `note` week may leave out rounds it can't
  model: a twist, a week still airing, or a Finale column. `note` explains why, and
  `raw` has the table text.
- **Double evictions.** Wikipedia lists both of a week's evictions under one week header,
  but only a fast-forward round is a double eviction: HOH, nominations, veto and eviction
  all on the night of the previous eviction. That round has `double_eviction: true`
  (e.g. BB28 Week 10's second round, Yash). A week whose two rounds were both ordinary,
  a few days apart, has the note `Two evictions`.
- **`raw` shape.** `{columns: [...], rows: [{label, cells: [...]}]}`, with one cell per
  sub-column.
- **Week keys.** `week` is the number from the table header; `week_label` is the header
  text as shown.
- **`photos`.** The Big Brother Wiki's 4:5 headshot of each houseguest, from the cards
  in the season page's Houseguests section. A houseguest with no Big Brother Wiki page
  has no entry. The wiki resizes on request: insert `/scale-to-width-down/<px>` after
  `/revision/latest` (the page asks for 80px). These pictures are CBS promotional photos,
  not CC BY-SA content: the page links to them where the wiki keeps them rather than
  copying them, and credits them in its footer.
- **Attribution.** If you publish anything built on this data, credit Wikipedia under
  CC BY-SA 4.0 and link the source pages. They're in `sources`, with `permalink` pointing
  at the exact revision used. If you use the Big Brother Wiki fields (everything under
  `fandom` and `seasons` in details.json), also credit the Big Brother Wiki under
  CC BY-SA 3.0; its pages are in `sources[].fandom`. What you build from the data must
  be shared under CC BY-SA 4.0 too, and should say it was adapted. See
  [`DATA_LICENSE.md`](../DATA_LICENSE.md).

### details.json

```jsonc
{
  "schema_version": 1, "generated_at": "…", "license": "…",   // as in weeks.json
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
        "items": ["AI Arena: Makensy"],     // twist rows and unusual outcomes
        "notes": [{ "label": "b", "text": "Quinn activated the Deepfake HoH, …" }]
      },
      "episodes": [{
        "number_overall": "909", "number": "12", "title": "Episode 12",
        "days": "Days 24–25", "air_date": "2024-08-11", "air_date_text": "August 11, 2024",
        "viewers_millions": 2.2, "summary": "…"
      }],
      "fandom": {                                  // from the Big Brother Wiki; absent if not fetched
        "comps": [{                                // every row of its Competition History this week
          "kind": "hoh",                           // "hoh" | "veto" | "twist"
          "type": "HOH", "name": "Bad AI", "format": "Knockout",  // format: the recurring comp, or null
          "day": "24", "winners": ["Angela"], "outcome": "wins HOH", "won": true,
          "round": 1,                              // round whose HOH/veto winner it is; null otherwise
          "extra": {},                             // other columns, e.g. BB25's {"Multiverse": "…"}
          "about": "In the \"Bad A.I.\" Head of Household competition, …",  // episode-summary sentence, or null
          "category": "Mental",                    // Endurance | Physical | Skill | Mental | Hybrid | Puzzle | Crapshoot | null
          "category_from": "summary",              // "wiki" | "format" | "summary" | "other plays" | null
          "wiki_category": null,                   // the format page's own type, when fetched
          "format_description": null,              // the format page's one-line summary
          "prize": { "name": "Diamond Power of Veto", "kind": "power" }  // twists only: the named power or
                                                   // punishment, from the type or the summaries; else null
        }],
        "have_nots": [{ "name": "Kimo", "chosen_by": null }],
        "checks": [{ "round": 1, "field": "Initial nominations",   // where the two wikis disagree
                     "wikipedia": ["…"], "fandom": ["…"] }]
      }
    }
  },
  "categories": [{ "name": "Endurance", "help": "last one standing" }, "…"],
  "formats": {                                     // one entry per recurring competition format
    "Knockout": { "url": "https://bigbrother.fandom.com/wiki/Knockout", "category": "Mental",
                  "description": "…",              // the wiki's one-line summary, or null
                  "about": { "text": "…", "season": 26, "week": "Week 4" },  // how it's played, or null
                  "plays": [{ "season": 26, "week": "Week 4", "kind": "hoh", "name": "Bad AI",
                              "winners": ["Angela"], "day": "24", "category": "Mental", "about": "…" }] }
  },
  "seasons": {
    "26": { "premiere": "2024-07-17", "finale": "2024-10-13", "days": "90", "houseguests": "16",
            "episodes": "39", "prize": "$750,000", "winner": "Chelsie Baham", "host": "Julie Chen-Moonves",
            "title": "Big Brother 26 (US)", "url": "…", "revid": 674463, "permalink": "…", "…": "…" }
  },
  "players": [{
    "season": 26, "name": "Angela", "result": "Evicted (Day 73)",  // null while still in the game
    "hoh": ["Week 1", "Week 4"], "veto": ["Week 9"],
    "nominated": ["Week 2", "…"], "on_block": ["…"], "evicted": "Week 10 (Day 73)",
    "votes_against": [{ "week": "Week 2", "voters": ["Kenney"] }],
    "votes_cast": [{ "week": "Week 3", "vote": "Kenney", "with_house": true }],
    "twist": [{ "week": "…", "label": "AI Arena winner" }],
    "bio": { "full_name": "Angela Murray", "age": 50,   // Wikipedia's cast table; null if unmatched
             "occupation": "Real estate agent", "hometown": "Syracuse, Utah" },
    "fandom": {                                    // null when no Big Brother Wiki page matched
      "page": "Angela Murray", "url": "https://bigbrother.fandom.com/wiki/Angela_Murray",
      "full_name": "Angela Lorraine Murray", "birth_date": "1973-08-17", "age": 50,  // age at the premiere
      "hometown": ["Long Beach, CA", "Syracuse, UT"], "occupation": "Realtor", "nickname": ["Mama"],
      "place": "6th", "days": "73", "alliances": ["BB Guns", "…"], "other_prizes": [],
      "seasons": ["Big Brother 26 (US)", "Big Brother 28 (US)"],
      "photo": "https://static.wikia.nocookie.net/…/US26_Small_Angela.jpg/revision/latest?cb=…",  // headshot, as in weeks.json
      "portrait": "https://static.wikia.nocookie.net/…/US26_Angela_Large.jpg/revision/latest",   // this season's large picture; null if none
      "have_not": ["Week 5"],
      "twist_wins": [{ "week": "…", "type": "AI Arena", "name": "…", "outcome": "is saved", "prize": null }]
                                                   // twist wins, plus punishments that have a name
    }
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
- **Competition categories.** `category` is worked out in `bbgrid/comps.py`: first the
  Big Brother Wiki's page for the format, whose opening sentence names its type ("a
  recurring endurance Head of Household competition"), then a list of recurring formats
  whose type is settled, then keywords in the format page's one-line description ("Hang
  on to a moving wall as long as you can"), then in the competition's episode-summary
  sentence, then the most common type among the format's other plays. About 19 in 20
  HOH and veto competitions get one.
- **`bio` vs `fandom`.** The page shows age, hometown and occupation from `bio`
  (Wikipedia, age as listed there) and falls back to `fandom`.
- **`comps`.** Competition names found in the episode summaries. A competition has a
  `winner` and `round` only when that round's HOH or veto winner is named in the same or
  the next sentence. Unmatched names (often the next week's HOH, which starts on the live
  show) have `winner: null`. `source` is the sentence the name came from.
- **`episodes`.** From the season page's episode table, grouped by the week headings
  already in that table.
- **`fandom.portrait`.** The larger picture in the houseguest's infobox for this season,
  picked by the season in its file name or caption. Its URL is built from the file name
  (the wiki stores files under the MD5 of the name), so it isn't checked when building;
  the page falls back to `photo`, then initials, if it doesn't load.
- **`fandom`.** Read from the Big Brother Wiki. Names are translated to Wikipedia's (the
  wiki says "Jackson" where Wikipedia says "Michie"). A name that can't be matched is kept
  as the wiki writes it and listed in `report.txt`. The page prefers `fandom.comps` over
  `comps` for competition names.

### Versioning

Both files carry `schema_version`, currently `1`. It goes up only when a field is
removed or renamed, or changes meaning. New fields can appear without a version change,
so ignore keys you don't know. To be safe, check the version before reading:

```js
if (data.schema_version !== 1) console.warn("weeks.json format changed; see docs/integration.md");
```

Example: every HOH in BB26.

```js
const data = await (await fetch("weeks.json")).json();
const hohs = data.weeks
  .filter(w => w.season === 26)
  .flatMap(w => w.rounds.map(r => `${w.week_label}: ${r.hoh.join(" & ")}`));
```

## Keeping it up to date

The **Fetch wiki pages** GitHub Action refetches the pages. If any page changed, it
rebuilds `web/weeks.json`, `web/details.json` and `report.txt` and commits them. To run it from a phone or
browser:

1. Open the repo's **Actions** tab and choose **Fetch wiki pages**. (GitHub only
   shows the **Run workflow** button once the workflow file is on the repo's default
   branch. Until then, it runs when `seasons.yaml` or the workflow file changes.)
2. Tap **Run workflow**. Pick the branch, and optionally enter season numbers (e.g. `28`).
   Leave it blank to fetch all seasons.

If you host with the Pages workflow above, it redeploys after every fetch run.

After a refresh, read `report.txt` for new `note`/`error` weeks. The workflow also updates
the test snapshots (`tests/snapshots/`) in the same commit, so the commit's snapshot diff
shows exactly which weeks changed. After a local `fetch`, accept the changes yourself with
`UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py tests/test_fandom_snapshots.py`.

To add a season, widen the range in `seasons.yaml` (e.g. `seasons: "21-29"`) and push.
The workflow runs automatically when that file changes. For older seasons, see
[`all-seasons.md`](all-seasons.md).
