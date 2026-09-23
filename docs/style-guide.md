# Style guide

How `web/index.html` looks and reads, and how to change it without drifting. The page
is one file: the `<style>` block at the top has three parts, in this order:

1. **Tokens.** Every color, font size, weight, letter spacing, radius, shadow and
   spacing step is a custom property on `:root`.
2. **Base and shared components.** Section headings, cards, chips, stat tiles,
   controls, tables and faces. New UI starts from these.
3. **Views.** Layout for each tab, written with the tokens only.

`tests/test_style.py` runs with the rest of the tests (`pytest -q`, and in CI) and fails
when a rule skips the tokens. The table under [What the test checks](#what-the-test-checks)
lists its rules.

## Tokens

### Color

Use the role, never the hex. Each token has a light value and a dark one.

| Token | Use |
|---|---|
| `--surface-0` | page background; the fill inside cards, stat tiles and quotes |
| `--surface-1` | panels, the drawer, pinned table columns |
| `--cell` / `--cell-hover` | grid cells, control tracks, unfilled chips and badges |
| `--line` | every border and rule |
| `--text-primary` / `--text-secondary` / `--text-muted` | body text / labels and supporting text / fine print, zeros, sources |
| `--accent` | the selected tab, HOH, the "now" pill, focus rings, live faces |
| `--good` | veto, winning counts |
| `--warning` | twist-week flags, nominations (mixed to 32%) |
| `--critical` | failed checks, evictions |
| `--gold` / `--silver` / `--bronze` | winners, first to third place |
| `--now` | the outline on the week that's airing |
| `--cat-*`, `--out-*` | chart series only (comp types, what the veto did). Validated as a set, so don't add one without re-checking the whole palette in both themes. |

**Text on a fill** uses the fill's on-color: `--on-accent`, `--on-good`, `--on-critical`,
`--on-gold`, `--on-silver`, `--on-bronze`, and `--on-series` / `--on-series-light` for
labels on chart segments. A new fill gets a new on-color token.

**Overlays:** `--scrim`, `--shadow-raised` (the pressed segment), `--shadow-drawer`, `--tip-shadow`.

**Dark mode** has two identical blocks: `@media (prefers-color-scheme: dark)` follows
the system, and `:root[data-theme="dark"]` is `?theme=dark`. Change both. The test
fails if they differ, or if a token exists only in dark mode.

### Type

One family (`--font`, the system UI font). Ten sizes:

| Token | px | Use |
|---|---|---|
| `--fs-3xs` | 10 | initials on the smallest faces; table group labels; drawer table heads |
| `--fs-2xs` | 11 | caps labels (table heads, placings), chips, the "now" pill, fine print under a name |
| `--fs-xs` | 12 | section headings, legends, sources, secondary lines |
| `--fs-sm` | 13 | tables, notes, controls, grid cells |
| `--fs-md` | 14 | body text, the drawer |
| `--fs-lg` | 15 | ledes, card titles, a comp format's description |
| `--fs-xl` | 17 | names on cards, count badges, the drawer title |
| `--fs-2xl` | 22 | the page title, stat numbers |
| `--fs-3xl` | 28 | initials on portrait faces, the phone jury score |
| `--fs-4xl` | 40 | the jury score |

**Simple view** (`?simple=1`, the stream view) redefines every `--fs-*` token larger
in the `:root.simple` block, from 12px up to 48px. A new size token gets a value there
too. Its layout rules (bigger cells and faces, what it hides) sit with the embed rules
in the Views part.

Weights: `--fw-regular` (400), `--fw-semibold` (600, controls and grid cells),
`--fw-bold` (700, names and caps labels), `--fw-heavy` (800, big numbers and badges).

Letter spacing: `--track-caps` (.08em) on **every** uppercase label, `--track-tight`
(.02em) on the pill and season labels, otherwise `0`. Uppercase text always comes from
the shared **caps label** rule; add your selector to it instead of writing
`text-transform` again.

### Shape

| Token | px | Use |
|---|---|---|
| `--r-xs` | 2 | legend swatches |
| `--r-sm` | 4 | small faces (under 28px), bar ends, the pill |
| `--r-md` | 6 | faces, buttons inside a control, badges |
| `--r-lg` | 8 | panels, control tracks, the tooltip, stat tiles, the drawer's close button |
| `--r-xl` | 10 | cards, portrait faces |
| `--r-sheet` | 14 | the phone bottom sheet's top corners |
| `--r-pill` | 999 | chips |

Nested corners step down one size: a `--r-lg` track holds `--r-md` buttons.

### Space

A 4px scale: `--sp-1` 4, `--sp-2` 8, `--sp-3` 12, `--sp-4` 16, `--sp-5` 20, `--sp-6` 24.
`--inset` is the side padding inside a panel: 16px, and 12px on phones. Use it for
anything that lines up with a panel's edge.
Tight component internals (a chip's 7px, a badge's 3px 9px) may be off-scale; spacing
between things should be on it.

### Breakpoints

| Width | What changes |
|---|---|
| ≤ 900px | the leaders strip scrolls sideways |
| ≤ 640px (phone) | tabs become two rows of four; pickers wrap; the drawer becomes a bottom sheet; `--inset` drops to 12px; tables' name column hides full names |
| ≤ 400px | the drawer portrait shrinks |

Check every change at 390px wide as well as on a desktop.

## Components

Reach for these before writing a new rule. Each is one rule (or one selector list) in
the "Base and shared components" part of the stylesheet. To give an existing element
the same look, add its selector to that list.

| Component | Markup | Notes |
|---|---|---|
| Page header | `.kicker`, `h1` + `.pill`, `.sub` | Title and intro change with the tab (`VIEWS` in the script). |
| View tabs | `.tabs` > `button[role=tab]` | Eight tabs make two rows of four on phones. A ninth adds a third row, so rethink the labels first. |
| Simple view toggle | `#simple-btn` in a `.seg`, after `.tabs` | Adds or removes `?simple=1` in the address. `?embed=1&simple=1` hides the whole toolbar and the `.controls`. |
| Picker / toggle | `.seg` > `button[aria-pressed]` (or a `select`) | Every secondary control, season pickers included. Wraps on phones. |
| Panel | `.panel` | The box each tab renders into. Tables go straight inside. |
| Panel body | `.view-body` | Pads a panel of prose, charts and sections (Finale, Endgame, HOH, Veto). |
| Section heading | `<h2>` in `.view-body`, `<h3>` in the drawer | 12px caps with a rule above; the first one has no rule. A `.note` right under it explains the section. |
| Subheading | `<h4>` in the drawer | A round or part within a section. |
| Lede | `.lede` / `.fin-lede` / `.lead` | One or two 15px sentences that sum up the view. |
| Card | `.board-col`, `.eg-round`, `.afh-card`, `.leaders li` | `--surface-0` fill, `--line` border, `--r-xl`. The winner's card has a gold border (`.win` / `.won`). |
| Stat tile | `.stats` > `.stat` > `b`, `span`, optional `small` | A big number, what it counts, and its context. |
| Count badge | `.n` in a card or leader row | Filled `--good` for the winner or leader, `--cell` otherwise. |
| Chip | `.tag` (outlined), `.cat` (comp type), `.t` + role | `.t` roles: `hoh`, `veto`, `nom`, `out`, `dec` (decided it), `won`. Legend: `.t-legend`. |
| Data table | `table.players` | Numbers right-aligned and tabular; the first column is pinned; `.l` left-aligns a text column; `.grp` row for grouped heads. `table.plays` is the compact version for the drawer. |
| Face | `faceHtml()` → `.face` | 4:5 photo or initials. `.out` greyed, `.live` accent ring, `.won` gold ring. Sizes: 20–26px in rows and chips (`--r-sm`), 28–36px in tables and cards, 72–104px as a portrait (`--r-xl`). A season whose large portraits are full-length (BB28) gets an entry in `PORTRAIT_ZOOM`, which zooms toward the head so the face fills the frame. Check a new season's portraits and add it there if needed. |
| Placing | `roleHtml(text)` → `.role` | The caps line under a portrait ("Winner", "3rd place", "Still in the game"). It wraps like any label; the helper keeps "Runner-up" on one line. Never set `nowrap` on it: four cards on a phone leave about 80px each. |
| Icon | `iconHtml("hoh" \| "veto")` → `svg.icon` | The HOH key and the veto medal, drawn in `currentColor`. Used in place of the words where space is tight: chips in the Endgame power table (`.t.hoh.icon-only`, `.t.veto.icon-only`) and column heads (`thIcon()`). Always pair one with a legend or a `title`, plus `.sr` text for screen readers. Prose keeps the words. |
| Name link | `plink()` → `a.plink` | Every houseguest or season name in text links to their details. |
| Legend | `.key` (series colors), `.legend` (grid marks), `.t-legend` (chips) | Sits above the chart or table it explains. |
| Small print | `.voters`, `.src`, `.note`, `.muted` | `.src` names the source of the data under a section, and every section with data has one. |
| Quote | `blockquote.wnote` + `cite` | A wiki's own words, with the page and wiki it came from. |
| Utilities | `.grow`, `.tight`, `.mt-2`, `.mt-3`, `.sr` | Use these instead of a `style=""` attribute. |

## Writing

- **Sentence case** everywhere: titles, headings, buttons ("Most competition wins", "From final 5").
- **Plain words, the show's terms:** HOH, veto, nominee, backdoor, jury, "evicted",
  "the block". Spell a term out once in the view's intro (`Head of Household`).
- **Names** as the show uses them ("BB26", "Week 10", "Day 67", "Final 4"). The first
  mention in running text is a link.
- **Separators:** a middle dot with spaces between facts (`Week 11 · Day 80`), an en dash
  in scores and ranges (`7–0`, `BB21–BB28`), `×` for counts (`Vince ×4`).
- **Typography:** curly quotes and apostrophes (`’`, `“ ”`), a real ellipsis (`…`),
  and `–` for "none".
- **Empty states** say what's missing and when it will appear ("Not named yet: the
  favorite is announced at the finale.").
- **Instructions** say "Click or tap".
- **Never show pipeline wording.** Notes in `weeks.json` are written for `report.txt`
  ("Finale; Two evictions", "Non-standard outcome: …"). The page rewrites them as
  plain phrases (`statusText()`: "Finale week · two evictions", "Cliff won re-entry
  into the game"), without labels like "Note:" or "Error:". A new kind of note gets a
  case in `notePhrase()`.

## Recipes

**Add a section to a view.** Emit `<h2>Title</h2><p class="note">What it shows.</p>`
inside the view's `.view-body`, then the content (a `.scroll`-wrapped `table.players`,
a `.board` of cards, `.stats`), and end with a `.src` line naming the source.

**Add a tab.** Add a `button[role=tab]` to `.tabs`, a `<section role="tabpanel">` with
`.controls` (a `.seg` season picker) and a `.panel`, an entry in `VIEWS` (title, intro,
hash, `show`), and render into `<div class="view-body">`. Add a shot to
`tools/screenshots.py`.

**Need a new value?** First check whether an existing token fits, since two nearly
equal sizes are a drift. If none does, add a token with a comment saying what it's for,
add it to the table above, and (for colors) give it a dark value in both dark blocks.

**Restyle something everywhere** by changing the token or the shared component rule,
not the places that use it.

**Before pushing** run `pytest -q` and look at the change at desktop and 390px, in light
and dark (`?theme=dark`), and in the simple view (`?simple=1`) if it's on the Weeks tab. If it shows in the README's screenshots, run
`python tools/screenshots.py` to retake them.

## What the test checks

`tests/test_style.py`, against `web/index.html`:

| Rule | Allowed |
|---|---|
| Colors | hex, `rgb()` and `hsl()` only inside custom properties; none in the script |
| `font-size`, `font` | a `--fs-*` token (`font: inherit` is fine) |
| `font-weight` | a `--fw-*` token |
| `letter-spacing` | a `--track-*` token or `0` |
| `border-radius` | `--r-*` tokens or `0`, per corner |
| `var(--name)` | must be defined (catches typos) |
| Dark mode | the two dark blocks match; light defines every dark token |
| `style=""` | only data: `background`, `width`, `height` or a custom property |

Spacing isn't checked, so keep to the scale by review.
