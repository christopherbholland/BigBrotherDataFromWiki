"""seasons.yaml: season ranges, title patterns and exceptions."""
import pytest

from bbgrid.config import load_fandom_seasons, load_seasons, season_numbers


def test_season_numbers():
    assert season_numbers("21-28") == list(range(21, 29))
    assert season_numbers(26) == [26]
    assert season_numbers(["1-3", 26, "2"]) == [1, 2, 3, 26]
    with pytest.raises(ValueError):
        season_numbers("BB26")


def test_patterns_and_exceptions(tmp_path):
    path = tmp_path / "seasons.yaml"
    path.write_text("""
seasons: ["1-3", 26]
titles:
  wikipedia: "Big Brother {n} (American season)"
  fandom: "Big Brother {n} (US)"
exceptions:
  wikipedia:
    2: "Big Brother 2 (special)"
  fandom:
    3: null
""", encoding="utf-8")
    assert load_seasons(path) == {
        1: "Big Brother 1 (American season)", 2: "Big Brother 2 (special)",
        3: "Big Brother 3 (American season)", 26: "Big Brother 26 (American season)"}
    assert list(load_fandom_seasons(path)) == [1, 2, 26]


def test_repo_seasons_file():
    wiki, fandom = load_seasons(), load_fandom_seasons()
    assert wiki[26] == "Big Brother 26 (American season)" and fandom[26] == "Big Brother 26 (US)"
    assert set(fandom) <= set(wiki)
