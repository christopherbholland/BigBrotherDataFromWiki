# Implementation notes

This file records choices made while building v1 and what the real tables showed.

## What the real tables showed (fetched 2026-09-22)

All eight pages were fetched by the "Fetch wiki pages" (then called "Fetch Wikipedia pages") GitHub Action, because the
Claude sandbox can't reach Wikipedia. The first build gave 100 weeks: 85 `ok`, 15 `note`,
0 `error`. The vote-count check passed on every `ok` round.

**Assumptions that held in all eight seasons**
- The table has a "voting history" caption.
- There are two header rows (three in BB23 and BB24, where the middle row doesn't
  matter), with week labels on top and sub-column labels below.
- The label column is one column wide.
- Rows run: summary rows, then one vote row per houseguest, then `Evicted`.
- The top-row labels are the same in every season: `Head of Household`,
  `Nominations (initial)`, `Veto winner` (BB21–22) or `Veto winner(s)` (BB23+), and
  `Nominations (final)`. No mapping changes were needed.
- Tally text is always `X of Y votes to evict` or `<name>'s choice to evict`. (The page
  shows a vote as `X–(Y−X)`, e.g. `12–0`.)

**Twist rows, which land in `extras` without any code for them**

| Season | Label |
|---|---|
| BB22 | Room winner |
| BB23 | Wild Card winner |
| BB26 | AI Arena winner |
| BB27, BB28 | Block Buster winner |

**Two changes made after inspecting**
1. *Rowspan continuation rows.* The `Evicted` label spans two rows, and the second row
   differs only in the Finale column (winner and runner-up vote counts). A body row whose
   label cell started in an earlier row is now ignored. Before this fix it put a junk
   `extras: {"Evicted": ...}` entry into every round.
2. *Non-standard outcomes are notes, not errors.* An `Evicted` cell that is neither a vote
   tally nor a sole vote is a readable twist, not a structural failure. The round isn't
   modeled; the week becomes `note: Non-standard outcome: …` and keeps its raw text. Any
   other round in the same week is still modeled. A round with an empty `Evicted` cell
   (a round still airing) is noted too, but is modeled when it has an HOH. The six cases:
   - BB21 Week 1, Day 1: David, "Evicted by competition"
   - BB21 Week 3, Comeback: Cliff, "Won re-entry into game"
   - BB24 Week 1: "Eviction cancelled"
   - BB25 Week 8: Cameron, "Won re-entry into game"
   - BB27 Week 9, Day 59: Rachel, "Eliminated by competition"
   - BB28 Week 8, Day 52: Haley, "Yash's choice to eliminate"

**Things to know about the data**
- Some two-column weeks aren't double evictions on the show. BB24 Week 7's columns are
  "Inside" and "Outside" (the split house), and BB21 Weeks 1 and 3, BB27 Week 9 and BB28
  Week 8 pair an ordinary eviction with a twist round. These get the note
  `Two rounds: <column> / <column>` instead of `Double eviction` (see Status rules).
- Two evictions in one Wikipedia week aren't always a double eviction either. A round's
  "Day N" column label is its nomination day. In a true (fast-forward) double eviction
  that is also the day its evictee left, since the whole round is played in one night;
  their vote row reads "Evicted (Day N)" (BB25's "Zombie (Day 51)" counts too). BB27
  Week 11's second round was nominated on Day 77 but evicted on Day 80, so that week is
  `Two evictions`. The Big Brother Wiki's competition days agree on every season:
  each double-eviction round's HOH and veto are on the same day.
- BB25's last week has three columns (Day 94, Day 100, Finale): two sole-vote rounds plus
  the Finale.
- BB28 was still airing when fetched. Week 11's second round (Taylor's HOH) and Week 12
  have no eviction yet. BB28's caption on Wikipedia reads "Big Brother 26 voting history", a
  mistake on the page itself that doesn't affect parsing.

## Detail views (details.json)

All of this comes from the same cached page. Nothing is shown on the main cards.

- **Votes.** Each houseguest's vote-row cell for a round is either a vote (exactly one
  final nominee's name) or a reason for not voting (e.g. "Head of Household",
  "Nominated", "Not eligible"). "Evicted (Day X)"-style cells are left out.
- **What was different.**
  - The unusual parts of the week's note: two rounds, non-standard outcomes. "Finale"
    and "No eviction" don't count.
  - The week's twist rows.
  - The text of every Wikipedia footnote on the week's cells, header included.
    `grid.footnote_texts` resolves each `[a]` marker to its entry in the page's notes
    list and drops backlinks and citation numbers. There's no attempt to classify or
    reword a twist; the notes are quoted as written.
- **Veto use.** Worked out from the table. A nominee who is in the initial noms but not
  the final noms came off the block. If they're named in a twist row (e.g. the AI Arena
  winner), the twist saved them; otherwise the veto did. Final nominees who weren't
  initially nominated are the replacements. No change means the veto wasn't used.
- **Competition names.** Taken from the episode summaries with four phrasings:
  - `the "X" HOH competition`
  - `HOH competition, "X"`
  - `Power of Veto ("X")`
  - `Veto competition: X.`

  A name is tied to a round only when that round's HOH or veto winner is named in the
  same or the next sentence, with at most one competition of each kind per round. Live
  shows start the next week's HOH, so other names are kept as "also mentioned". Names
  were found in 75 of 100 weeks; some summaries (e.g. BB25's early weeks) don't name
  competitions at all.
- **Episodes.** Every season page has one `wikiepisodetable`, grouped by full-width
  "Week N" rows. Each episode row is followed by a full-width summary row. The week
  headings match the voting table's week labels in all eight seasons. Two BB24 episodes
  have no summary on Wikipedia, and BB28's unaired episodes have none yet.
- **Players.**
  - The roster is the voting table's vote rows. A player's result is the last cell in
    their row that states an outcome ("Winner", "Evicted (Day 52)"); jurors' Finale
    votes are skipped.
  - Stats count the modeled rounds only.
  - A name in parentheses in a twist row, like BB22's "Room winner: Kaysar, (Janelle)",
    isn't counted as a twist win.
  - Any summary-cell name that matches no houseguest is listed in `report.txt`. There are
    none today.
- **Header footnotes.** Footnotes on week headers (e.g. "[a] This week was a Double
  Eviction week") were previously missed. They're now included in each week's
  `footnotes`, which changed 17 weeks' snapshots.

## Row-label patterns (`bbgrid/interpret.py`)

Labels are lowercased, whitespace is collapsed, and footnote markers are removed before
matching.

| Pattern | Field |
|---|---|
| `head of household…` | `hoh` |
| `nomination(s) (initial / original / pre-veto)` | `nominees_initial` |
| `(power of) veto winner(s) / veto holder` | `veto_winners` |
| `nomination(s) (final / post-veto)` | `nominees_final` |
| `evicted…` | `evicted` + `tally` |
| any other label in a summary section | `extras` (keyed by the label as shown) |

If the same field matches twice, the second row goes to `extras` rather than overwriting
the first.

## Status rules as implemented

- One non-Finale sub-column: one round, `ok` if it passes validation.
- Two non-Finale sub-columns: two rounds, `ok`. The note is `Double eviction` when a round
  after the first has `double_eviction` (its "Day N" label is its evictee's exit day, and
  it had a veto, so a final-HOH round never counts). It is `Two evictions` when both
  sub-labels are "Day N" and both rounds are ordinary evictions. Otherwise it is
  `Two rounds: <label> / <label>`, e.g. BB24's split house, `Two rounds: Inside / Outside`,
  or a round still to be played.
- A Finale sub-column is never a round. It sets `note` / `Finale`, and the week's regular
  column is still modeled as a round and validated.
- Three or more non-Finale sub-columns: `note`, no rounds, raw text kept.
- A round with an empty or missing Evicted cell: `note` / `No eviction`. If it has an HOH
  it's still modeled, with `evicted` and `tally` null, so a round in progress (BB28 Week
  11's Day 77: Taylor's HOH, nominations and veto) shows up; the validator checks only
  its HOH. With no HOH either, the round isn't modeled. The week's other rounds are
  modeled either way.
- An Evicted cell that isn't a vote tally or a sole vote: `note` /
  `Non-standard outcome: …`. That round isn't modeled.
- A plain eviction round with no HOH: `error`.
- A failed validation check sets `error` and appends `Validation failed: …` to the note.
  Validation runs on every modeled round, including a Finale week's regular round.

## Output shape

`web/weeks.json` is `{schema_version, generated_at, license, sources: [...], weeks: [...], photos: {...}}`. Each entry in
`weeks` is exactly the per-week record from the design doc. `sources` holds each season's
title, URL, revision ID, and a permalink to that revision, which the page uses for
attribution.

`raw` is `{columns: [sub-labels], rows: [{label, cells: [text per sub-column]}]}` and is
filled in only for `note` and `error` weeks.

`footnotes` lists the markers (e.g. `"a"`) from any cell in the week's columns. Their
text is in `details.json`, under each week's `special.notes`.

## Web page

- Seasons are rows. Columns are keyed by week label, with numbered weeks first.
- Each cell names the evicted houseguest. A week with two modeled rounds shows two stacked
  halves.
- `note` and `error` weeks get a folded corner (yellow for `note`, red for `error`), with a
  legend. Each cell's accessible label also states the status, so color isn't the only
  signal.
- The tooltip appears on hover or keyboard focus. Clicking or tapping a week opens its
  details; Escape or the close button closes them.
- `?seasons=26-28` limits the page to some seasons, and `?embed=1` / `?theme=` are for
  embedding (see `docs/integration.md`).
- Light and dark themes are supported.
- The page fetches `weeks.json`, so serve it over HTTP. `file://` won't work.

## Big Brother Wiki (fetched 2026-09-22)

The fan-run Big Brother Wiki (bigbrother.fandom.com) runs MediaWiki 1.43, so it has the same API
as Wikipedia. The sandbox can't reach it either. A one-off GitHub Action first dumped the
eight season pages and every page they link to, so the reader could be written against the
real markup. The regular fetch workflow now fetches both wikis.

**What's fetched** (`bbgrid/fetch.py`, into `cache/fandom/`)
- Each season page, as rendered HTML (tables) and as wikitext (the `{{Season}}` infobox).
- The *lead section* of each houseguest's page, for the `{{Houseguest}}` infobox. The rest
  of each page (biography, game history) isn't kept. The pages come from the season page's
  Houseguests section, 50 per API query, with redirects followed.
- A failed Big Brother Wiki fetch prints a warning and doesn't stop the Wikipedia refresh.

**What's read** (`bbgrid/fandom.py`). Each table is found by its h2 section heading, and
its columns by their header labels, not by position.

| Section | Read as |
|---|---|
| Houseguests | roster: page title + short name ("Jackson Michie" / "Jackson") from each card's bold link |
| Competition History | one row per competition: week, day, type, name, the linked format page, result |
| Have/Have-Not History | Have-Not = a cell with the key's "Have-Not" colour; "+" = HOH; a name in the cell = who gave them the status (the page's own note says so) |
| Game History | HOH, initial noms, veto holder, "Used?" (a Yes!/No! icon's alt text), final noms, evicted |
| `{{Season}}` / `{{Houseguest}}` | infobox fields via `bbgrid/wikitext.py`; a returnee's per-season fields are numbered (`Place2`, `Days2`), matched by `SeasonFullName2` or `Season2` |

- Results read "winners / verb phrase" ("Makensy / wins HOH", "Ashley & Barrett / fail to
  advance"). `won` is true for wins, saves, upgrades, awards and returns.
- `TBA`/`TBD` names and placeholder rows (BB28's unplayed weeks) are dropped.
- BB28's Competition History starts with a row made only of header cells, so the header is
  found by its "Name" label instead of `split_header`.
- BB21 marks weeks before the Have-Not phase "Phase Not Active"; they're skipped.

**Matching names** (`bbgrid/enrich.py`). Each Wikipedia houseguest is matched to one wiki
page in three steps:
1. The same short name, ignoring case, accents, dots, spaces, hyphens and apostrophes
   ("Nicole A." = "Nicole A", "La Trice" = "LaTrice", "Azäh" = "Azah").
2. Otherwise, one whole word of the page title ("Michie" → "Jackson Michie").
3. Otherwise, the start of the page title.

All 131 houseguests match. Every wiki name is then translated through that page. The
initials in BB24's "A&I" (who made a Have-Not) can't be resolved, so they're kept as
written.

**Cross-check.** Each week's Game History rows are paired with Wikipedia's rounds by who
was evicted, or by order when the counts match. HOH, initial noms, veto winner and final
noms are compared as sets. The veto's use is compared with what `details.py` works out.
- In BB26–28, the wiki's final nominations still include the nominee a twist saved (the
  AI Arena or Block Buster winner), while Wikipedia's come after the twist. Names in the
  round's twist rows are left out of that comparison, which removed 25 false alarms.
- 7 disagreements remain, all listed in `report.txt` and under "Sources disagree" on the
  page:
  - BB22 Week 6 and BB23 Week 7: a third initial nominee.
  - BB23 Week 8: two HOHs on Wikipedia.
  - BB25 Week 1: the four Multiverse nominees, and so veto use.
  - BB26 Week 3: America's Veto and the re-nomination.

  They reflect how each wiki records a twist, not parser errors. The grid follows Wikipedia.

**Coverage.** 326 competitions across the eight seasons. Competition names now cover 210 of
the 213 HOH and veto rounds; the episode summaries alone covered about 75%. There are 142
Have-Not entries, and all 131 houseguests have a bio.
