"""Infobox reading from wikitext (bbgrid/wikitext.py)."""
from datetime import date

from bbgrid import wikitext as wt

INFOBOX = """{{Houseguest
|Currently = Jury Member
|Image = <gallery>
A.jpg|BB2
</gallery>
|hometown = Springfield, IL<br>Shelbyville, IL
|occupation = [[wikipedia:Teacher|Teacher]]
|birthdate = {{Birth date and age|1990|4|2|mf=yes}}
|SeasonFullName = [[Big Brother 1 (US)]]
|Place = 5th
|Alliances = [[The Four]]<br>[[Side Deal|The Side Deal]]<!-- a comment -->
|Season2 = 2 (US)
|Place2 = 3rd
|Loyalties2 = {{bb2|Casey}}
}}'''Alex Quinn Stone''' was a houseguest on ''[[Big Brother 1 (US)]]''."""


def test_template_params_handle_nesting_and_elements():
    p = wt.template_params(INFOBOX, "Houseguest")
    assert p["Place"] == "5th" and p["Place2"] == "3rd"
    assert "gallery" not in p["Image"] and "BB2" not in p  # gallery lines don't become fields
    assert wt.template_params("{{Template:houseguest|a=1}}", "Houseguest") == {"a": "1"}
    assert wt.template_params("no infobox", "Houseguest") is None


def test_plain_and_lines():
    p = wt.template_params(INFOBOX, "Houseguest")
    assert wt.lines(p["hometown"]) == ["Springfield, IL", "Shelbyville, IL"]
    assert wt.plain(p["occupation"]) == "Teacher"
    assert wt.lines(p["Alliances"]) == ["The Four", "The Side Deal"]
    assert wt.links(p["Alliances"]) == ["The Four", "Side Deal"]
    assert wt.plain(p["Loyalties2"]) == "Casey"
    assert wt.plain("''{{PAGENAME}}''") == ""


def test_birth_date_and_bold_lead():
    assert wt.birth_date("{{Birth date and age|1990|4|2|mf=yes}}") == date(1990, 4, 2)
    assert wt.birth_date("unknown") is None
    assert wt.bold_lead(INFOBOX) == "Alex Quinn Stone"
