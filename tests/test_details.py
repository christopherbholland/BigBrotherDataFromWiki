"""Detail-view data: votes, what was different, players, footnote text, episodes."""
from pathlib import Path

from bbgrid.episodes import episodes_by_week
from bbgrid.export import process_season_full
from bbgrid.grid import build_episode_grid, build_grid
from bbgrid.interpret import houseguests

FIXTURE = (Path(__file__).parent / "fixtures" / "synthetic_season.html").read_text()


def full(html=FIXTURE):
    return process_season_full(99, html)


def test_votes_split_into_votes_and_non_voters():
    week1 = full()["details"]["99|Week 1"]["rounds"][0]
    assert {(v["voter"], v["vote"]) for v in week1["votes"]} == {
        ("Casey", "Dana"), ("Hana", "Blair"), ("Eli", "Blair"), ("Gus", "Blair"), ("Fran", "Blair")}
    assert week1["by_nominee"] == [
        {"nominee": "Blair", "voters": ["Hana", "Eli", "Gus", "Fran"]},
        {"nominee": "Dana", "voters": ["Casey"]},
    ]
    # "Evicted (Day X)" cells are left out; HOH and nominees give a reason.
    assert week1["not_voting"] == [
        {"voter": "Alex", "reason": "Head of Household"},
        {"voter": "Dana", "reason": "Nominated"},
        {"voter": "Blair", "reason": "Nominated"},
    ]


def test_what_was_different():
    d = full()["details"]
    assert d["99|Week 1"]["special"]["items"] == ["AI Arena: Dana"]
    assert d["99|Week 2"]["special"]["items"] == []
    assert d["99|Week 3"]["special"]["items"] == ["Double eviction"]
    assert d["99|Week 4"]["special"]["items"] == []  # "Finale" alone isn't unusual


def test_footnote_text_reaches_the_week():
    html = FIXTURE.replace(
        "</div>\n",
        '<ol class="references"><li id="cite_note-b"><span class="mw-cite-backlink">^ a b</span>'
        '<span class="reference-text">Blair was the <i>first</i> evictee.<sup class="reference">'
        '<a href="#cite_note-9">[9]</a></sup></span></li></ol></div>\n', 1)
    assert build_grid(html).notes == {"b": "Blair was the first evictee."}
    notes = full(html)["details"]["99|Week 1"]["special"]["notes"]
    assert notes == [{"label": "b", "text": "Blair was the first evictee."}]


def test_houseguest_results_skip_jury_votes():
    guests = {g["name"]: g["result"] for g in houseguests(build_grid(FIXTURE))}
    assert guests["Alex"] == "Winner" and guests["Casey"] == "Runner-up"
    assert guests["Hana"] == "Third place"
    assert guests["Eli"] == "Evicted (Day 30)" and guests["Blair"] == "Evicted (Day 6)"


def test_player_stats():
    result = full()
    players = {p["name"]: p for p in result["players"]}
    assert result["unmatched"] == []
    alex = players["Alex"]
    assert alex["hoh"] == ["Week 1", "Week 4"]
    assert alex["veto"] == ["Week 3 (Day 23)"]
    assert alex["nominated"] == ["Week 3 (Day 20)", "Week 3 (Day 23)"]
    assert alex["on_block"] == ["Week 3 (Day 20)"]
    assert alex["votes_against"] == [{"week": "Week 3 (Day 20)", "voters": ["Hana"]}]
    assert players["Blair"]["evicted"] == "Week 1"
    assert players["Dana"]["twist"] == [{"week": "Week 1", "label": "AI Arena winner"}]
    assert players["Casey"]["votes_cast"][0] == {"week": "Week 1", "vote": "Dana", "with_house": False}


EPISODES = """<table class="wikitable wikiepisodetable">
<tr><th>No.<br>overall</th><th>No. in<br>season</th><th>Title</th><th>Day(s)</th><th>Original release date</th><th>U.S. viewers<br>(millions)</th></tr>
<tr><td colspan="6">Week 1</td></tr>
<tr class="vevent"><th>1</th><td>1</td><td>"Episode 1"</td><td>Day 1</td><td>July 17, 2024</td><td>2.75<sup class="reference"><a href="#cite_note-1">[1]</a></sup></td></tr>
<tr class="expand-child"><td colspan="6">The houseguests moved in.</td></tr>
<tr class="vevent"><th>2</th><td>2</td><td>"Episode 2"</td><td>Days 1–3</td><td>July 18, 2024</td><td>2.36</td></tr>
<tr><td colspan="6">Week 2</td></tr>
<tr class="vevent"><th>3</th><td>3</td><td>"Episode 3"</td><td>Day 8</td><td>TBA</td><td>N/A</td></tr>
</table>"""


def test_episodes_grouped_by_week():
    eps = episodes_by_week(build_episode_grid(EPISODES))
    assert list(eps) == ["Week 1", "Week 2"]
    first, second = eps["Week 1"]
    assert first == {"number_overall": "1", "number": "1", "title": "Episode 1", "days": "Day 1",
                     "air_date": "2024-07-17", "air_date_text": "July 17, 2024",
                     "viewers_millions": 2.75, "summary": "The houseguests moved in."}
    assert second["summary"] is None  # no summary row on the page
    (third,) = eps["Week 2"]
    assert third["air_date"] is None and third["air_date_text"] == "TBA" and third["viewers_millions"] is None


def test_page_without_episode_table():
    assert build_episode_grid("<p>nothing</p>") is None
    assert episodes_by_week(None) == {}


def _round(**kw):
    base = {"hoh": ["Hana"], "nominees_initial": ["Alex", "Casey"], "veto_winners": ["Alex"],
            "nominees_final": ["Casey", "Dana"], "extras": {}, "sub_label": None}
    return {**base, **kw}


def test_veto_use_from_nominations():
    from bbgrid.details import veto_use
    assert veto_use(_round()) == {"used": True, "on": ["Alex"], "replacements": ["Dana"], "twist_saved": []}
    assert veto_use(_round(nominees_final=["Alex", "Casey"]))["used"] is False
    # Someone saved by a twist row came off the block without the veto.
    three = _round(nominees_initial=["Alex", "Casey", "Eli"], nominees_final=["Casey", "Dana"],
                   extras={"AI Arena winner": ["Eli"]})
    assert veto_use(three) == {"used": True, "on": ["Alex"], "replacements": ["Dana"], "twist_saved": ["Eli"]}
    assert veto_use(_round(veto_winners=[])) is None


def _votes(in_house, out=()):
    return {"votes": [{"voter": n, "vote": "x"} for n in in_house], "not_voting": [{"voter": n, "reason": "Remained evicted (Day 30)"} for n in out]}


def test_veto_players_from_the_draw():
    """The HOH and nominees play; the summaries name the rest. Then anyone else didn't play."""
    from bbgrid.details import veto_players
    cast = ["Hana", "Alex", "Casey", "Dana", "Eli", "Fay", "Gus", "Rome"]
    rnd = _round(_voters=[(n, []) for n in cast])
    house = _votes(cast)
    said = ["During the Veto draw, Rome's backdoor plan is set in place as Eli and Fay are selected to compete alongside the nominees.",
            "Gus was chosen by houseguest's choice to play in the veto."]
    out = veto_players(rnd, house, said)
    assert out == {"players": ["Hana", "Alex", "Casey", "Eli", "Fay", "Gus"], "complete": True}  # not Rome: only his plan is named
    # Only two of the three named: someone missing may still have played.
    assert veto_players(rnd, house, said[:1])["complete"] is False
    # Nothing said and a big house: only the HOH and nominees are known.
    assert veto_players(rnd, house, []) == {"players": ["Hana", "Alex", "Casey"], "complete": False}
    # Six or fewer left in the house: everyone plays.
    small = _votes(cast[:6], out=cast[6:])
    assert veto_players(rnd, small, []) == {"players": cast[:6], "complete": True}
    assert veto_players(_round(veto_winners=[]), house, said) is None


def test_competition_names_tied_to_the_winner():
    from bbgrid.details import episode_insights
    record = {"rounds": [_round(hoh=["Makensy"], veto_winners=["Kimo"])]}
    episodes = [{"summary": 'In the "Eye Candy" Head of Household competition, Makensy emerged as the winner. '
                            'Everyone competed in the Power of Veto ("Eye in the Sky"). Kimo won it. '
                            'At the Veto Meeting, Kimo used the Veto on himself. '
                            'The live show ended with the "Warning Messages" HOH competition.'}]
    out = episode_insights(record, episodes)
    assert [(c["kind"], c["name"], c["winner"], c["round"]) for c in out["comps"]] == [
        ("hoh", "Eye Candy", "Makensy", 1),
        ("veto", "Eye in the Sky", "Kimo", 1),
        ("hoh", "Warning Messages", None, None),  # next week's HOH: mentioned, not tied
    ]
    assert out["veto_notes"] == ["At the Veto Meeting, Kimo used the Veto on himself."]


def test_week_details_include_veto_and_comps():
    d = full()["details"]["99|Week 1"]
    # Three nominees; Casey vetoes themselves off and nobody replaces them.
    assert d["rounds"][0]["veto"] == {"used": True, "on": ["Casey"], "replacements": [], "twist_saved": [],
                                      "players": {"players": ["Alex", "Blair", "Casey", "Dana"], "complete": False}}
    assert d["comps"] == [] and d["veto_notes"] == []


def test_finale_without_jury_votes():
    # The fixture's Finale column names the final three but has no jurors.
    f = full()["finale"]
    assert (f["week"], f["decided"], f["winner"], f["runner_up"]) == ("Week 4", True, "Alex", "Casey")
    assert f["finalists"] == [{"name": "Alex", "votes": 0, "jurors": []}, {"name": "Casey", "votes": 0, "jurors": []}]
    assert f["jury"] == []


def test_finale_jury_votes_counted_from_the_jurors():
    html = (FIXTURE
            .replace('<td colspan="2" style="background:salmon">Evicted (Day 23)</td>', "<td>Evicted (Day 23)</td><td>Casey</td>")
            .replace('<td colspan="3">Evicted (Day 20)</td>', '<td colspan="2">Evicted (Day 20)</td><td>Alex</td>')
            .replace('<td colspan="4">Evicted (Day 13)</td>', '<td colspan="3">Evicted (Day 13)</td><td>Alex</td>'))
    f = full(html)["finale"]
    assert f["finalists"] == [{"name": "Alex", "votes": 2, "jurors": ["Fran", "Gus"]},
                              {"name": "Casey", "votes": 1, "jurors": ["Dana"]}]
    # In the order they left, with how and when.
    assert [(j["name"], j["vote"], j["left"], j["day"]) for j in f["jury"]] == [
        ("Fran", "Alex", "Evicted", 13), ("Gus", "Alex", "Evicted", 20), ("Dana", "Casey", "Evicted", 23)]


def test_finale_while_airing():
    html = (FIXTURE.replace("<td>Winner</td>", "<td></td>").replace("<td>Runner-up</td>", "<td></td>")
            .replace('<td colspan="2" style="background:salmon">Evicted (Day 23)</td>', "<td>Evicted (Day 23)</td><td>Jury Member</td>"))
    f = full(html)["finale"]
    assert (f["decided"], f["winner"], f["finalists"]) == (False, None, [])
    assert f["jury"] == [{"name": "Dana", "vote": None, "left": "Evicted", "day": 23}]
