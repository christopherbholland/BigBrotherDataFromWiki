"""The season's cast table ("Name, Age, Occupation, Residence") from Wikipedia.

Reads the Grid from grid.build_table_with_columns; no HTML here. Names in the
cast table are full names ("Jackson Michie"); the voting table uses short ones
("Michie"), so each vote-row name is matched to one cast row.
"""
import re

from .enrich import Names
from .grid import build_table_with_columns

COLUMNS = ("Name", "Age", "Occupation", "Residence")


def cast_table(html):
    """[{"full_name", "age", "occupation", "hometown"}] in table order."""
    grid = build_table_with_columns(html, COLUMNS)
    if grid is None or not grid.header_rows:
        return []
    header = [c.text.replace("\n", " ").strip().casefold() for c in grid.header_rows[0]]
    col = {k: header.index(k.casefold()) for k in COLUMNS}
    out, seen = [], set()
    for row in grid.body_rows:
        # A returning player's cell adds their earlier seasons on later lines.
        name = (row[col["Name"]].names or [""])[0]
        if not name or name in seen:
            continue
        seen.add(name)
        age = re.match(r"\s*(\d+)", row[col["Age"]].text)
        out.append({
            "full_name": name,
            "age": int(age.group(1)) if age else None,
            "occupation": " ".join(row[col["Occupation"]].names) or None,
            "hometown": " ".join(row[col["Residence"]].names) or None,
        })
    return out


def bios(html, names):
    """{vote-row name: cast row} for each houseguest matched to one cast row."""
    rows = cast_table(html)
    # A nickname in quotes is the name the voting table uses: Olukemi "Kemi" Fakunle.
    roster = [(r["full_name"], (re.findall(r'["“]([^"”]+)["”]', r["full_name"]) or [r["full_name"]])[0])
              for r in rows]
    match = Names(roster, names)
    by_name = {r["full_name"]: r for r in rows}
    return {n: by_name[title] for n, title in match.page.items()}
