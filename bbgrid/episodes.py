"""Episodes per week, from the season page's episode table.

Reads the Grid from grid.build_episode_grid (no HTML here). The table is
already grouped by week: a full-width "Week N" row, then each episode's row
followed by a full-width summary row.
"""
import re
from datetime import datetime

from .grid import Grid

WEEK_HEADING_RE = re.compile(r"^(week\s*\d+|finale\b.*)$", re.I)
COLUMNS = {
    "number_overall": re.compile(r"overall", re.I),
    "number": re.compile(r"in\s*season", re.I),
    "title": re.compile(r"^title", re.I),
    "days": re.compile(r"^day", re.I),
    "air_date": re.compile(r"release|air\s*date", re.I),
    "viewers": re.compile(r"viewers", re.I),
}


def _column_map(grid):
    header = grid.header_rows[-1] if grid.header_rows else []
    cols = {}
    for c, cell in enumerate(header):
        text = cell.text.replace("\n", " ")
        for key, pat in COLUMNS.items():
            if key not in cols and pat.search(text):
                cols[key] = c
    return cols


def _full_width(row):
    """A row made of one cell spanning (nearly) the whole table: a heading or a summary."""
    return row[0].colspan > 1 and row[0] is row[1]


def _iso_date(text):
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _number(text):
    m = re.match(r"\s*([\d.]+)", text)
    return float(m.group(1)) if m and m.group(1).replace(".", "", 1).isdigit() else None


def episodes_by_week(grid: Grid):
    """Return {week_label: [episode, ...]} in table order.

    Each episode is {number_overall, number, title, days, air_date,
    air_date_text, viewers_millions, summary}. Episodes before the first
    week heading are keyed under "".
    """
    if grid is None:
        return {}
    cols = _column_map(grid)
    by_week, week, last = {}, "", None
    for row in grid.body_rows:
        if _full_width(row):
            text = row[0].text.replace("\n", " ").strip()
            if WEEK_HEADING_RE.match(text):
                week = text
            elif last is not None:
                last["summary"] = row[0].text
            continue

        def cell(key):
            return row[cols[key]].text.replace("\n", " ").strip() if key in cols else ""

        title = cell("title").strip('"“”')
        if not title and not cell("number_overall"):
            continue
        date_text = cell("air_date")
        last = {
            "number_overall": cell("number_overall") or None,
            "number": cell("number") or None,
            "title": title,
            "days": cell("days") or None,
            "air_date": _iso_date(date_text),
            "air_date_text": date_text or None,
            "viewers_millions": _number(cell("viewers")),
            "summary": None,
        }
        by_week.setdefault(week, []).append(last)
    return by_week
