"""Interpreter + validator tests on the synthetic fixture and small variants."""
from pathlib import Path

from bbgrid.export import process_season

FIXTURE = (Path(__file__).parent / "fixtures" / "synthetic_season.html").read_text()


def weeks():
    return {w["week"]: w for w in process_season(99, FIXTURE)}


def test_standard_week():
    w = weeks()[1]
    assert w["status"] == "ok" and w["note"] is None and w["raw"] is None
    (r,) = w["rounds"]
    assert r["hoh"] == ["Alex"]
    assert r["nominees_initial"] == ["Blair", "Casey", "Dana"]
    assert r["veto_winners"] == ["Casey"]
    assert r["nominees_final"] == ["Blair", "Dana"]
    assert r["evicted"] == "Blair"
    assert r["tally"] == {"type": "vote", "votes_to_evict": 4, "votes_cast": 5}
    assert r["extras"] == {"AI Arena winner": ["Dana"]}
    assert w["footnotes"] == ["b"]


def test_multiple_veto_winners_and_footnote():
    w = weeks()[2]
    assert w["status"] == "ok"
    assert w["rounds"][0]["veto_winners"] == ["Casey", "Eli"]
    assert w["rounds"][0]["extras"] == {}  # "(none)" is not a name
    assert w["footnotes"] == ["a"]


def test_double_eviction():
    w = weeks()[3]
    assert w["status"] == "ok" and w["note"] == "Double eviction"
    assert [r["sub_label"] for r in w["rounds"]] == ["Day 20", "Day 23"]
    assert [r["evicted"] for r in w["rounds"]] == ["Gus", "Dana"]
    assert w["rounds"][1]["hoh"] == ["Hana"]
    # Round 2 was played the night of round 1's eviction: Dana left on its column's day.
    assert [r["double_eviction"] for r in w["rounds"]] == [False, True]


def test_two_evictions_days_apart_are_not_a_double_eviction():
    # Round 2's label is its nomination day; its evictee left three days later.
    html = FIXTURE.replace("Evicted (Day 23)", "Evicted (Day 26)")
    w = {w["week"]: w for w in process_season(99, html)}[3]
    assert w["status"] == "ok" and w["note"] == "Two evictions"
    assert [r["double_eviction"] for r in w["rounds"]] == [False, False]


def test_finale_column_is_not_a_round():
    w = weeks()[4]
    assert w["status"] == "note" and w["note"] == "Finale"
    (r,) = w["rounds"]
    assert r["sub_label"] == "Day 30"
    assert r["tally"] == {"type": "sole_vote", "by": "Hana"}
    assert w["raw"]["columns"] == ["Day 30", "Finale"]


def test_vote_count_mismatch_is_an_error():
    html = FIXTURE.replace("4 of 5 votes", "5 of 5 votes")
    w = {w["week"]: w for w in process_season(99, html)}[1]
    assert w["status"] == "error"
    assert "vote rows show 4 votes to evict Blair, tally says 5" in w["note"]
    assert w["raw"] is not None


def test_evicted_not_a_final_nominee_is_an_error():
    html = FIXTURE.replace("<td>Blair<br />Dana</td>", "<td>Casey<br />Dana</td>")
    w = {w["week"]: w for w in process_season(99, html)}[1]
    assert w["status"] == "error"
    assert "not in final nominees" in w["note"]


def test_non_standard_outcome_is_a_note_and_not_modeled():
    # e.g. "Evicted by competition", "Won re-entry into game", "Eviction cancelled"
    html = FIXTURE.replace("3 of 4 votes<br />to evict", "Eliminated by competition")
    w = {w["week"]: w for w in process_season(99, html)}[2]
    assert w["status"] == "note"
    assert w["note"] == "Non-standard outcome: Fran Eliminated by competition"
    assert w["rounds"] == [] and w["raw"]["rows"]


def test_double_eviction_with_one_round_unfinished_keeps_both_rounds():
    # Like BB28 Week 11: the second round's HOH and noms are known, its eviction isn't yet.
    html = FIXTURE.replace("<td>Dana<br /><small>2 of 2 votes<br />to evict</small></td>", "<td></td>")
    w = {w["week"]: w for w in process_season(99, html)}[3]
    assert w["status"] == "note"
    assert w["note"] == "Two rounds: Day 20 / Day 23; Round 2 (Day 23): Eviction to come"
    assert [r["evicted"] for r in w["rounds"]] == ["Gus", None]
    assert w["rounds"][1]["hoh"] and w["rounds"][1]["tally"] is None


def test_label_spanning_two_rows_is_not_a_second_row():
    # Wikipedia's Evicted label spans two rows; the second row differs only in the Finale column.
    html = FIXTURE.replace('<th colspan="2">Evicted</th>', '<th colspan="2" rowspan="2">Evicted</th>').replace(
        '<tr>\n  <th colspan="2">Notes</th>',
        '<tr><td>Blair</td><td>Fran</td><td>Gus</td><td>Dana</td><td>Eli</td><td>Casey</td></tr>\n'
        '<tr>\n  <th colspan="2">Notes</th>',
    )
    assert html.count('rowspan="2">Evicted') == 1 and "<td>Casey</td></tr>" in html
    weeks = process_season(99, html)
    assert [w["status"] for w in weeks] == ["ok", "ok", "ok", "note"]
    assert all("Evicted" not in r["extras"] for w in weeks for r in w["rounds"])


def test_week_without_eviction_is_a_note():
    # Like an in-progress week: summary rows filled in, Evicted cell still empty.
    html = FIXTURE.replace("<td>Fran<br /><small>3 of 4 votes<br />to evict</small></td>", "<td></td>")
    w = {w["week"]: w for w in process_season(99, html)}[2]
    assert w["status"] == "note" and w["note"] == "Eviction to come"
    assert [r["hoh"] for r in w["rounds"]] == [["Casey"]] and w["rounds"][0]["evicted"] is None
    assert w["raw"]["rows"]


def test_week_without_eviction_or_hoh_is_not_modeled():
    html = FIXTURE.replace("<td>Fran<br /><small>3 of 4 votes<br />to evict</small></td>", "<td></td>")
    html = html.replace('<td>Casey<sup class="reference"><a href="#cite_note-a">[a]</a></sup></td>', "<td></td>")
    w = {w["week"]: w for w in process_season(99, html)}[2]
    assert w["status"] == "note" and w["note"] == "Eviction to come"
    assert w["rounds"] == [] and w["raw"]["rows"]


def test_three_sub_columns_are_not_modeled():
    html = """<table class="wikitable"><caption>Voting history</caption>
    <tr><th rowspan=2></th><th colspan=3>Week 1</th></tr>
    <tr><th>Day 1</th><th>Day 2</th><th>Day 3</th></tr>
    <tr><th>Head of Household</th><td>A</td><td>B</td><td>C</td></tr>
    <tr><th>Nominations (final)</th><td>X<br>Y</td><td>X<br>Z</td><td>Y<br>Z</td></tr>
    <tr><th>Evicted</th><td>X<br>1 of 1 votes to evict</td><td>Z<br>1 of 1 votes to evict</td><td>Y<br>1 of 1 votes to evict</td></tr>
    </table>"""
    (w,) = process_season(1, html)
    assert w["status"] == "note" and w["note"] == "3 sub-columns (not modeled)"
    assert w["rounds"] == []


def test_two_rounds_without_day_labels_is_not_called_a_double_eviction():
    # A split house: two separate evictions labeled "Inside" / "Outside".
    html = FIXTURE.replace("<th>Day 20</th><th>Day 23</th>", "<th>Inside</th><th>Outside</th>")
    w = {w["week"]: w for w in process_season(99, html)}[3]
    assert w["status"] == "ok" and w["note"] == "Two rounds: Inside / Outside"
    assert [r["sub_label"] for r in w["rounds"]] == ["Inside", "Outside"]


def test_twist_round_beside_an_eviction_is_not_called_a_double_eviction():
    html = FIXTURE.replace("<td>Gus<br /><small>2 of 3 votes<br />to evict</small></td>",
                           "<td>Gus<br /><small>Evicted by competition</small></td>")
    w = {w["week"]: w for w in process_season(99, html)}[3]
    assert w["note"] == "Two rounds: Day 20 / Day 23; Round 1 (Day 20): Non-standard outcome: Gus Evicted by competition"
    assert [r["evicted"] for r in w["rounds"]] == ["Dana"]
