"""America's Favorite HouseGuest on a synthetic page (made-up houseguests)."""
from bbgrid.afh import afh, check, names_in

PEOPLE = [("Remy", "Remy Castillo"), ("Dana K.", "Dana Kirby"), ("Dana W.", "Dana Wells"),
          ("America", "America Soto"), ("Jo", "Jo Park")]

PAGE = """<div class="mw-parser-output">
<table class="infobox"><tr><th>Winner</th><td>Jo Park</td></tr>
<tr><th>America's Favorite HouseGuest</th><td>Dana Kirby<sup>[1]</sup></td></tr></table>
<p>Jo Park won 5–2. Dana Kirby was voted America's Favorite HouseGuest, winning the $50,000 prize.</p>
<div class="mw-heading mw-heading2"><h2>Format</h2></div>
<p>The viewing public is able to award an additional prize by choosing "America's Favorite HouseGuest".</p>
</div>"""

EPISODES = [{"title": "Episode 40", "summary":
             "Jo wins. Julie reveals that Remy, Dana K. and America placed in the top 3 for America's "
             "Favorite HouseGuest, and Dana K. wins."}]


def test_reads_the_winner_top_three_prize_and_quotes():
    a = afh(PAGE, PEOPLE, EPISODES)
    assert a["winner"] == "Dana K." and a["winner_text"] == "Dana Kirby"
    assert (a["others_label"], a["others"]) == ("Top 3", ["Remy", "America"])
    assert a["prize"] == "$50,000"
    # The Format section's general description isn't quoted.
    assert [n["where"] for n in a["notes"]] == ["Introduction", "Episode 40"]


def test_runner_up_sentence():
    eps = [{"title": "Finale", "summary": "Dana K. was named America's Favorite HouseGuest with Remy as runner-up."}]
    a = afh(PAGE, PEOPLE, eps)
    assert (a["others_label"], a["others"]) == ("Runner-up", ["Remy"])


def test_names_skip_the_award_and_shared_first_names():
    # "America" in the award's title isn't the houseguest; "Dana" alone is ambiguous.
    assert names_in("Dana was voted America's Favorite HouseGuest over America", PEOPLE) == ["America"]


def test_no_infobox_row_while_airing():
    assert afh("<table class='infobox'><tr><th>Winner</th><td></td></tr></table>", PEOPLE) is None
    assert check(28, None, [], decided=False) == []
    assert check(27, None, [], decided=True)


def test_check_takes_the_wiki_prize_and_reports_disagreements():
    a = afh(PAGE, PEOPLE, EPISODES)
    players = [{"name": "Remy", "fandom": {"other_prizes": ["$50,000 & 7-Day Cruise (Fan Favorite)"]}}]
    lines = check(27, a, players, decided=True)
    assert a["prize"] == "$50,000 & 7-Day Cruise"
    assert lines == ["BB27: America's Favorite HouseGuest: Wikipedia Dana K. / Fandom Remy"]
