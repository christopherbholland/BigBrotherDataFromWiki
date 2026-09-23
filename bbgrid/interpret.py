"""Step 3: turn a Grid into week records.

This module knows Big Brother and nothing about HTML: it only reads the Grid
produced by grid.py (cell text, name lists, and which positions share a
merged cell).
"""
import re

from .grid import Grid

# --- Row label mapping -------------------------------------------------------
# Matched against the normalized label (lowercase, single spaces, no
# footnote markers). Order matters only for readability; patterns don't overlap.
TOP_FIELDS = [
    ("hoh", re.compile(r"^head of household")),
    ("nominees_initial", re.compile(r"^nominations? \((initial|original|pre-veto)\)")),
    ("veto_winners", re.compile(r"^(power of )?veto winners?\b|^veto winner\(s\)|^(power of )?veto holder")),
    ("nominees_final", re.compile(r"^nominations? \((final|post-veto)\)")),
]
EVICTED_RE = re.compile(r"^evicted\b")
# Bottom-section rows that are page furniture, not week facts.
IGNORED_LABELS = re.compile(r"^(notes?|references?)$")
# A row in the vote section whose label looks like a summary row rather than a
# houseguest's name is treated as an extra, not a vote row.
SUMMARY_WORDS = re.compile(r"\b(winners?|nominations?|nominees?|veto|power|saved|evicted)\b")

WEEK_NUM_RE = re.compile(r"\bweek\s*(\d+)", re.I)
FINALE_RE = re.compile(r"\bfinale\b", re.I)
DAY_RE = re.compile(r"^day\s*(\d+)$", re.I)
EXIT_DAY_RE = re.compile(r"\(day\s*(\d+)\)", re.I)  # "Evicted (Day 73)", BB25's "Zombie (Day 51)"
NONE_RE = re.compile(r"^\(?(none|n/?a|—|–|-)\)?$", re.I)

VOTE_TALLY_RE = re.compile(r"(\d+)\s+of\s+(\d+)\s+votes?\s+to\s+evict", re.I)
SOLE_VOTE_RE = re.compile(r"^(.+?)['’]s\s+choice\s+to\s+evict", re.I)

NON_STANDARD = "Non-standard outcome: "

STATUS_RANK = {"ok": 0, "note": 1, "error": 2}


def normalize_label(text):
    text = re.sub(r"\[[^\]]*\]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def split_names(cell):
    """Names in a summary cell. Splits on line breaks (already done) and commas."""
    out = []
    for line in cell.names:
        for part in line.split(","):
            part = part.strip()
            if part and not NONE_RE.match(part):
                out.append(part)
    return out


def classify_rows(grid, label_cols):
    """Return a list of (kind, key, label, row) for body rows.

    key is the field name for "field" rows and the table label otherwise;
    label is always the row label as shown in the table.

    kind is one of: "field" (known summary field), "extra" (unknown summary
    row), "vote" (individual houseguest vote row), "evicted", "ignored".
    """
    labeled = []
    first_body_row = len(grid.header_rows)
    for i, row in enumerate(grid.body_rows):
        if row[label_cols[0]].row != first_body_row + i:
            # The label cell spans down from an earlier row (e.g. a two-row
            # "Evicted" whose second row only differs in a Finale column).
            labeled.append(("", "", row))
            continue
        seen, parts = set(), []
        for c in label_cols:
            cell = row[c]
            if id(cell) not in seen and cell.text:
                seen.add(id(cell))
                parts.append(cell.text.replace("\n", " "))
        display = re.sub(r"\[[^\]]*\]", "", " ".join(parts)).strip()
        labeled.append((normalize_label(display), display, row))

    def top_field(label):
        return next((f for f, pat in TOP_FIELDS if pat.search(label)), None)

    evicted_idx = next((i for i, (lab, _, _) in enumerate(labeled) if EVICTED_RE.search(lab)), len(labeled))
    top_end = max((i for i, (lab, _, _) in enumerate(labeled[:evicted_idx]) if top_field(lab)), default=-1)

    out, used_fields = [], set()
    for i, (label, display, row) in enumerate(labeled):
        if not label or IGNORED_LABELS.match(label):
            out.append(("ignored", display, display, row))
        elif i == evicted_idx:
            out.append(("evicted", display, display, row))
        elif i <= top_end or i > evicted_idx:
            field = top_field(label) if i <= top_end else None
            if field and field not in used_fields:
                used_fields.add(field)
                out.append(("field", field, display, row))
            else:
                out.append(("extra", display, display, row))
        elif SUMMARY_WORDS.search(label):
            out.append(("extra", display, display, row))
        else:
            out.append(("vote", display, display, row))
    return out


def label_columns(grid):
    """Leading columns covered by the corner cell of the first header row."""
    corner = grid.header_rows[0][0]
    return [c for c in range(grid.width) if grid.header_rows[0][c] is corner] or [0]


def week_columns(grid, label_cols):
    """Group data columns into weeks, and weeks into sub-columns.

    Returns [(week_label, [(sub_label, col), ...]), ...] left to right.
    """
    week_row = next(
        (row for row in grid.header_rows if any(WEEK_NUM_RE.search(c.text) for c in row)),
        grid.header_rows[0],
    )
    sub_row = grid.header_rows[-1]
    weeks = []
    for c in range(grid.width):
        if c in label_cols:
            continue
        week_cell, sub_cell = week_row[c], sub_row[c]
        if not week_cell.text:
            continue
        if not weeks or weeks[-1][0] is not week_cell:
            weeks.append((week_cell, []))
        subs = weeks[-1][1]
        if subs and subs[-1][0] is sub_cell:
            continue  # same sub-column spanning several grid columns
        subs.append((sub_cell, c))
    result = []
    for week_cell, subs in weeks:
        cols = []
        for sub_cell, c in subs:
            sub_label = sub_cell.text.replace("\n", " ") if sub_cell is not week_cell else None
            cols.append((sub_label, c))
        result.append((week_cell.text.replace("\n", " "), cols))
    return result


def parse_evicted(cell):
    """Return (evicted_name, tally) from an Evicted cell; tally None if unreadable."""
    if not cell.names:
        return None, None
    name = cell.names[0]
    rest = " ".join(cell.names[1:])
    m = VOTE_TALLY_RE.search(rest)
    if m:
        return name, {"type": "vote", "votes_to_evict": int(m.group(1)), "votes_cast": int(m.group(2))}
    m = SOLE_VOTE_RE.search(rest)
    if m:
        return name, {"type": "sole_vote", "by": m.group(1).strip()}
    return name, None


def raw_text(rows, cols, sub_labels):
    """The week's column text for note/error weeks (every row with content)."""
    out = {"columns": sub_labels, "rows": []}
    for kind, _, label, row in rows:
        cells = [row[c].text for c in cols]
        if any(cells) and kind != "ignored":
            out["rows"].append({"label": label, "cells": cells})
    return out


def build_round(rows, col, sub_label):
    rnd = {
        "sub_label": sub_label,
        "hoh": [],
        "nominees_initial": [],
        "veto_winners": [],
        "nominees_final": [],
        "evicted": None,
        "tally": None,
        "extras": {},
    }
    vote_cells, voters, evicted_cell = [], [], None
    for kind, key, label, row in rows:
        cell = row[col]
        if kind == "field":
            rnd[key] = split_names(cell)
        elif kind == "extra":
            names = split_names(cell)
            if names:
                rnd["extras"][key] = names
        elif kind == "evicted":
            evicted_cell = cell
            rnd["evicted"], rnd["tally"] = parse_evicted(cell)
        elif kind == "vote":
            vote_cells.append(cell.names)
            voters.append((label, cell.names))
    # Used by the validator and the details export; dropped from weeks.json.
    rnd["_vote_cells"] = vote_cells
    rnd["_voters"] = voters
    rnd["_col"] = col
    return rnd, round_problem(rnd, evicted_cell)


def round_problem(rnd, evicted_cell):
    """Return None, or (status, message, modeled) for a round that isn't a plain eviction.

    An empty Evicted cell (e.g. a week still airing) and an outcome that isn't
    a vote tally or a sole vote (competition eliminations, re-entries,
    cancelled evictions) are flagged and the round is left out. A plain
    eviction with no HOH is a structural error.
    """
    if rnd["evicted"] is None:
        return ("note", "No eviction", False)
    if rnd["tally"] is None:
        return ("note", NON_STANDARD + " ".join(evicted_cell.names), False)
    if not rnd["hoh"]:
        return ("error", "Missing HOH", True)
    return None


def eviction_day(rows, rnd):
    """The day the round's evictee left, from their vote row: the first
    "Evicted (Day N)"-style cell from the round's column on. None if not found."""
    name = normalize_label(rnd["evicted"] or "")
    for kind, _, label, row in rows:
        if kind == "vote" and normalize_label(label) == name:
            for cell in row[rnd["_col"]:]:
                m = EXIT_DAY_RE.search(cell.text)
                if m:
                    return int(m.group(1))
    return None


def mark_double_evictions(rows, rounds):
    """Flag each round that was a true double eviction.

    Wikipedia puts both of a week's evictions under one week when there are
    two, but only a fast-forward round is a double eviction: its HOH,
    nominations, veto and eviction all happen on the night of the previous
    eviction. Such a round's column is labeled with the day it was evicted on
    ("Day 73", with its evictee "Evicted (Day 73)"), where an ordinary round's
    label is its nomination day, days before the eviction. A round with no veto
    (a final HOH round) is never one. Sets rnd["double_eviction"].
    """
    for i, rnd in enumerate(rounds):
        m = DAY_RE.match(rnd["sub_label"] or "")
        rnd["double_eviction"] = bool(
            i > 0 and m and rnd["veto_winners"] and rnd["evicted"]
            and eviction_day(rows, rnd) == int(m.group(1)))


def two_round_note(round_cols, rounds, problem):
    """Note for a week with two rounds.

    "Double eviction" when a round was a true (same-night) double eviction;
    "Two evictions" when both sub-columns are "Day N" and both rounds are
    ordinary evictions a few days apart. Other two-column weeks (a split
    house's "Inside"/"Outside", a competition elimination beside an eviction,
    a round still to be played) get a neutral note naming the columns.
    """
    labels = [s or "" for s, _ in round_cols]
    if any(r.get("double_eviction") for r in rounds):
        return "Double eviction"
    if not problem and all(DAY_RE.match(label) for label in labels):
        return "Two evictions"
    return "Two rounds: " + " / ".join(labels)


def finale_cells(rows, col):
    """Each houseguest's Finale cell, for details.py's jury vote.

    Returns [(name, finale cell text, exit cell text or None)], in table order.
    The exit cell is the last "Evicted (Day N)"-style cell before the Finale
    column, which dates a juror's eviction.
    """
    out = []
    for kind, _, label, row in rows:
        if kind != "vote":
            continue
        exit_cell = next((row[c].text for c in reversed(range(col)) if EXIT_DAY_RE.search(row[c].text)), None)
        out.append((label, row[col].text, exit_cell))
    return out


def worst(a, b):
    return a if STATUS_RANK[a] >= STATUS_RANK[b] else b


def interpret(grid: Grid, season: int):
    if not grid.header_rows:
        raise ValueError("voting table has no header rows")
    label_cols = label_columns(grid)
    rows = classify_rows(grid, label_cols)
    records = []
    for week_label, subcols in week_columns(grid, label_cols):
        m = WEEK_NUM_RE.search(week_label)
        record = {
            "season": season,
            "week": int(m.group(1)) if m else None,
            "week_label": week_label,
            "status": "ok",
            "note": None,
            "rounds": [],
            "raw": None,
            "footnotes": [],
        }
        notes = []
        cols = [c for _, c in subcols]
        finale = [(s, c) for s, c in subcols if FINALE_RE.search(s or week_label)]
        round_cols = [(s, c) for s, c in subcols if (s, c) not in finale]

        if finale:
            record["status"] = "note"
            notes.append("Finale")
        if len(round_cols) >= 3:
            record["status"] = "note"
            notes.append(f"{len(round_cols)} sub-columns (not modeled)")
            round_cols = []
        problem_round = False
        for i, (sub_label, c) in enumerate(round_cols, 1):
            rnd, problem = build_round(rows, c, sub_label)
            if problem:
                status, msg, modeled = problem
                problem_round = True
                record["status"] = worst(record["status"], status)
                if len(round_cols) > 1:
                    msg = f"Round {i}" + (f" ({sub_label})" if sub_label else "") + f": {msg}"
                notes.append(msg)
                if not modeled:
                    continue
            record["rounds"].append(rnd)
        if len(round_cols) == 2:
            mark_double_evictions(rows, record["rounds"])
            notes.insert(1 if finale else 0, two_round_note(round_cols, record["rounds"], problem_round))
        for rnd in record["rounds"]:
            rnd.setdefault("double_eviction", False)

        for _, _, _, row in [(None, None, None, r) for r in grid.header_rows] + rows:
            for c in cols:
                for fn in row[c].footnotes:
                    if fn not in record["footnotes"]:
                        record["footnotes"].append(fn)
        record["note"] = "; ".join(notes) or None
        record["_raw"] = raw_text(rows, cols, [s or week_label for s, _ in subcols])
        if finale:
            record["_finale"] = finale_cells(rows, finale[-1][1])
        records.append(record)
    return records


# A houseguest's last cell in the vote rows says how their game ended.
RESULT_RE = re.compile(r"\b(winner|runner-up|place|evicted|eliminated|walked|expelled|ejected|removed|quit)\b", re.I)


def houseguests(grid: Grid):
    """The season's houseguests in table order, with how their game ended.

    Returns [{"name", "result"}]. "result" is the last cell of the
    houseguest's vote row that states an outcome ("Winner", "Evicted
    (Day 52)"), or None for someone still in the game while the season airs.
    """
    label_cols = label_columns(grid)
    out = []
    for kind, _, label, row in classify_rows(grid, label_cols):
        if kind != "vote":
            continue
        cells = [row[c].text.replace("\n", " ") for c in range(grid.width) if c not in label_cols]
        # Jurors' last cell is their Finale vote, so take the last stated outcome.
        result = next((t for t in reversed(cells) if RESULT_RE.search(t)), None)
        out.append({"name": label, "result": result})
    return out
