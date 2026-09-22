"""Detail data for the page's click-through views, written to details.json.

Works on the interpreter's week records (before export drops their internal
keys), the voting Grid's footnote text, the houseguest list and the episode
table. Nothing here is shown on the main cards.
"""
import re

OUT_OF_GAME_RE = re.compile(r"^(evicted|eliminated|walked|expelled|ejected|removed|quit)\b", re.I)
# Parts of a week's note that don't describe anything unusual about the game.
ROUTINE_NOTES = re.compile(r"^(finale|no eviction)$|: no eviction$", re.I)


def _key(name):
    return " ".join(name.split()).casefold()


def week_key(season, week_label):
    return f"{season}|{week_label}"


def round_votes(rnd):
    """Split a round's vote-row cells into votes and reasons for not voting.

    Returns {"votes": [{"voter", "vote"}], "not_voting": [{"voter", "reason"}],
    "by_nominee": [{"nominee", "voters": [...]}]} with by_nominee in the order
    of nominees_final.
    """
    finals = {_key(n): n for n in rnd["nominees_final"]}
    votes, not_voting = [], []
    for voter, names in rnd.get("_voters", []):
        text = " ".join(names)
        if len(names) == 1 and _key(names[0]) in finals:
            votes.append({"voter": voter, "vote": finals[_key(names[0])]})
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
            items.append(f"{prefix}{label}: {', '.join(names)}")
    texts = [{"label": fn, "text": notes[fn]} for fn in record["footnotes"] if fn in notes]
    return {"items": items, "notes": texts}


def week_details(records, notes, episodes):
    """{week_key: {"rounds": [votes...], "special": {...}, "episodes": [...]}}."""
    out = {}
    for record in records:
        out[week_key(record["season"], record["week_label"])] = {
            "rounds": [{"sub_label": r["sub_label"], **round_votes(r)} for r in record["rounds"]],
            "special": special(record, notes),
            "episodes": episodes.get(record["week_label"], []),
        }
    return out


def players(season, records, guests):
    """Per-houseguest stats for one season, from the modeled rounds.

    Returns (players, unmatched): players in table order (winner first), and
    names seen in summary cells that match no houseguest row.
    """
    table = {}
    for g in guests:
        table[_key(g["name"])] = {
            "season": season, "name": g["name"], "result": g["result"],
            "hoh": [], "veto": [], "nominated": [], "on_block": [], "evicted": None,
            "votes_against": [], "votes_cast": [], "twist": [],
        }
    unmatched = set()

    def add(name, field, value):
        p = table.get(_key(name))
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
