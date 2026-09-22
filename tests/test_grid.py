"""Grid builder unit tests on small synthetic tables."""
import pytest

from bbgrid.grid import TableNotFound, build_grid


def table(body, caption="Voting history"):
    return f'<table class="wikitable"><caption>{caption}</caption>{body}</table>'


def texts(rows):
    return [[c.text for c in row] for row in rows]


def test_colspan():
    g = build_grid(table("<tr><th></th><th colspan=2>Week 1</th></tr><tr><th>HOH</th><td>A</td><td>B</td></tr>"))
    assert texts(g.header_rows) == [["", "Week 1", "Week 1"]]
    assert g.header_rows[0][1] is g.header_rows[0][2]
    assert texts(g.body_rows) == [["HOH", "A", "B"]]


def test_rowspan():
    g = build_grid(table(
        "<tr><th>L</th><th>W1</th><th>W2</th></tr>"
        "<tr><th>a</th><td rowspan=2>X</td><td>1</td></tr>"
        "<tr><th>b</th><td>2</td></tr>"
    ))
    assert texts(g.body_rows) == [["a", "X", "1"], ["b", "X", "2"]]
    assert g.body_rows[0][1] is g.body_rows[1][1]


def test_rowspan_and_colspan_combined():
    g = build_grid(table(
        "<tr><th rowspan=2 colspan=2></th><th colspan=2>Week 1</th><th rowspan=2>Week 2</th></tr>"
        "<tr><th>Day 1</th><th>Day 2</th></tr>"
        "<tr><th colspan=2>HOH</th><td rowspan=2 colspan=2>Big</td><td>Z</td></tr>"
        "<tr><th colspan=2>Veto</th><td>Y</td></tr>"
    ))
    assert texts(g.header_rows) == [
        ["", "", "Week 1", "Week 1", "Week 2"],
        ["", "", "Day 1", "Day 2", "Week 2"],
    ]
    assert texts(g.body_rows) == [["HOH", "HOH", "Big", "Big", "Z"], ["Veto", "Veto", "Big", "Big", "Y"]]
    big = g.body_rows[0][2]
    assert all(g.body_rows[r][c] is big for r in (0, 1) for c in (2, 3))
    assert (big.rowspan, big.colspan) == (2, 2)


def test_names_split_on_br_not_spaces_and_footnotes_removed():
    g = build_grid(table(
        "<tr><th></th><th>W1</th></tr>"
        '<tr><th>Evicted</th><td style="background:#fcc">Mary Ann<sup class="reference"><a href="#cite_note-x">[x]</a></sup>'
        "<br/><small>8 of 11 votes<br>to evict</small></td></tr>"
    ))
    cell = g.body_rows[0][1]
    assert cell.names == ["Mary Ann", "8 of 11 votes", "to evict"]
    assert cell.footnotes == ["x"]
    assert cell.style == "background:#fcc"


def test_ragged_rows_are_padded():
    g = build_grid(table("<tr><th></th><th>W1</th><th>W2</th></tr><tr><th>a</th><td>1</td></tr>"))
    assert texts(g.body_rows) == [["a", "1", ""]]


def test_finds_table_by_section_heading_when_no_caption():
    html = (
        '<table class="wikitable"><tr><th>other</th></tr></table>'
        '<div class="mw-heading mw-heading2"><h2 id="Voting_history">Voting history</h2></div>'
        '<table class="wikitable"><tr><th></th><th>Week 1</th></tr><tr><th>HOH</th><td>A</td></tr></table>'
    )
    assert texts(build_grid(html).header_rows) == [["", "Week 1"]]


def test_missing_table_raises():
    with pytest.raises(TableNotFound):
        build_grid("<table><caption>Something else</caption></table>")
