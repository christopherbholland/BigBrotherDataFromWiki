"""Snapshot tests: interpreter output per cached season.

Any code change that alters a week's record shows up as a diff here.
Snapshots live in tests/snapshots/bbNN.json. To accept intentional changes:
    UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py
Seasons that aren't in cache/ yet are skipped.
"""
import json
import os
from pathlib import Path

import pytest

from bbgrid.config import load_seasons
from bbgrid.export import process_season
from bbgrid.fetch import load_cached

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.mark.parametrize("season", list(load_seasons()))
def test_season_snapshot(season):
    cached = load_cached(season)
    if cached is None:
        pytest.skip(f"BB{season} not in cache/")
    actual = process_season(season, cached[0])
    path = SNAPSHOT_DIR / f"bb{season}.json"
    if os.environ.get("UPDATE_SNAPSHOTS") or not path.exists():
        path.write_text(json.dumps(actual, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if not os.environ.get("UPDATE_SNAPSHOTS"):
            pytest.skip(f"wrote new snapshot {path.name}")
        return
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual == expected
