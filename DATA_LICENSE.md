# Data license

The data in this repository is adapted from two wikis and shared under the
**[Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/)**
license (CC BY-SA 4.0). This covers:

- `web/weeks.json`, `web/details.json`, and the text the page in `web/` shows
- `proofread.xlsx` and `report.txt`
- the cached copies of the source pages in `cache/`
- `tests/snapshots/`

## Sources

- **Wikipedia**, the "Big Brother N (American season)" articles, under
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Each season's article and
  the exact revision used are listed in `web/weeks.json` (`sources[].url` and
  `sources[].permalink`) and linked from the page footer. The authors are listed in each
  article's history.
- **The Big Brother Wiki** ([bigbrother.fandom.com](https://bigbrother.fandom.com/)), the
  season pages plus the houseguest and competition-format pages they link to, under
  [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Season pages and
  revisions are in `sources[].fandom`. Houseguest and format pages are in `details.json`
  (`players[].fandom.url`, `formats[].url`) and linked from the page where they're used.
  CC BY-SA 3.0 lets adaptations be shared under a later version of the license, which is
  why the combined data uses 4.0.

## Changes made

The wiki tables and text were extracted, reorganized by season and week, and summarized:
counts, vote tallies, veto use and competition types are worked out from the tables.
Episode summaries, footnotes, competition descriptions and houseguest bios are quoted as
the wikis wrote them. The cached pages in `cache/` are unmodified copies (only the
houseguest and format pages are trimmed to their opening section).

## Not covered

- **Houseguest photos.** They're CBS promotional images. This repository doesn't contain
  them: the page and the data link to where the Big Brother Wiki hosts them. They aren't
  covered by the CC license.
- **The code** in `bbgrid/`, `tests/` (other than `tests/snapshots/`), `web/index.html`'s
  markup and script, and the workflows. They're not covered by this data license.
- **Trademarks.** *Big Brother* and related names are trademarks of their owners. This
  project isn't affiliated with or endorsed by CBS, Banijay, or the show's producers.

## Reusing the data

Credit Wikipedia and the Big Brother Wiki, link the source pages (the permalinks above
work), say that you changed the material if you did, and share what you make from it under
CC BY-SA 4.0. The page's footer is an example of the credit.
