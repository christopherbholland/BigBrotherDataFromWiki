"""America's Favorite HouseGuest: the viewers' vote, from the season's Wikipedia page.

The winner comes from the page's infobox ("America's Favorite HouseGuest | Nicole
Anthony"). The page's own sentences about the vote are kept as written: the lead,
the Prizes section and the finale's episode summary say who else placed ("The top
3 ... were revealed to be Angela, Tucker and Quinn", "with Derek X. as runner-up")
and sometimes the share of the vote. The Big Brother Wiki's houseguest pages list
the award under the winner's other prizes ("$50,000 (Fan Favorite)"), which gives
the prize and a cross-check (see check()).
"""
import re

from bs4 import BeautifulSoup

from .util import norm, split_sentences

LABEL_RE = re.compile(r"america['’]?s\s+favou?rite\s+house\s*guest", re.I)
MENTION_RE = re.compile(r"america['’]?s\s+favou?rite\s+house\s*guest|\bAF[HP]\b|fan favou?rite", re.I)
# The Format section's description of the award, which names no one.
GENERIC_RE = re.compile(r"able to award|eligible|is held to determine|receives \$|is worth|increased", re.I)
TOP_RE = re.compile(r"\btop\s+(?:3|three)\b", re.I)
RUNNER_UP_RE = re.compile(r"\bwith\s+(.+?)\s+(?:as|being)\s+(?:the\s+)?(?:runner-up|next closest)", re.I)
MONEY_RE = re.compile(r"\$\d[\d,]*")
# The award's own amount: "winning the $25,000 prize", "received $25,000", not a running total.
PRIZE_RE = re.compile(r"\b(?:winning|won|received|receives|and)\s+(?:the\s+)?(\$\d[\d,]*)(?!\s*total)", re.I)
PRIZE_LINE_RE = re.compile(r"fan favou?rite|favou?rite house\s*guest", re.I)


def infobox_winner(soup):
    """The infobox's "America's Favorite HouseGuest" row as text, or None."""
    for th in soup.select("table.infobox th"):
        if LABEL_RE.search(th.get_text(" ")):
            td = th.find_next_sibling("td")
            text = " ".join(td.get_text(" ").split()) if td else ""
            return re.sub(r"\s*\[\s*\w+\s*\]", "", text) or None  # footnote marks
    return None


def _clean(text):
    text = re.sub(r"\[\s*(?:\d+|[a-z]|citation needed)\s*\]", "", text)  # footnote marks
    return " ".join(text.split())


def page_sentences(soup):
    """[(sentence, section)] for the article's paragraphs; section is None in the lead."""
    root = soup.select_one(".mw-parser-output") or soup
    out, section = [], None
    for el in root.find_all(["p", "div", "h2", "h3"], recursive=False):
        classes = el.get("class") or []
        if el.name in ("h2", "h3") or "mw-heading" in classes:
            section = _clean(el.get_text(" ")).replace(" [ edit ]", "").replace("[edit]", "").strip()
            continue
        if el.name == "p":
            out += [(s, section) for s in split_sentences(_clean(el.get_text(" ")))]
    return out


def _first_names(name, full):
    """The voting table's first word and the full name's: "Derek" for ("Derek X.", "Derek Xiao")."""
    return {name.split()[0], (full or name).split()[0]}


def names_in(text, people):
    """Houseguests named in text, in the order they appear.

    people is [(voting-table name, full name or None)]. A name matches as a whole
    word: the voting table's ("Derek X."), the full name, or the first name when
    no one else in the season shares it.
    """
    text = MENTION_RE.sub(" ", text)  # BB25 has a houseguest named America
    firsts = {}  # norm(first name) -> the houseguests it could be
    for name, full in people:
        for n in _first_names(name, full):
            firsts.setdefault(norm(n), set()).add(name)
    found = []
    for name, full in people:
        options = [name] + ([full] if full else [])
        options += [n for n in _first_names(name, full) if firsts[norm(n)] == {name}]
        hits = [m.start() for o in options for m in re.finditer(r"(?<!\w)" + re.escape(o.rstrip(".")) + r"(?!\w)", text)]
        if hits:
            found.append((min(hits), name))
    return [n for _, n in sorted(found)]


def match_player(text, people):
    """The voting-table name for the infobox's name ("Nicole Anthony" -> "Nicole A."), or None."""
    if not text:
        return None
    for name, full in people:
        if norm(text) in (norm(name), norm(full or "")):
            return name
    hits = names_in(text, people)
    return hits[0] if len(hits) == 1 else None


def afh(html, people, episodes=()):
    """America's Favorite HouseGuest for one season, or None if the page doesn't name one.

    people is [(voting-table name, full name or None)]; episodes are the season's
    episode records (see episodes.py). Returns {"winner", "winner_text", "others",
    "others_label", "prize", "notes": [{"text", "where"}]}. winner is the voting-table
    name (None if it can't be matched; winner_text is the infobox's own text).
    others are the other houseguests the page says placed, and others_label says how
    ("Top 3" or "Runner-up").
    """
    soup = BeautifulSoup(html, "lxml")
    text = infobox_winner(soup)
    if not text:
        return None
    winner = match_player(text, people)
    found = [(s, where or "Introduction") for s, where in page_sentences(soup)]
    for ep in episodes:
        for para in (ep.get("summary") or "").split("\n"):
            found += [(s, ep.get("title") or "Episode summary") for s in split_sentences(_clean(para))]
    notes, seen = [], set()
    for s, where in found:
        # Outside the introduction, only sentences that name someone: the Format
        # section describes the award in general.
        named = where == "Introduction" or names_in(s, people)
        if MENTION_RE.search(s) and not GENERIC_RE.search(s) and named and s not in seen:
            seen.add(s)
            notes.append({"text": s, "where": where})
    others, label = [], None
    for n in notes:
        s = n["text"]
        if TOP_RE.search(s):
            named = names_in(s, people)
            if winner in named and len(named) > 1:
                others, label = [x for x in named if x != winner], "Top 3"
                break
        m = RUNNER_UP_RE.search(s)
        if m and not others:
            named = [x for x in names_in(m.group(1), people) if x != winner]
            if len(named) == 1:
                others, label = named, "Runner-up"
    prizes = []
    for n in notes:
        # The first amount after the award is named: BB21's sentence gives the runner-up's first.
        at = MENTION_RE.search(n["text"]).start()
        prizes += [m.group(1) for m in PRIZE_RE.finditer(n["text"]) if m.end() > at]
    return {
        "winner": winner,
        "winner_text": text,
        "others": others,
        "others_label": label,
        "prize": prizes[0] if prizes else None,
        "notes": notes,
    }


def fandom_winner(players):
    """(voting-table name, prize) for the houseguest whose Big Brother Wiki page lists
    the award among this season's prizes ("$50,000 & 7-Day Cruise (Fan Favorite)"),
    else (None, None)."""
    for p in players:
        for line in (p.get("fandom") or {}).get("other_prizes") or []:
            if PRIZE_LINE_RE.search(line):
                prize = re.sub(r"\s*\([^)]*\)\s*$", "", line).strip()
                return p["name"], prize if MONEY_RE.search(prize) else None
    return None, None


def check(season, result, players, decided):
    """Merge the Big Brother Wiki's side into result in place; return report lines."""
    report = []
    wiki, prize = fandom_winner(players)
    if result is None:
        if decided:
            report.append(f"BB{season}: Wikipedia's infobox names no America's Favorite HouseGuest")
        return report
    if result["winner"] is None:
        report.append(f"BB{season}: America's Favorite HouseGuest {result['winner_text']!r} matches no houseguest")
    if wiki and result["winner"] and wiki != result["winner"]:
        report.append(f"BB{season}: America's Favorite HouseGuest: Wikipedia {result['winner']} / Fandom {wiki}")
    # The wiki's prize line is per houseguest, so it's the more reliable amount.
    result["prize"] = prize or result["prize"]
    return report

