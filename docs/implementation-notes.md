# Implementation notes

This file records choices made while building v1, and assumptions that need checking
against the real pages.

## Not checked against real pages yet

The pipeline was built in a sandbox whose network policy blocks `en.wikipedia.org`.
Nothing here has run on real voting-history tables yet. Step 2 of the suggested order
("inspect each table before writing the interpreter") is still open. To do it:

```sh
python -m bbgrid fetch
python -m bbgrid inspect      # headers, week/sub-column grouping, row-label mapping per season
python -m bbgrid build        # then read report.txt
```

Assumptions to confirm against the `inspect` output:

1. **Table location.** A `<caption>` containing "voting history", or else the first
   `wikitable` after a heading with that text.
2. **Header rows.** The leading rows whose own cells are all `<th>`. Body rows are assumed
   to start with a `<th>` label and contain `<td>` data cells. Week labels come from the
   first header row that has a "Week N" cell. Sub-column labels ("Day 67", "Finale") come
   from the last header row. A week header that spans both header rows has no sub-label.
3. **Label columns.** The columns covered by the top-left corner header cell.
4. **Row sections.**
   - The top summary block runs from the first body row to the last row with a known top
     label (HOH, nominations, veto, final nominations).
   - The bottom block starts at the first `Evicted…` row.
   - The rows in between are houseguest vote rows. A row there whose label contains a
     summary word (winner, nominations, veto, power, saved, evicted) is counted as an
     extra instead.
   - `Notes` and `References` rows are ignored except for their footnote markers.
5. **Evicted cell.** The first line is the evicted name. The remaining lines are joined
   and matched against `X of Y votes to evict` or `<name>'s choice to evict`.
6. **Name lists.** Summary cells are split on line breaks and commas, never on spaces.
   `(none)`, `N/A` and dashes are dropped.

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
- A round with an empty or missing Evicted cell: `note` / `No eviction`, no rounds, raw
  text kept. This covers BB28's in-progress weeks.
- Missing HOH, or an Evicted cell with an unreadable tally: `error`.
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
