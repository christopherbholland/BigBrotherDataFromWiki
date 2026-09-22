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
NONE_RE = re.compile(r"^\(?(none|n/?a|—|–|-)\)?$", re.I)

VOTE_TALLY_RE = re.compile(r"(\d+)\s+of\s+(\d+)\s+votes?\s+to\s+evict", re.I)
SOLE_VOTE_RE = re.compile(r"^(.+?)['’]s\s+choice\s+to\s+evict", re.I)

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
    vote_cells, evicted_cell = [], None
    for kind, key, _, row in rows:
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
    rnd["_vote_cells"] = vote_cells  # used by the validator, dropped on export
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
        return ("note", "Non-standard outcome: " + " ".join(evicted_cell.names), False)
    if not rnd["hoh"]:
        return ("error", "Missing HOH", True)
    return None


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
        elif len(round_cols) == 2:
            notes.append("Double eviction")

        for i, (sub_label, c) in enumerate(round_cols, 1):
            rnd, problem = build_round(rows, c, sub_label)
            if problem:
                status, msg, modeled = problem
                record["status"] = worst(record["status"], status)
                if len(round_cols) > 1:
                    msg = f"Round {i}" + (f" ({sub_label})" if sub_label else "") + f": {msg}"
                notes.append(msg)
                if not modeled:
                    continue
            record["rounds"].append(rnd)

        for _, _, _, row in rows:
            for c in cols:
                for fn in row[c].footnotes:
                    if fn not in record["footnotes"]:
                        record["footnotes"].append(fn)
        record["note"] = "; ".join(notes) or None
        record["_raw"] = raw_text(rows, cols, [s or week_label for s, _ in subcols])
        records.append(record)
    return records
