# Implementation notes

This file records choices made while building v1 and what the real tables showed.

## What the real tables showed (fetched 2026-09-22)

All eight pages were fetched by the "Fetch Wikipedia pages" GitHub Action, because the
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
- Tally text is always `X of Y votes to evict` or `<name>'s choice to evict`.

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
   other round in the same week is still modeled. The same goes for a round with an empty
   `Evicted` cell, which covers a double eviction that's half finished. The six cases:
   - BB21 Week 1, Day 1: David, "Evicted by competition"
   - BB21 Week 3, Comeback: Cliff, "Won re-entry into game"
   - BB24 Week 1: "Eviction cancelled"
   - BB25 Week 8: Cameron, "Won re-entry into game"
   - BB27 Week 9, Day 59: Rachel, "Eliminated by competition"
   - BB28 Week 8, Day 52: Haley, "Yash's choice to eliminate"

**Things to know about the data**
- A "Double eviction" note means two sub-columns under one week. Not all of them are
  double evictions in the TV sense. BB24 Week 7's columns are "Inside" and "Outside" (the
  split-house twist), and BB21 Week 1 and BB27 and BB28's early two-column weeks are
  competition-elimination twists. The note is accurate about the table's layout. If
  "Double eviction" wording matters for these weeks, a generic fix would be to use the
  note only when both sub-labels are "Day N".
- BB25's last week has three columns (Day 94, Day 100, Finale): two sole-vote rounds plus
  the Finale.
- BB28 was still airing when fetched. Week 11's second round and Week 12 have no
  eviction yet. BB28's caption on Wikipedia reads "Big Brother 26 voting history", a
  mistake on the page itself that doesn't affect parsing.

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
- Two non-Finale sub-columns: two rounds, `ok`, note `Double eviction`.
- A Finale sub-column is never a round. It sets `note` / `Finale`, and the week's regular
  column is still modeled as a round and validated.
- Three or more non-Finale sub-columns: `note`, no rounds, raw text kept.
- A round with an empty or missing Evicted cell: `note` / `No eviction`. That round isn't
  modeled, but the week's other rounds are. This covers BB28's in-progress weeks.
- An Evicted cell that isn't a vote tally or a sole vote: `note` /
  `Non-standard outcome: …`. That round isn't modeled.
- A plain eviction round with no HOH: `error`.
- A failed validation check sets `error` and appends `Validation failed: …` to the note.
  Validation runs on every modeled round, including a Finale week's regular round.

## Output shape

`web/weeks.json` is `{generated_at, license, sources: [...], weeks: [...]}`. Each entry in
`weeks` is exactly the per-week record from the design doc. `sources` holds each season's
title, URL, revision ID, and a permalink to that revision, which the page uses for
attribution.

`raw` is `{columns: [sub-labels], rows: [{label, cells: [text per sub-column]}]}` and is
filled in only for `note` and `error` weeks.

`footnotes` lists the markers (e.g. `"a"`) from any cell in the week's columns. The
footnote text itself isn't extracted in v1.

## Web page

- Seasons are rows. Columns are keyed by week label, with numbered weeks first.
- Each cell names the evicted houseguest. A double eviction shows two stacked halves.
- `note` and `error` weeks get an icon badge (`!` / `×`) with a legend. Color is never the
  only signal.
- The tooltip appears on hover or keyboard focus, and clicking pins it (useful on touch).
  Escape or clicking outside closes it.
- Light and dark themes are supported.
- The page fetches `weeks.json`, so serve it over HTTP. `file://` won't work.
