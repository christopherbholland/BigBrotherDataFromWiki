"""Read a Big Brother Wiki (Fandom) season page into plain data.

Input is the cached page HTML, its wikitext and the lead sections of the
houseguests' pages (see fetch.py). Output uses the wiki's own names ("Jackson",
"Nicole A", "Derek X"); enrich.py matches them to Wikipedia's houseguests.

Tables read, each found by its section heading:
  Houseguests            roster: each houseguest's page title and short name
  Competition History    every competition: week, day, type, name, result
  Have/Have-Not History  who was a Have-Not each week (cell colour), and who picked them
  Game History           HOH, noms, veto holder, "Used?", final noms, evicted, vote
Infoboxes read from wikitext: {{Season}}, each houseguest's {{Houseguest}}, and
each recurring competition's {{Recurring Competition}} with its opening sentence.
"""
import re
from datetime import date, datetime

from bs4 import BeautifulSoup, Tag

from . import wikitext as wt
from .grid import expand_table, split_header

HAVE_NOT_COLOR = "#cc6666"  # the wiki's Have-Not colour, used when the key table is missing
PLACEHOLDER_RE = re.compile(r"^(tba|tbd|\?+|-+|—)$", re.I)
WEEK_RE = re.compile(r"^\s*(\d+)\s*$")
BG_RE = re.compile(r"background(?:-color)?\s*:\s*(#[0-9a-f]{3,6})\b", re.I)
RESULT_SPLIT_RE = re.compile(r"\s*(?:,|&|\band\b)\s*")
VERB_RE = re.compile(r"^(.*?)\s+((?:wins?|is|are|fails?|returns?|remains?|loses?)\b.*)$", re.I)


def _heading_text(h):
    return re.sub(r"\[\s*\]$", "", h.get_text(" ", strip=True)).strip()


def section_tables(soup, prefix):
    """Top-level tables between the h2 whose text starts with prefix and the next h2."""
    for h in soup.find_all("h2"):
        if _heading_text(h).lower().startswith(prefix.lower()):
            anchor = h.parent if "mw-heading" in (h.parent.get("class") or []) else h
            tables = []
            for el in anchor.find_all_next():
                if not isinstance(el, Tag):
                    continue
                if el.name == "h2" and el is not h:
                    break
                if el.name == "table" and el.find_parent("table") is None:
                    tables.append(el)
            return tables
    return []


def _bg(cell):
    m = BG_RE.search(cell.style or "")
    return m.group(1).lower() if m else None


def _week(text):
    m = WEEK_RE.match(text or "")
    return int(m.group(1)) if m else None


def _clean_name(text):
    """A competition name as shown: quotes and stray spaces removed."""
    text = " ".join((text or "").split())
    return text.strip(' "“”')


def _names(text):
    out = []
    for part in RESULT_SPLIT_RE.split(text or ""):
        part = part.strip()
        if part and not PLACEHOLDER_RE.match(part):
            out.append(part)
    return out


# --- Houseguests ------------------------------------------------------------

def houseguest_links(html):
    """[(page title, short name)] from the Houseguests section, in page order.

    Each houseguest is a card whose bold caption links to their page, e.g.
    <b><a title="Jackson Michie">Jackson</a></b>. Repeats are dropped.
    """
    soup = BeautifulSoup(html, "lxml") if isinstance(html, str) else html
    out, seen = [], set()
    for table in section_tables(soup, "houseguests"):
        for b in table.find_all("b"):
            a = b.find("a", title=True)
            if a is None or a.find("img") or a.get("href", "").startswith("http"):
                continue
            title, short = a["title"], a.get_text(" ", strip=True)
            if title not in seen and short:
                seen.add(title)
                out.append((title, short))
    return out


# --- Competition History ----------------------------------------------------

COMP_COLUMNS = {
    "week": re.compile(r"^week$", re.I),
    "day": re.compile(r"^day", re.I),
    "type": re.compile(r"^type$", re.I),
    "name": re.compile(r"^name$", re.I),
    "result": re.compile(r"^result", re.I),
}


def _column_labels(header_rows, width):
    """Each column's label: the last header row's text there, first line only."""
    last = header_rows[-1] if header_rows else []
    return [(last[c].text.split("\n")[0].strip() if c < len(last) else "") for c in range(width)]


def comp_kind(type_text):
    t = type_text.lower()
    if t.startswith("hoh") or t.endswith("/hoh") or t == "head of household":
        return "hoh"
    if "pov" in t or "veto" in t:
        return "veto"
    return "twist"


def parse_result(cell):
    """(winners, outcome) from a Result cell such as "Makensy / wins HOH"."""
    lines = [x for x in cell.names if x]
    if len(lines) >= 2:
        who, outcome = " ".join(lines[:-1]), lines[-1]
    else:
        m = VERB_RE.match(cell.text or "")
        who, outcome = (m.group(1), m.group(2)) if m else ("", cell.text or "")
    return _names(who), outcome.strip()


def competitions(soup):
    """Every row of the Competition History table.

    Returns [{"week", "day", "type", "kind", "name", "format", "winners",
    "outcome", "result", "extra"}]: kind is "hoh", "veto" or "twist"; format
    is the recurring-competition page the name links to (when it differs from
    the name); extra holds any other columns (e.g. BB25's "Multiverse").
    """
    tables = section_tables(soup, "competition history")
    if not tables:
        return []
    expanded, width = expand_table(tables[0])
    # The header ends at the row labelling the columns ("Week", "Type", "Name", ...).
    # Not split_header: a placeholder row made only of <th> cells can follow it.
    label_row = next((i for i, row in enumerate(expanded[:4])
                      if any(COMP_COLUMNS["name"].search(c.text) for c in row)), None)
    if label_row is None:
        return []
    header, body = expanded[:label_row + 1], expanded[label_row + 1:]
    labels = _column_labels(header, width)
    cols = {}
    for c, label in enumerate(labels):
        for key, pat in COMP_COLUMNS.items():
            if key not in cols and pat.search(label):
                cols[key] = c
    if not {"week", "type", "name", "result"} <= set(cols):
        return []
    known = set(cols.values())
    out, week = [], None
    for row in body:
        week = _week(row[cols["week"]].text) or week
        name_cell, result_cell = row[cols["name"]], row[cols["result"]]
        name = _clean_name(name_cell.text)
        winners, outcome = parse_result(result_cell)
        if (not name or PLACEHOLDER_RE.match(name)) and not winners:
            continue  # an empty placeholder row, or one not played yet
        fmt = next((t for t in name_cell.links if t.casefold() != name.casefold()), None)
        type_lines = row[cols["type"]].names or [""]
        out.append({
            "week": week,
            "day": row[cols["day"]].text.replace("\n", " ") if "day" in cols else None,
            "type": " ".join(type_lines),
            "kind": comp_kind(type_lines[0]),
            "name": name if name and not PLACEHOLDER_RE.match(name) else None,
            "format": fmt,
            "winners": winners,
            "outcome": outcome,
            "result": " ".join(result_cell.names),
            "extra": {labels[c]: row[c].text.replace("\n", " ") for c in range(width)
                      if c not in known and labels[c] and row[c].text},
        })
    return out


# --- Have/Have-Not History --------------------------------------------------

def _key_colors(tables):
    """{"have": colour, "have-not": colour} from the section's key table, if present."""
    colors = {}
    for table in tables[1:]:
        expanded, _ = expand_table(table)
        for row in expanded:
            for cell in row:
                label = cell.text.strip().lower()
                if label in ("have", "have-not") and _bg(cell):
                    colors[label] = _bg(cell)
    return colors


def have_nots(soup):
    """{week: [{"guest": page title, "chosen_by": short name or None}]} plus HOHs.

    Returns {"weeks": {...}, "hoh": {week: [page titles]}}. A cell coloured
    as "Have-Not" in the key marks a Have-Not; a name in the cell is who gave
    them the status (the page's own note says so). "+" marks the week's HOH.
    Weeks shown as "Phase Not Active" have no entry.
    """
    tables = section_tables(soup, "have/have-not")
    if not tables:
        return {"weeks": {}, "hoh": {}}
    table = tables[0]
    first = table.find("tr")
    guests = []
    for cell in first.find_all(["td", "th"], recursive=False)[1:]:
        a = cell.find("a", title=True)
        guests.append(a["title"] if a else None)
    color = _key_colors(tables).get("have-not", HAVE_NOT_COLOR)
    expanded, _ = expand_table(table)
    weeks, hohs = {}, {}
    for row in expanded[1:]:
        week = _week(row[0].text)
        if week is None:
            continue
        for guest, cell in zip(guests, row[1:]):
            if guest is None:
                continue
            if cell.text.strip() == "+":
                hohs.setdefault(week, [])
                if guest not in hohs[week]:
                    hohs[week].append(guest)
            elif _bg(cell) == color:
                entries = weeks.setdefault(week, [])
                if all(e["guest"] != guest for e in entries):
                    text = cell.text.strip()
                    entries.append({"guest": guest, "chosen_by": text or None})
    return {"weeks": weeks, "hoh": hohs}


# --- Game History -----------------------------------------------------------

GAME_COLUMNS = [
    ("hoh", re.compile(r"^hoh\b", re.I)),
    ("nominees_initial", re.compile(r"^initial\b", re.I)),
    ("veto_holders", re.compile(r"^veto\b", re.I)),
    ("veto_used", re.compile(r"^used\b", re.I)),
    ("nominees_final", re.compile(r"^final\b", re.I)),
    ("evicted", re.compile(r"^evicted\b", re.I)),
    ("vote", re.compile(r"^vote\b", re.I)),
    ("finish", re.compile(r"^finish\b", re.I)),
]


def _cell_values(row, columns):
    """Distinct non-empty cells across a column group, left to right."""
    seen, out = set(), []
    for c in columns:
        cell = row[c]
        if id(cell) in seen:
            continue
        seen.add(id(cell))
        if cell.text or cell.images:
            out.append(cell)
    return out


def game_history(soup):
    """One entry per row of the Game History table (a week can have several).

    Each: {"week", "hoh", "nominees_initial", "veto_holders", "veto_used",
    "nominees_final", "evicted", "vote", "finish", "other": {label: [names]}}.
    veto_used is True/False from the "Yes!"/"No!" icon, None when blank.
    """
    tables = [t for t in section_tables(soup, "game history") if "wikitable" in (t.get("class") or [])]
    if not tables:
        return []
    expanded, width = expand_table(tables[0])
    header, body = split_header(expanded)
    # The label is the full header text ("Initial Nominations"), joined across lines.
    top = header[0] if header else []
    labels = [" ".join((top[c].text if c < len(top) else "").split()) for c in range(width)]
    groups, other = {}, {}
    for c, label in enumerate(labels[1:], 1):
        key = next((k for k, pat in GAME_COLUMNS if pat.search(label)), None)
        if key:
            groups.setdefault(key, []).append(c)
        elif label:
            other.setdefault(label, []).append(c)
    out = []
    for row in body:
        week = _week(row[0].text)
        if week is None:
            continue

        def names(key):
            return [n for cell in _cell_values(row, groups.get(key, [])) for n in _names(cell.text.replace("\n", ", "))]

        def text(key):
            cells = _cell_values(row, groups.get(key, []))
            return " ".join(cell.text.replace("\n", " ") for cell in cells) or None

        used = None
        for cell in _cell_values(row, groups.get("veto_used", [])):
            flag = " ".join(cell.images + [cell.text]).lower()
            if "yes" in flag:
                used = True
            elif "no" in flag:
                used = False
        out.append({
            "week": week,
            "hoh": names("hoh"),
            "nominees_initial": names("nominees_initial"),
            "veto_holders": names("veto_holders"),
            "veto_used": used,
            "nominees_final": names("nominees_final"),
            "evicted": names("evicted"),
            "vote": text("vote"),
            "finish": text("finish"),
            "other": {label: [n for cell in _cell_values(row, cs) for n in _names(cell.text.replace("\n", ", "))]
                      for label, cs in other.items() if _cell_values(row, cs)},
        })
    return out


# --- Infoboxes --------------------------------------------------------------

def _date(text):
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            pass
    return None


def season_info(wikitext):
    """Fields from the {{Season}} infobox, as display text (None if absent)."""
    p = wt.template_params(wikitext or "", "Season")
    if p is None:
        return None
    run = wt.plain(p.get("seasonrun", ""))
    start_text, _, end_text = run.partition(" - ")
    start, end = _date(start_text) if start_text else None, _date(end_text) if end_text else None

    def field(key):
        return wt.plain(p.get(key, "")) or None
    return {
        "season_run": run or None,
        "premiere": start.isoformat() if start else None,
        "finale": end.isoformat() if end else None,
        "days": field("numberofdays"),
        "houseguests": field("numberofhouseguests"),
        "episodes": field("numberofepisodes"),
        "prize": field("prizemoney"),
        "winner": field("winner"),
        "runner_up": field("runnersup"),
        "host": field("host"),
        "average_viewers": field("viewership"),
    }


def _season_suffix(params, season):
    """The field suffix ("", "2", "3", ...) for this season in a multi-season infobox."""
    want = f"big brother {season} (us)"
    for key, value in params.items():
        m = re.match(r"^(SeasonFullName|Season)(\d*)$", key)
        if not m:
            continue
        text = wt.plain(value).lower()
        if text == want or text == f"{season} (us)":
            return m.group(2)
    return None


def age_on(born, day):
    if not born or not day:
        return None
    return day.year - born.year - ((day.month, day.day) < (born.month, born.day))


def houseguest_bio(title, lead, season, premiere=None):
    """A houseguest's infobox fields for one season, or None if there's no infobox.

    Returns {"page", "full_name", "birth_date", "age", "hometown", "occupation",
    "nickname", "place", "days", "alliances", "other_prizes", "seasons"}. age is
    at the season premiere. The per-season fields come from the infobox's
    numbered fields (Place2, Days2, ...) for the matching season.
    """
    p = wt.template_params(lead or "", "Houseguest")
    if p is None:
        return None
    suffix = _season_suffix(p, season)

    def field(key, per_season=False):
        if per_season:
            if suffix is None:
                return None
            key += suffix
        return p.get(key)
    born = wt.birth_date(p.get("birthdate", ""))
    premiere_day = date.fromisoformat(premiere) if premiere else None
    seasons = []
    for key, value in p.items():
        if re.match(r"^(SeasonFullName|Season)\d*$", key) and wt.plain(value):
            label = wt.plain(value)
            seasons.append(label if label.lower().startswith("big brother") else f"Big Brother {label}")
    place = wt.plain(field("Place", True) or "") or None
    return {
        "page": title,
        "full_name": wt.bold_lead(lead) or title,
        "birth_date": born.isoformat() if born else None,
        "age": age_on(born, premiere_day),
        "hometown": wt.lines(p.get("hometown", "")),
        "occupation": wt.plain(p.get("occupation", "")) or None,
        "nickname": wt.lines(p.get("nickname", "")),
        "place": place,
        "days": wt.plain(field("Days", True) or "") or None,
        "alliances": wt.links(field("Alliances", True) or "") or wt.lines(field("Alliances", True) or ""),
        "other_prizes": wt.lines(field("OtherPrizes", True) or ""),
        "seasons": seasons,
    }


# --- Recurring competition (format) pages ----------------------------------

# The opening sentence names the type: "... is a recurring endurance [[Head of Household]] ...".
FORMAT_TYPE_WORDS = [
    ("Endurance", re.compile(r"\bendurance\b", re.I)),
    ("Puzzle", re.compile(r"\bpuzzle\b", re.I)),
    ("Mental", re.compile(r"\b(mental|trivia|memory|quiz|knowledge|question|counting)\b", re.I)),
    ("Crapshoot", re.compile(r"\b(luck|luck-based|chance|crapshoot|random)\b", re.I)),
    ("Physical", re.compile(r"\b(physical|skill|speed|agility|aim|obstacle|athletic)\b", re.I)),
]
OPENING_RE = re.compile(r"\bis (?:a|an|the)\b(.*?)(?:\[\[|\bcompetition\b|\.)", re.I | re.S)


def format_info(lead):
    """{"description", "category"} from a competition format page's lead, or None.

    description: the infobox's one-line summary ("Hang on to a moving wall as
    long as you can."). category: from the type word in the opening sentence,
    one of comps.CATEGORIES, or None when the sentence names none.
    """
    if not lead:
        return None
    p = wt.template_params(lead, "Recurring Competition") or {}
    body = lead
    m = re.search(r"\{\{\s*Recurring Competition", lead, re.I)
    if m:
        inner = wt._template_body(lead, m.start())
        if inner is not None:
            body = lead[m.start() + len(inner) + 4:]
    opening = OPENING_RE.search(wt.COMMENT_RE.sub("", body))
    words = opening.group(1) if opening else ""
    category = next((cat for cat, pat in FORMAT_TYPE_WORDS if pat.search(words)), None)
    return {"description": wt.plain(p.get("description", "")) or None, "category": category}


# --- Everything for one season ----------------------------------------------

def parse_season(cached, season):
    """All of the above for one cached season (see fetch.load_fandom_cached)."""
    soup = BeautifulSoup(cached["html"], "lxml")
    info = season_info(cached.get("wikitext", ""))
    premiere = info["premiere"] if info else None
    roster = houseguest_links(soup)
    leads = cached.get("houseguests", {})
    bios = {}
    for title, _ in roster:
        entry = leads.get(title)
        bio = houseguest_bio(title, entry["lead"], season, premiere) if entry else None
        if bio:
            bio["revid"] = entry.get("revid")
            bios[title] = bio
    formats = {}
    for title, entry in (cached.get("formats") or {}).items():
        info_ = format_info(entry.get("lead"))
        if info_:
            formats[title] = {**info_, "revid": entry.get("revid")}
    return {
        "info": info,
        "formats": formats,
        "roster": roster,
        "competitions": competitions(soup),
        "have_nots": have_nots(soup),
        "game": game_history(soup),
        "bios": bios,
    }
