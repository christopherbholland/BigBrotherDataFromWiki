"""Snapshot tests: what's read from each cached Big Brother Wiki page.

Like test_snapshots.py, but for bbgrid/fandom.py. Snapshots live in
tests/snapshots/fandom_bbNN.json. To accept intentional changes:
    UPDATE_SNAPSHOTS=1 pytest tests/test_fandom_snapshots.py
Seasons that aren't in cache/fandom/ yet are skipped.
"""
import json
import os
from pathlib import Path

import pytest

from bbgrid.config import load_fandom_seasons
from bbgrid.fandom import parse_season
from bbgrid.fetch import load_fandom_cached

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.mark.parametrize("season", list(load_fandom_seasons()))
def test_fandom_snapshot(season):
    cached = load_fandom_cached(season)
    if cached is None:
        pytest.skip(f"BB{season} not in cache/fandom/")
    data = parse_season(cached, season)
    # JSON keys are strings; compare in that form.
    actual = json.loads(json.dumps(data, ensure_ascii=False))
    path = SNAPSHOT_DIR / f"fandom_bb{season}.json"
    if os.environ.get("UPDATE_SNAPSHOTS") or not path.exists():
        path.write_text(json.dumps(actual, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if not os.environ.get("UPDATE_SNAPSHOTS"):
            pytest.skip(f"wrote new snapshot {path.name}")
        return
    assert actual == json.loads(path.read_text(encoding="utf-8"))
