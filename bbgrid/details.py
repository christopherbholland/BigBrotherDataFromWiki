"""Detail data for the page's click-through views, written to details.json.

Works on the interpreter's week records (before export drops their internal
keys), the voting Grid's footnote text, the houseguest list and the episode
table. Nothing here is shown on the main cards.
"""
import re

from .util import mentions, name_key, split_sentences

OUT_OF_GAME_RE = re.compile(r"^(evicted|eliminated|walked|expelled|ejected|removed|quit)\b", re.I)
# Parts of a week's note that don't describe anything unusual about the game.
WINNER_SUFFIX = re.compile(r"\s+winners?$", re.I)
ROUTINE_NOTES = re.compile(r"^(finale|eviction to come)$|: eviction to come$", re.I)


def week_key(season, week_label):
    return f"{season}|{week_label}"


def round_votes(rnd):
    """Split a round's vote-row cells into votes and reasons for not voting.

    Returns {"votes": [{"voter", "vote"}], "not_voting": [{"voter", "reason"}],
    "by_nominee": [{"nominee", "voters": [...]}]} with by_nominee in the order
    of nominees_final.
    """
    finals = {name_key(n): n for n in rnd["nominees_final"]}
    votes, not_voting = [], []
    for voter, names in rnd.get("_voters", []):
        text = " ".join(names)
        if len(names) == 1 and name_key(names[0]) in finals:
            votes.append({"voter": voter, "vote": finals[name_key(names[0])]})
        elif text and not OUT_OF_GAME_RE.match(text):
            not_voting.append({"voter": voter, "reason": text})
    by_nominee = [
        {"nominee": n, "voters": [v["voter"] for v in votes if v["vote"] == n]}
        for n in rnd["nominees_final"]
    ]
    return {"votes": votes, "not_voting": not_voting, "by_nominee": by_nominee}


def special(record, notes):
    """What was different about the week, from the table only.

    items: twist rows (e.g. "AI Arena winner: Kimo") and the unusual parts of
    the week's note (double eviction, non-standard outcomes).
    notes: Wikipedia's footnote text for the week, verbatim.
    """
    multi = len(record["rounds"]) > 1
    items = []
    for part in (record["note"] or "").split("; "):
        if part and not ROUTINE_NOTES.search(part) and not part.startswith("Validation failed"):
            items.append(part)
    for i, rnd in enumerate(record["rounds"], 1):
        for label, names in rnd["extras"].items():
            prefix = f"Round {i}: " if multi else ""
            # "Block Buster: Melody", not Wikipedia's "Block Buster winner".
            short = WINNER_SUFFIX.sub("", label)
            items.append(f"{prefix}{short}: {', '.join(names)}")
    texts = [{"label": fn, "text": notes[fn]} for fn in record["footnotes"] if fn in notes]
    return {"items": items, "notes": texts}


def veto_use(rnd):
    """What the veto did, from the nominations before and after it.

    The table doesn't say who the veto was used on, but it does show who came
    off the block and who replaced them. A nominee who left the block and is
    named in a twist row (e.g. the AI Arena winner) was saved by the twist, not
    the veto. Returns None when there was no veto or nothing to compare.
    """
    if not rnd["veto_winners"] or not rnd["nominees_initial"] or not rnd["nominees_final"]:
        return None
    initial, final = rnd["nominees_initial"], rnd["nominees_final"]
    finals = {name_key(n) for n in final}
    removed = [n for n in initial if name_key(n) not in finals]
    added = [n for n in final if name_key(n) not in {name_key(i) for i in initial}]
    twist_names = {name_key(n) for names in rnd["extras"].values() for n in names}
    twist_saved = [n for n in removed if name_key(n) in twist_names]
    saved = [n for n in removed if name_key(n) not in twist_names]
    return {
        "used": bool(saved),
        "on": saved,
        "replacements": added,
        "twist_saved": twist_saved,
    }


# --- Competition names and veto decisions from the episode summaries --------
_QUOTED = r'["“]([^"”]{2,40}?)[,.!?]?["”]'
_KIND = r"((?i:head[ -]of[ -]household|hoh|power[ -]of[ -]veto|pov|veto))"
_COMP = r"[Cc]omp(?:etition)?"
COMP_PATTERNS = [
    # (regex, index of the kind group, index of the name group)
    (re.compile(_QUOTED + r"\s+" + _KIND + r"\s+" + _COMP), 2, 1),              # the "X" HOH competition
    (re.compile(_KIND + r"\s+" + _COMP + r"[,:]?\s*\(?\s*(?:called\s+|titled\s+|named\s+)?" + _QUOTED), 1, 2),
    (re.compile(_KIND + r"(?:\s+" + _COMP + r")?\s*\(\s*" + _QUOTED + r"\s*\)"), 1, 2),  # Power of Veto ("X")
    (re.compile(_KIND + r"\s+" + _COMP + r":\s*([A-Z][^.:;\"“]{2,40}?)\."), 1, 2),     # Veto competition: X.
]
VETO_DECISION_RE = re.compile(
    r"\bveto (meeting|ceremony)\b|\b(used|use|using) the (power of )?veto\b|\bnot to use\b|\bdecided not\b", re.I)


def episode_insights(record, episodes):
    """Competition names and veto-meeting sentences found in the week's episode summaries.

    comps: [{"kind": "hoh"|"veto", "name", "winner", "round", "source"}]. A
    competition is tied to a round only when that round's HOH or veto winner
    is named in the same or the next sentence; live shows often start the
    next week's HOH, so unmatched names are kept with winner=None.
    veto_notes: sentences about the veto meeting, verbatim.
    """
    sentences = []
    for ep in episodes:
        sentences += split_sentences(ep.get("summary") or "")
    comps, seen, taken = [], {}, set()  # taken: (round, kind) already given a competition
    for i, sent in enumerate(sentences):
        context = sent + " " + (sentences[i + 1] if i + 1 < len(sentences) else "")
        for pattern, kind_group, name_group in COMP_PATTERNS:
            for m in pattern.finditer(sent):
                kind = "veto" if re.search(r"veto|pov", m.group(kind_group), re.I) else "hoh"
                name = m.group(name_group).strip()
                winner, round_no = None, None
                for n, rnd in enumerate(record["rounds"], 1):
                    field = "veto_winners" if kind == "veto" else "hoh"
                    hit = next((w for w in rnd[field] if mentions(context, w)), None)
                    if hit and (n, kind) not in taken:
                        winner, round_no = hit, n
                        break
                key = (kind, name.casefold())
                if key in seen:
                    if winner and not seen[key]["winner"]:
                        seen[key].update(winner=winner, round=round_no, source=sent)
                        taken.add((round_no, kind))
                    continue
                if winner:
                    taken.add((round_no, kind))
                seen[key] = {"kind": kind, "name": name, "winner": winner, "round": round_no, "source": sent}
                comps.append(seen[key])
    veto_notes = []
    for sent in sentences:
        if VETO_DECISION_RE.search(sent) and sent not in veto_notes:
            veto_notes.append(sent)
    return {"comps": comps, "veto_notes": veto_notes}


# --- Who played in the veto ---------------------------------------------------
# The HOH and the nominees always play; the rest are drawn (or picked by
# "houseguest's choice"), six players in all. Neither wiki's tables list them,
# so they come from the episode summaries ("Angela and Barrett are selected to
# compete alongside the nominees"), or from the house being small enough that
# everyone plays.
VETO_PLAYERS = 6
_VETO_WORD = re.compile(r"\b(?:veto|pov)\b", re.I)
_DRAWN = re.compile(
    r"\b(?:(?:was|were|is|are|get|gets|got|been|being)\s+(?:randomly\s+)?(?:selected|chosen|picked|drawn)"
    r"|(?:competes?|competing|plays?|playing)\s+(?:for|in)\s+the\s+(?:power\s+of\s+)?(?:veto|pov)"
    r"|selects?\s+the\s+(?:third|last|other))\b", re.I)
# Out of the house that week: already evicted, or waiting in a comeback twist.
_NOT_IN_HOUSE = re.compile(r"evicted|comeback|zombie", re.I)


def _named(text, name):
    """True if text names this houseguest as a person (not "Rome's backdoor plan")."""
    return re.search(r"(?<!\w)" + re.escape(name) + r"(?![\w’'])", text, re.I) is not None


def veto_players(rnd, votes, sentences):
    """Who played in the round's veto competition, as far as the sources say.

    Returns {"players": [...], "complete": bool}: complete is True when every
    player is known (the whole house played, or the summaries name everyone
    drawn), so someone missing from the list didn't play. None without a veto.
    """
    if not rnd["veto_winners"]:
        return None
    in_house = [v["voter"] for v in votes["votes"]] + [
        v["voter"] for v in votes["not_voting"] if not _NOT_IN_HOUSE.search(v["reason"])]
    in_house += [n for n in rnd["hoh"] + rnd["nominees_initial"] if n not in in_house]
    if len(in_house) <= VETO_PLAYERS:
        return {"players": in_house, "complete": True}
    cast = [n for n, _ in rnd.get("_voters", [])]
    sure = list(dict.fromkeys(rnd["hoh"] + rnd["nominees_initial"] + rnd["veto_winners"]))
    drawn = []
    for i, sent in enumerate(sentences):
        # A split after an initial ("Derek X.") leaves "were chosen …" on its own.
        if i and sent[:1].islower():
            sent = sentences[i - 1] + " " + sent
        if not (_VETO_WORD.search(sent) and _DRAWN.search(sent)):
            continue
        drawn += [n for n in cast if _named(sent, n) and n not in sure and n not in drawn]
        if len(sure) + len(drawn) >= VETO_PLAYERS:
            break
    return {"players": sure + drawn, "complete": len(sure) + len(drawn) >= VETO_PLAYERS}


def week_details(records, notes, episodes):
    """{week_key: {"rounds": [...], "special", "episodes", "comps", "veto_notes"}}."""
    out = {}
    for record in records:
        eps = episodes.get(record["week_label"], [])
        sentences = [s for ep in eps for s in split_sentences(ep.get("summary") or "")]
        rounds = []
        for r in record["rounds"]:
            votes = round_votes(r)
            veto = veto_use(r)
            if veto is not None:
                veto["players"] = veto_players(r, votes, sentences)
            rounds.append({"sub_label": r["sub_label"], **votes, "veto": veto})
        out[week_key(record["season"], record["week_label"])] = {
            "rounds": rounds,
            "special": special(record, notes),
            "episodes": eps,
            **episode_insights(record, eps),
        }
    return out


def players(season, records, guests):
    """Per-houseguest stats for one season, from the modeled rounds.

    Returns (players, unmatched): players in table order (winner first), and
    names seen in summary cells that match no houseguest row.
    """
    table = {}
    for g in guests:
        table[name_key(g["name"])] = {
            "season": season, "name": g["name"], "result": g["result"],
            "hoh": [], "veto": [], "nominated": [], "on_block": [], "evicted": None,
            "votes_against": [], "votes_cast": [], "twist": [],
        }
    unmatched = set()

    def add(name, field, value):
        p = table.get(name_key(name))
        if p is None:
            unmatched.add(name)
        elif field == "evicted":
            p["evicted"] = value
        else:
            p[field].append(value)

    for record in records:
        multi = len(record["rounds"]) > 1
        for rnd in record["rounds"]:
            week = record["week_label"] + (f" ({rnd['sub_label']})" if multi and rnd["sub_label"] else "")
            for n in rnd["hoh"]:
                add(n, "hoh", week)
            for n in rnd["veto_winners"]:
                add(n, "veto", week)
            for n in rnd["nominees_initial"]:
                add(n, "nominated", week)
            for n in rnd["nominees_final"]:
                add(n, "on_block", week)
            for label, names in rnd["extras"].items():
                for n in names:
                    # "(Janelle)" beside a winner names someone else involved, not a winner.
                    if not (n.startswith("(") and n.endswith(")")):
                        add(n, "twist", {"week": week, "label": label})
            if rnd["evicted"]:
                add(rnd["evicted"], "evicted", week)
            v = round_votes(rnd)
            for vote in v["votes"]:
                add(vote["voter"], "votes_cast", {"week": week, "vote": vote["vote"],
                                                  "with_house": vote["vote"] == rnd["evicted"]})
            for row in v["by_nominee"]:
                if row["voters"]:
                    add(row["nominee"], "votes_against", {"week": week, "voters": row["voters"]})
    return list(table.values()), sorted(unmatched)


# --- The finale: every juror's vote, from the Finale column ------------------
FINALIST_RE = re.compile(r"^(winner|runner-up)\b", re.I)
JUROR_PENDING_RE = re.compile(r"^jury member\b", re.I)  # a juror while the season is still airing
EXIT_RE = re.compile(r"^(.*?)\s*\(day\s*(\d+)\)", re.I | re.S)


def finale(record):
    """The jury vote for a week with a Finale column, else None.

    The votes are counted from the jurors' own cells rather than read from the
    Evicted row, which can be wrong (BB22's says "Enzo 0 votes to win"). While
    a season is airing the finalists aren't known and jurors have no vote yet:
    "decided" is False and each juror's "vote" is None.

    Returns {"season", "week", "decided", "winner", "runner_up",
    "finalists": [{"name", "votes", "jurors": [...]}], "jury": [{"name",
    "vote", "left", "day"}]}, jurors in the order they left the game.
    """
    cells = record.get("_finale")
    if not cells:
        return None
    result = {name: text.split("\n")[0].strip().lower() for name, text, _ in cells if FINALIST_RE.match(text)}
    finalists = {name_key(n): n for n in result}
    jury = []
    for name, text, exit_cell in cells:
        vote = finalists.get(name_key(text.replace("\n", " ")))
        if vote is None and not JUROR_PENDING_RE.match(text):
            continue
        m = EXIT_RE.match(exit_cell or "")
        left = " ".join(m.group(1).split()) if m else None
        jury.append({"name": name, "vote": vote, "left": left, "day": int(m.group(2)) if m else None})
    # The table lists the latest to leave first; a juror with no exit day goes last.
    jury.sort(key=lambda j: j["day"] if j["day"] is not None else 10**6)
    winner = next((n for n, r in result.items() if r == "winner"), None)
    return {
        "season": record["season"],
        "week": record["week_label"],
        "decided": winner is not None,
        "winner": winner,
        "runner_up": next((n for n, r in result.items() if r == "runner-up"), None),
        "finalists": [{"name": n, "votes": sum(j["vote"] == n for j in jury),
                       "jurors": [j["name"] for j in jury if j["vote"] == n]} for n in result],
        "jury": jury,
    }
