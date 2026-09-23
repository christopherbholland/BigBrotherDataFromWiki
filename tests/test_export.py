"""The whole build (export.run) on one cached season, written to a temporary folder.

Checks the top-level shape of weeks.json and details.json that the page and
other integrations rely on (see docs/integration.md). Skipped if the season
isn't in cache/.
"""
import json

import pytest

from bbgrid.config import FANDOM_CACHE_DIR, load_fandom_seasons, load_seasons
from bbgrid.export import SCHEMA_VERSION, run
from bbgrid.fetch import load_cached

SEASON = 26


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if load_cached(SEASON) is None:
        pytest.skip(f"BB{SEASON} not in cache/")
    out = tmp_path_factory.mktemp("build") / "web"
    seasons = {SEASON: load_seasons()[SEASON]}
    fandom = {SEASON: load_fandom_seasons()[SEASON]}
    doc, report = run(seasons=seasons, out_dir=out, fandom_seasons=fandom, fandom_dir=FANDOM_CACHE_DIR)
    return out, doc, report


def test_weeks_json(built):
    out, doc, _ = built
    on_disk = json.loads((out / "weeks.json").read_text(encoding="utf-8"))
    assert on_disk == doc
    assert set(doc) == {"schema_version", "generated_at", "license", "sources", "weeks", "photos"}
    assert doc["schema_version"] == SCHEMA_VERSION
    (source,) = doc["sources"]
    assert source["season"] == SEASON and "error" not in source
    assert source["permalink"].startswith("https://en.wikipedia.org/w/index.php?oldid=")
    assert source["fandom"]["permalink"].startswith("https://bigbrother.fandom.com/?oldid=")
    assert doc["weeks"] and all(w["season"] == SEASON for w in doc["weeks"])
    # Interpreter-internal keys never reach the output.
    assert not [k for w in doc["weeks"] for r in w["rounds"] for k in r if k.startswith("_")]
    assert not [k for w in doc["weeks"] for k in w if k.startswith("_")]


def test_details_json(built):
    out, doc, _ = built
    details = json.loads((out / "details.json").read_text(encoding="utf-8"))
    assert details["schema_version"] == SCHEMA_VERSION
    assert details["generated_at"] == doc["generated_at"]
    assert set(details) >= {"seasons", "categories", "formats", "weeks", "players"}
    # Every week in weeks.json has its details, under "<season>|<week_label>".
    assert {f"{w['season']}|{w['week_label']}" for w in doc["weeks"]} == set(details["weeks"])
    assert str(SEASON) in details["seasons"]


def test_report(built):
    out, doc, report = built
    assert (out.parent / "report.txt").read_text(encoding="utf-8") == report
    assert report.startswith(f"{len(doc['weeks'])} weeks: ")
    assert "SEASON ERROR" not in report
