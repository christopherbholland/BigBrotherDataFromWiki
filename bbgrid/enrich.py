"""Merge Big Brother Wiki (Fandom) data into the Wikipedia-based records.

Wikipedia stays the source of the grid: nothing here changes weeks.json's week
records. This adds to details.json:
  weeks[key]["fandom"]   competitions (all of them, with names, formats and the
                         episode-summary sentence describing them),
                         Have-Nots, and where the two wikis disagree
  players[i]["fandom"]   bio (full name, age, hometown, occupation, ...) and
                         Have-Not weeks
  seasons[season]        the season infobox (premiere, prize, host, ...)
and returns report lines for anything that didn't match up.

Names: the two wikis use different short names ("Michie" / "Jackson",
"Nicole A." / "Nicole A"). Each Wikipedia houseguest is matched to one Fandom
page, and every Fandom name is translated through that page.
"""
import re
import unicodedata

from .config import fandom_permalink, fandom_url
from .comps import describe, sentences
from .details import week_key

WIN_RE = re.compile(r"^(wins?|is saved|is upgraded|is awarded|is rewarded|returns?)\b", re.I)
COMPARED = [  # (Wikipedia round field, Fandom game-history field, label)
    ("hoh", "hoh", "HOH"),
    ("nominees_initial", "nominees_initial", "Initial nominations"),
    ("veto_winners", "veto_holders", "Veto winner"),
    ("nominees_final", "nominees_final", "Final nominations"),
]


def norm(name):
    """Compare names ignoring case, accents, dots, spaces, hyphens and apostrophes."""
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[\s.'’\-]+", "", text).casefold()


class Names:
    """Translate one season's Fandom names to Wikipedia's."""

    def __init__(self, roster, wiki_names):
        self.page = {}  # Wikipedia name -> Fandom page title
        self.alias = {}  # norm(Fandom short name or page title) -> Wikipedia name
        self.unmatched = []  # Wikipedia names with no Fandom page
        by_short = {}
        for title, short in roster:
            by_short.setdefault(norm(short), []).append(title)
        for w in wiki_names:
            key = norm(w)
            cands = by_short.get(key, [])
            if len(cands) != 1:
                # "Michie" -> "Jackson Michie": a whole word of the page title.
                cands = [t for t, _ in roster if key in [norm(p) for p in t.split()]]
            if len(cands) != 1:
                cands = [t for t, _ in roster if norm(t).startswith(key)]
            if len(cands) == 1:
                self.page[w] = cands[0]
            else:
                self.unmatched.append(w)
        taken = set(self.page.values())
        for w, title in self.page.items():
            self.alias[norm(title)] = w
            self.alias[norm(w)] = w
        for title, short in roster:
            if title in taken:
                self.alias.setdefault(norm(short), self.page_owner(title))
        self.unknown = set()  # Fandom names seen that match no one

    def page_owner(self, title):
        return next(w for w, t in self.page.items() if t == title)

    def __call__(self, name, record_unknown=True):
        """The Wikipedia name for a Fandom name or page title; the name itself if unknown."""
        w = self.alias.get(norm(name))
        if w is None and record_unknown:
            self.unknown.add(name)
        return w or name

    def known(self, name):
        return norm(name) in self.alias


def _round_for(record, kind, winners, taken=()):
    """1-based round whose HOH/veto winners include one of winners, or None.

    Rounds in taken ((kind, round) pairs already given a competition) are
    passed over while another round matches, so someone who won both of a
    double-eviction week's vetoes gets one competition per round.
    """
    field = "hoh" if kind == "hoh" else "veto_winners" if kind == "veto" else None
    if field is None:
        return None
    hits = [i for i, rnd in enumerate(record["rounds"], 1)
            if {norm(n) for n in rnd[field]} & {norm(n) for n in winners}]
    free = [i for i in hits if (kind, i) not in taken]
    return (free or hits or [None])[0]


def _pair_rows(record, rows):
    """[(round index, game-history row)] for one week, paired by who was evicted, then by order."""
    rounds = record["rounds"]
    if not rounds or not rows:
        return []
    pairs, used = [], set()
    for i, rnd in enumerate(rounds):
        hit = next((j for j, row in enumerate(rows) if j not in used and rnd["evicted"]
                    and norm(rnd["evicted"]) in {norm(n) for n in row["evicted"]}), None)
        if hit is not None:
            used.add(hit)
            pairs.append((i, rows[hit]))
    if not pairs and len(rows) == len(rounds):
        pairs = list(enumerate(rows))
    return pairs


def cross_check(record, week_details, rows):
    """Where Fandom's Game History disagrees with Wikipedia's round, field by field.

    Only fields both wikis fill in are compared, as sets of names; the veto's
    use is compared with what details.py worked out. Returns
    [{"round", "field", "wikipedia", "fandom"}].
    """
    out = []
    for i, row in _pair_rows(record, rows):
        rnd = record["rounds"][i]
        # Fandom's final nominations still list a nominee a twist saved (the AI Arena
        # or Block Buster winner); Wikipedia's are after the twist. Compare like with like.
        twist_saved = {norm(n) for names in rnd["extras"].values() for n in names}
        for wfield, ffield, label in COMPARED:
            a, b = rnd[wfield], row[ffield]
            if wfield == "nominees_final":
                b = [n for n in b if norm(n) not in twist_saved or norm(n) in {norm(x) for x in a}]
            if a and b and {norm(n) for n in a} != {norm(n) for n in b}:
                out.append({"round": i + 1, "field": label, "wikipedia": a, "fandom": b})
        derived = (week_details["rounds"][i].get("veto") or {}) if i < len(week_details["rounds"]) else {}
        if row["veto_used"] is not None and derived and derived["used"] != row["veto_used"]:
            out.append({"round": i + 1, "field": "Veto used",
                        "wikipedia": ["Yes" if derived["used"] else "No"],
                        "fandom": ["Yes" if row["veto_used"] else "No"]})
    return out


def enrich_season(season, fandom_data, meta, weeks, details, players):
    """Add Fandom data for one season in place; return (season_entry, report_lines)."""
    season_players = [p for p in players if p["season"] == season]
    names = Names(fandom_data["roster"], [p["name"] for p in season_players])
    report = [f"BB{season}: Fandom has no page for houseguest {w!r}" for w in names.unmatched]

    def translate(values):
        return [names(v) for v in values]

    game = fandom_data["game"]
    comps_by_week, game_by_week = {}, {}
    for c in fandom_data["competitions"]:
        comps_by_week.setdefault(c["week"], []).append(c)
    for row in game:
        row = {**row, **{k: translate(row[k]) for k in
                         ("hoh", "nominees_initial", "veto_holders", "nominees_final", "evicted")}}
        game_by_week.setdefault(row["week"], []).append(row)
    have_nots = fandom_data["have_nots"]["weeks"]
    player_have_not = {}  # Wikipedia name -> [week labels]
    player_wins = {}  # Wikipedia name -> [{"week", "type", "name"}]

    for record in (w for w in weeks if w["season"] == season):
        d = details.get(week_key(season, record["week_label"]))
        if d is None:
            continue
        num = record["week"]
        comps, taken = [], set()
        sents = sentences(d["episodes"])
        for c in comps_by_week.get(num, []):
            winners = translate(c["winners"])
            rnd = _round_for(record, c["kind"], winners, taken)
            if rnd:
                taken.add((c["kind"], rnd))
            comps.append({
                "kind": c["kind"], "type": c["type"], "name": c["name"], "format": c["format"],
                "day": c["day"], "winners": winners, "outcome": c["outcome"],
                "won": bool(WIN_RE.match(c["outcome"] or "")),
                "round": rnd, "extra": c["extra"],
                "about": describe(c["name"], sents) if c["kind"] != "twist" and c["name"] else None,
            })
            if c["kind"] == "twist" and comps[-1]["won"]:
                for w in winners:
                    player_wins.setdefault(w, []).append(
                        {"week": record["week_label"], "type": c["type"], "name": c["name"],
                         "outcome": c["outcome"]})
        hn = []
        for entry in have_nots.get(num, []):
            who = names(entry["guest"])
            by = entry["chosen_by"]
            if by:
                parts = [n.strip() for n in re.split(r"&|,", by) if n.strip()]
                # Initials such as "A&I" can't be resolved; keep the wiki's text as is.
                by = " & ".join(names(n) for n in parts) if all(names.known(n) for n in parts) else by
            hn.append({"name": who, "chosen_by": by})
            player_have_not.setdefault(who, []).append(record["week_label"])
        d["fandom"] = {
            "comps": comps,
            "have_nots": hn,
            "checks": cross_check(record, d, game_by_week.get(num, [])),
        }
        for chk in d["fandom"]["checks"]:
            rnd = f" round {chk['round']}" if len(record["rounds"]) > 1 else ""
            report.append(f"BB{season} {record['week_label']}{rnd}: {chk['field']}: Wikipedia "
                          f"{', '.join(chk['wikipedia'])} / Fandom {', '.join(chk['fandom'])}")

    bios = fandom_data["bios"]
    for p in season_players:
        title = names.page.get(p["name"])
        bio = bios.get(title) if title else None
        p["fandom"] = {
            **({k: v for k, v in bio.items() if k != "revid"} if bio else {"page": title}),
            "url": fandom_url(title) if title else None,
            "have_not": player_have_not.get(p["name"], []),
            "twist_wins": player_wins.get(p["name"], []),
        } if title else None
        if title and not bio:
            report.append(f"BB{season}: Fandom page {title!r} has no houseguest infobox")

    for name in sorted(names.unknown):
        if not re.search(r"\b(void|none|no one|n/a)\b", name, re.I):
            report.append(f"BB{season}: name on Fandom matches no houseguest: {name!r}")

    entry = {
        **(fandom_data["info"] or {}),
        "title": meta.get("title"),
        "url": fandom_url(meta["title"]) if meta.get("title") else None,
        "revid": meta.get("revid"),
        "permalink": fandom_permalink(meta["revid"]) if meta.get("revid") else None,
        "fetched_at": meta.get("fetched_at"),
        "competitions": len(fandom_data["competitions"]),
        "have_not_weeks": len(have_nots),
    }
    return entry, report
