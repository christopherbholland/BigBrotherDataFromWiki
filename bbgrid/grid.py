"""Step 2: locate the voting-history table and expand it into a rectangular grid.

This module knows about HTML and nothing about Big Brother. If Wikipedia
changes its markup, this is the only file that should need to change.

Output model:
  Grid.header_rows : list[list[Cell]]  leading rows made only of <th> cells
  Grid.body_rows   : list[list[Cell]]  every other row
Each row is a full-width list; a cell spanning several positions appears at
each of them as the *same* Cell object, so callers can tell a merged cell from
two cells with equal text (`a is b`).
"""
import copy
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, NavigableString, Tag

CAPTION_RE = re.compile(r"voting\s+history", re.I)
BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "tr", "table"}
MAX_SPAN = 200  # guard against malformed rowspan/colspan values


@dataclass(eq=False)
class Cell:
    text: str  # visible text, lines joined with "\n", footnote markers removed
    names: list  # text split on <br>/block boundaries (never on spaces)
    is_header: bool = False
    classes: list = field(default_factory=list)
    style: str = ""  # inline style, plus bgcolor attribute if present
    footnotes: list = field(default_factory=list)  # e.g. ["a", "12"]
    row: int = 0  # origin row/col in the expanded grid
    col: int = 0
    rowspan: int = 1
    colspan: int = 1


@dataclass
class Grid:
    header_rows: list
    body_rows: list
    width: int
    caption: str = ""


class TableNotFound(Exception):
    pass


def _span(tag, attr):
    raw = tag.get(attr, "1")
    m = re.match(r"\s*(\d+)", str(raw))
    n = int(m.group(1)) if m else 1
    return max(1, min(n, MAX_SPAN))


def _is_footnote(tag):
    if tag.name != "sup":
        return False
    classes = tag.get("class") or []
    return "reference" in classes or "noprint" in classes or tag.find("a", href=re.compile(r"^#cite_note")) is not None


def cell_from_tag(tag):
    """Build a Cell from a <td>/<th> tag (spans and position are set by the caller)."""
    tag = copy.copy(tag)
    footnotes = []
    for sup in tag.find_all("sup"):
        if _is_footnote(sup):
            label = sup.get_text("", strip=True).strip("[]")
            if label:
                footnotes.append(label)
            sup.decompose()
    for hidden in tag.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        hidden.decompose()
    for br in tag.find_all("br"):
        br.replace_with(NavigableString("\n"))
    for block in tag.find_all(BLOCK_TAGS):
        block.insert_before(NavigableString("\n"))
        block.insert_after(NavigableString("\n"))
    raw = tag.get_text("")
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw.split("\n")]
    names = [line for line in lines if line]
    style = tag.get("style", "") or ""
    if tag.get("bgcolor"):
        style = (style + f";background:{tag['bgcolor']}").lstrip(";")
    return Cell(
        text="\n".join(names),
        names=names,
        is_header=tag.name == "th",
        classes=list(tag.get("class") or []),
        style=style,
        footnotes=footnotes,
    )


def expand_table(table):
    """Expand rowspan/colspan into a rectangular list of rows of Cells."""
    rows = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]
    grid = []  # list[dict[col -> Cell]]
    for r, tr in enumerate(rows):
        while len(grid) <= r:
            grid.append({})
        c = 0
        for td in tr.find_all(["td", "th"], recursive=False):
            while c in grid[r]:
                c += 1
            cell = cell_from_tag(td)
            cell.row, cell.col = r, c
            cell.rowspan, cell.colspan = _span(td, "rowspan"), _span(td, "colspan")
            # rowspan may not extend past the table
            cell.rowspan = min(cell.rowspan, len(rows) - r)
            for dr in range(cell.rowspan):
                while len(grid) <= r + dr:
                    grid.append({})
                for dc in range(cell.colspan):
                    grid[r + dr].setdefault(c + dc, cell)
            c += cell.colspan
    width = max((max(row) + 1 for row in grid if row), default=0)
    empty = Cell(text="", names=[])
    return [[row.get(c, empty) for c in range(width)] for row in grid], width


def split_header(expanded):
    """Header rows are the leading rows whose own (originating) cells are all <th>."""
    n = 0
    for r, row in enumerate(expanded):
        own = [cell for cell in row if cell.row == r and (cell.text or cell.names or cell.is_header)]
        if own and all(cell.is_header for cell in own):
            n += 1
        else:
            break
    return expanded[:n], expanded[n:]


def find_voting_table(soup):
    for table in soup.find_all("table"):
        cap = table.find("caption")
        if cap and CAPTION_RE.search(cap.get_text(" ")):
            return table
    # Fallback: the first wikitable after a heading that says "Voting history".
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if CAPTION_RE.search(heading.get_text(" ")):
            anchor = heading.parent if "mw-heading" in (heading.parent.get("class") or []) else heading
            for sib in anchor.find_all_next():
                if isinstance(sib, Tag) and sib.name in ("h2", "h3") and sib is not heading:
                    break
                if isinstance(sib, Tag) and sib.name == "table" and "wikitable" in (sib.get("class") or []):
                    return sib
    raise TableNotFound("no table captioned or headed 'voting history'")


def build_grid(html):
    soup = BeautifulSoup(html, "lxml")
    table = find_voting_table(soup)
    cap = table.find("caption")
    expanded, width = expand_table(table)
    header, body = split_header(expanded)
    return Grid(
        header_rows=header,
        body_rows=body,
        width=width,
        caption=cap.get_text(" ", strip=True) if cap else "",
    )
