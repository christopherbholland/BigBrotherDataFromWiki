# Copyright and licensing review

A check of how this project uses other people's material, done 2026-09-23. It isn't legal
advice. It's a reading of the licenses against what the code actually copies, links and
shows. The notice for people reusing the data is [`DATA_LICENSE.md`](../DATA_LICENSE.md).

## Summary

| Material | Where it comes from | License | How it's used | Status |
|---|---|---|---|---|
| Voting tables, episode summaries, footnotes, cast table | Wikipedia | CC BY-SA 4.0 | Copied into `cache/`, extracted into `web/*.json`, shown on the page | OK: credited and linked per season, and the data is now marked CC BY-SA 4.0 |
| Season, houseguest and competition-format pages | Big Brother Wiki (Fandom) | CC BY-SA 3.0 | Same | OK: credited and linked where used; 3.0 lets adaptations use 4.0 |
| Houseguest photos | CBS promotional images, hosted by the Big Brother Wiki | All rights reserved | Linked (hotlinked), not copied | Gray area (see below) |
| Facts: who won, who was evicted, vote counts | Both wikis | Facts aren't copyrightable | Extracted | OK |
| The name *Big Brother* | Banijay (format owner), CBS (US broadcaster) | Trademark | Used to describe the show | OK: descriptive use, with a no-affiliation line |
| The MediaWiki APIs | Wikimedia, Fandom | Terms of use | Read once a day with an identifying User-Agent | OK for Wikipedia; see below for Fandom |

## What each license asks, and how it's met

CC BY-SA (4.0 for Wikipedia, 3.0 for the Big Brother Wiki) asks for four things:

1. **Credit, with a link to the source.** The page footer links each season's article on
   both wikis at the exact revision used. Each player's details link their Big Brother
   Wiki profile, and each competition format links its page. The episode summaries and
   footnotes shown in a week's details come from that season's Wikipedia article, which
   the footer credits. Wikimedia's terms accept a link to the article as credit to its
   authors. **Met.**
2. **A link to the license.** The footer links CC BY-SA 4.0 and 3.0, and the JSON files'
   `license` field names both. **Met.**
3. **Say what was changed.** *Fixed in this review.* The footer now says the data is
   "rearranged and summarized from these pages", and `DATA_LICENSE.md` describes the
   changes.
4. **Share alike.** Anything adapted from the wikis must be shared under the same license.
   The JSON files, the proofreading workbook, the cached pages and the text shown on the
   page are all adaptations or copies. *Fixed in this review:* the repository had no
   license at all, which meant the adapted data wasn't offered under CC BY-SA. It is now,
   through `DATA_LICENSE.md`, the JSON `license` field, the workbook's read-me sheet and
   the page footer.

Mixing the two: the Big Brother Wiki's CC BY-SA 3.0 (section 4(b)) allows adaptations to be
licensed under "a later version of this License with the same License Elements", so
sharing the combined data under CC BY-SA 4.0 is allowed. The credit for the wiki's material
still names the wiki and its 3.0 license, which the footer does.

## Houseguest photos (the gray area)

The photos are CBS promotional headshots. The Big Brother Wiki hosts them, but they aren't
under its CC license. What the project does:

- The page shows them by linking to the wiki's image server (hotlinking). It never copies
  them into the repository, and the JSON files hold only their URLs. This is the safer
  side of the gray area, but not risk-free.
- The page's `<img>` tags send no referrer (`referrerpolicy="no-referrer"`). That's good for
  viewers' privacy. It also means the wiki can't tell where the requests come from, and
  some image hosts treat that as a way around hotlink protection. If Fandom objects, the
  simplest fix is turning the photos off by default.
- The page credits them ("Houseguest photos: CBS, via the Big Brother Wiki").
- **The README screenshots don't include them.** They're taken with the image server
  blocked, so houseguests show as initials. A screenshot with the photos in it would be a
  copy of CBS's images inside this repository, which is a different thing from linking.
  `tools/screenshots.py` blocks them for that reason.

Options if you ever want to be more careful: turn the photos off by default (the
**Photos** button already exists; flip its default in `web/index.html`), or only show them
on a player's own page.

## Other things checked

- **Episode summaries are long quotations.** They're copied verbatim from Wikipedia, which
  CC BY-SA allows with credit. If Wikipedia's own summaries ever copy CBS's press text
  (it happens, and editors remove it when noticed), that's inherited from the source. A
  refresh picks up Wikipedia's fix.
- **Wikimedia API rules.** The fetcher sends a User-Agent that names the project and links
  the repository, makes one request at a time, and runs once a day. That follows
  Wikimedia's User-Agent policy and API etiquette.
- **Fandom's terms.** The fetcher uses Fandom's public MediaWiki API with the same
  User-Agent and a pause between requests. Fandom's Terms of Use couldn't be read from
  the environment this review ran in (the site was blocked). Worth reading yourself,
  especially on automated access and image hotlinking.
- **Personal information.** The data includes houseguests' full names, birth dates,
  hometowns and occupations, all from the public wikis. That isn't a copyright issue, and
  they're public figures in this context. If someone asks for their details to be removed,
  the Big Brother Wiki reader (`bbgrid/fandom.py`, `houseguest_bio`) is where to drop a
  field.
- **The page itself** loads no outside fonts, scripts or trackers. Its only outside
  requests are the photos.
- **The code has no license.** That's your choice to make. Without one, others can read
  the code but have no right to reuse it. If you want it reusable, a permissive license
  such as MIT for the code sits fine alongside CC BY-SA for the data. Code licenses and
  CC BY-SA are kept apart on purpose, which is why `DATA_LICENSE.md` leaves the code out.

## Keeping it right

- Keep the footer's credit lines and license links. `docs/integration.md` already asks
  embedders not to hide them.
- A new source (another wiki, a stats site) needs its license checked before its text goes
  into `web/*.json`. Facts alone are fine; copied text brings its license along.
- Don't commit anything containing the photos: screenshots, cached images or exported
  sheets.
