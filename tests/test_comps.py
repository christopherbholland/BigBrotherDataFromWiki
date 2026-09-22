"""Competition descriptions and categories, the cast table, and round matching."""
from bbgrid.cast import bios, cast_table
from bbgrid.comps import categorize, describe, sentences
from bbgrid.enrich import _round_for

CAST = """<table class="wikitable">
<tr><th>Name</th><th>Age</th><th>Occupation</th><th>Residence</th><th>Result</th></tr>
<tr><td>Jackson Michie</td><td>24</td><td>Server</td><td>Los Angeles, California</td><td>Winner</td></tr>
<tr><td>Olukemi "Kemi" Fakunle</td><td>25</td><td>Marketing<br>manager</td><td>Brooklyn, New York</td><td>Evicted</td></tr>
<tr><td>Nicole Franzel<br><small>Big Brother 16</small></td><td>28</td><td>Nurse</td><td>Ubly, Michigan</td><td>Winner</td></tr>
</table>"""


def test_cast_table_reads_age_job_and_hometown():
    rows = cast_table(CAST)
    assert rows[0] == {"full_name": "Jackson Michie", "age": 24, "occupation": "Server",
                       "hometown": "Los Angeles, California"}
    assert rows[1]["occupation"] == "Marketing manager"
    assert rows[2]["full_name"] == "Nicole Franzel"  # earlier seasons on a second line are dropped


def test_cast_names_match_the_voting_table():
    matched = bios(CAST, ["Michie", "Kemi", "Nicole F."])
    assert {k: v["full_name"] for k, v in matched.items()} == {
        "Michie": "Jackson Michie", "Kemi": 'Olukemi "Kemi" Fakunle', "Nicole F.": "Nicole Franzel"}


def test_description_is_the_sentence_naming_the_comp():
    sents = sentences([{"summary": 'Angela was evicted.\nIn the "Wall Street" HOH competition, HouseGuests '
                                   'had to hold on to a wall. Chelsie won.'}])
    assert describe("Wall Street", sents) == (
        'In the "Wall Street" HOH competition, HouseGuests had to hold on to a wall. Chelsie won.')
    assert describe("Nowhere", sents) is None


def test_categories_from_format_keywords_and_other_plays():
    comps = [
        {"format": "The Wall", "name": "A", "about": None},  # a known format
        {"format": "Mystery", "name": "B", "about": "Players answer true or false questions."},
        {"format": "Mystery", "name": "C", "about": None},  # same format, no description
        {"format": None, "name": "D", "about": "Players race to roll balls down a ramp."},
        {"format": None, "name": "E", "about": None},
    ]
    categorize(comps)
    assert [(c["category"], c["category_from"]) for c in comps] == [
        ("Endurance", "format"), ("Mental", "summary"), ("Mental", "other plays"),
        ("Physical", "summary"), (None, None)]


def test_same_winner_gets_one_comp_per_round():
    # Kyland won both of a double-eviction week's vetoes.
    record = {"rounds": [{"hoh": ["Kyland"], "veto_winners": ["Kyland"]},
                         {"hoh": ["Azah"], "veto_winners": ["Kyland"]}]}
    taken = set()
    first = _round_for(record, "veto", ["Kyland"], taken)
    taken.add(("veto", first))
    assert (first, _round_for(record, "veto", ["Kyland"], taken)) == (1, 2)


WALL_LEAD = """{{Recurring Competition
| image= [[File:Wall.jpg|225px]]
| description= Hang on to a moving wall as long as you can.
}}'''{{PAGENAME}}''' is a recurring endurance [[Head of Household]] and [[Re-Entry Competition|Re-Entry]] competition.
"""


def test_format_page_gives_type_and_description():
    from bbgrid.fandom import format_info
    assert format_info(WALL_LEAD) == {"description": "Hang on to a moving wall as long as you can.",
                                      "category": "Endurance"}
    # A page whose opening sentence names no type leaves the category to comps.py.
    assert format_info(WALL_LEAD.replace("endurance ", ""))["category"] is None


def test_wiki_type_wins_over_guesses():
    comps = [{"format": "The Wall", "name": "A", "about": "Players answer questions.", "wiki_category": "Mental"}]
    categorize(comps)
    assert (comps[0]["category"], comps[0]["category_from"]) == ("Mental", "wiki")
