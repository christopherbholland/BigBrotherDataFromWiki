"""Big Brother Wiki parsing and merging, on tests/fixtures/fandom_season.html.

That page is SYNTHETIC: the houseguests and events are made up. Its markup
copies the real season pages' Houseguests, Have/Have-Not History, Competition
History and Game History sections.
"""
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from bbgrid import fandom
from bbgrid.enrich import Names, cross_check, enrich_season, norm

FIXTURE = Path(__file__).parent / "fixtures" / "fandom_season.html"
LEAD = """{{Houseguest
|hometown = Springfield, IL
|occupation = Teacher
|birthdate = {{Birth date and age|1990|7|20}}
|SeasonFullName = [[Big Brother 1 (US)]]
|Place = 1st
|Days = 30
|Alliances = [[The Four]]
}}'''Alex Quinn Stone''' won."""


@pytest.fixture(scope="module")
def soup():
    return BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "lxml")


def test_roster(soup):
    assert fandom.houseguest_links(soup) == [
        ("Alex Stone", "Alex"), ("Robin Park", "Robin"), ("Sam Lee", "Sam L"),
        ("Sam Ortiz", "Sam O"), ("Jordan Kay", "Jordan")]


def test_competitions(soup):
    comps = fandom.competitions(soup)
    assert [(c["week"], c["kind"], c["name"], c["winners"]) for c in comps] == [
        (1, "hoh", "Hold On Tight", ["Alex"]),
        (1, "veto", "Puzzle Box", ["Robin"]),
        (1, "twist", "Last Chance", ["Jordan"]),
        (2, "hoh", "Endurance Run", ["Sam L"]),
        (2, "veto", None, ["Sam O", "Robin"]),  # "TBA" name; the TBD row is dropped
    ]
    assert comps[0]["format"] == "Wall Format" and comps[1]["format"] is None
    assert comps[2]["outcome"] == "is saved" and comps[2]["day"] == "6"


def test_have_nots(soup):
    hn = fandom.have_nots(soup)
    assert hn["weeks"] == {1: [{"guest": "Robin Park", "chosen_by": None},
                               {"guest": "Sam Lee", "chosen_by": "Robin"}]}
    assert hn["hoh"] == {1: ["Alex Stone"]}


def test_game_history(soup):
    rows = fandom.game_history(soup)
    assert [(r["week"], r["hoh"], r["veto_used"], r["nominees_final"], r["evicted"]) for r in rows] == [
        (1, ["Alex"], True, ["Sam O", "Jordan"], ["Sam O"]),
        (2, ["Sam L"], False, ["Alex", "Jordan"], ["Jordan"]),
    ]
    assert rows[0]["vote"] == "3-0" and rows[0]["finish"] == "1st Evicted Day 7"


def test_houseguest_bio():
    bio = fandom.houseguest_bio("Alex Stone", LEAD, 1, premiere="2020-07-19")
    assert bio["full_name"] == "Alex Quinn Stone"
    assert bio["age"] == 29  # birthday falls the day after the premiere
    assert bio["hometown"] == ["Springfield, IL"] and bio["place"] == "1st" and bio["days"] == "30"
    assert bio["alliances"] == ["The Four"] and bio["seasons"] == ["Big Brother 1 (US)"]
    assert fandom.houseguest_bio("Alex Stone", LEAD, 2)["place"] is None  # no fields for another season
    assert fandom.houseguest_bio("X", "no infobox", 1) is None


def test_season_info():
    info = fandom.season_info("{{Season\n|seasonrun = July 19, 2020 - September 1, 2020\n|prizemoney = $1\n}}")
    assert info["premiere"] == "2020-07-19" and info["finale"] == "2020-09-01" and info["prize"] == "$1"


def test_names_match_across_wikis():
    roster = [("Jackson Michie", "Jackson"), ("Nicole Anthony", "Nicole A"), ("Nicole Franzel", "Nicole F"),
              ("Azah Awasum", "Azah"), ("LaTrice Verrett", "LaTrice")]
    names = Names(roster, ["Michie", "Nicole A.", "Nicole F.", "Azäh", "La Trice", "Nobody"])
    assert names.page == {"Michie": "Jackson Michie", "Nicole A.": "Nicole Anthony",
                          "Nicole F.": "Nicole Franzel", "Azäh": "Azah Awasum", "La Trice": "LaTrice Verrett"}
    assert names.unmatched == ["Nobody"]
    assert names("Jackson") == "Michie" and names("Nicole A") == "Nicole A." and names("Azah") == "Azäh"
    assert names("Stranger") == "Stranger" and names.unknown == {"Stranger"}
    assert norm("T’kor") == norm("T'kor")


def _record(rounds):
    base = {"sub_label": None, "hoh": [], "nominees_initial": [], "veto_winners": [], "nominees_final": [],
            "evicted": None, "tally": None, "extras": {}}
    return {"season": 1, "week": 1, "week_label": "Week 1", "rounds": [{**base, **r} for r in rounds]}


def test_cross_check_ignores_twist_saved_nominee():
    record = _record([{"hoh": ["Alex"], "nominees_initial": ["Sam L", "Sam O"], "veto_winners": ["Robin"],
                       "nominees_final": ["Sam O"], "evicted": "Sam O", "extras": {"Arena winner": ["Jordan"]}}])
    details = {"rounds": [{"veto": {"used": True}}]}
    row = {"hoh": ["Alex"], "nominees_initial": ["Sam L", "Sam O"], "veto_holders": ["Robin"], "veto_used": True,
           "nominees_final": ["Sam O", "Jordan"], "evicted": ["Sam O"]}
    assert cross_check(record, details, [row]) == []
    row = {**row, "hoh": ["Robin"], "veto_used": False}
    assert cross_check(record, details, [row]) == [
        {"round": 1, "field": "HOH", "wikipedia": ["Alex"], "fandom": ["Robin"]},
        {"round": 1, "field": "Veto used", "wikipedia": ["Yes"], "fandom": ["No"]},
    ]


def test_enrich_season(soup):
    data = {
        "info": fandom.season_info("{{Season\n|seasonrun = July 19, 2020 - September 1, 2020\n}}"),
        "roster": fandom.houseguest_links(soup),
        "competitions": fandom.competitions(soup),
        "have_nots": fandom.have_nots(soup),
        "game": fandom.game_history(soup),
        "bios": {"Alex Stone": {**fandom.houseguest_bio("Alex Stone", LEAD, 1, "2020-07-19"), "revid": 5}},
    }
    weeks = [_record([{"hoh": ["Alex"], "nominees_initial": ["Sam L.", "Sam O."], "veto_winners": ["Robin"],
                       "nominees_final": ["Sam O."], "evicted": "Sam O.", "extras": {"Arena winner": ["Jordan"]}}])]
    details = {"1|Week 1": {"rounds": [{"veto": {"used": True}}], "episodes": [
        {"summary": 'In the "Hold On Tight" HOH competition, HouseGuests had to hang on to a rope. Alex won.'}]}}
    players = [{"season": 1, "name": n} for n in ["Alex", "Robin", "Sam L.", "Sam O.", "Jordan"]]
    entry, report = enrich_season(1, data, {"title": "Big Brother 1 (US)", "revid": 9}, weeks, details, players)
    f = details["1|Week 1"]["fandom"]
    assert [(c["name"], c["winners"], c["round"], c["won"]) for c in f["comps"]] == [
        ("Hold On Tight", ["Alex"], 1, True), ("Puzzle Box", ["Robin"], 1, True), ("Last Chance", ["Jordan"], None, True)]
    assert f["have_nots"] == [{"name": "Robin", "chosen_by": None}, {"name": "Sam L.", "chosen_by": "Robin"}]
    assert f["checks"] == []
    alex = players[0]["fandom"]
    assert alex["full_name"] == "Alex Quinn Stone" and alex["url"].endswith("/wiki/Alex_Stone")
    assert players[1]["fandom"]["have_not"] == ["Week 1"]
    assert f["comps"][0]["about"] == ('In the "Hold On Tight" HOH competition, HouseGuests had to hang on to '
                                      'a rope. Alex won.')
    assert players[4]["fandom"]["twist_wins"] == [
        {"week": "Week 1", "type": "Arena", "name": "Last Chance", "outcome": "is saved", "prize": None}]
    assert entry["premiere"] == "2020-07-19" and entry["permalink"].endswith("oldid=9")
    # Four houseguests have no bio in this test; that is reported, nothing else is.
    assert len(report) == 4 and all("no houseguest infobox" in line for line in report)
