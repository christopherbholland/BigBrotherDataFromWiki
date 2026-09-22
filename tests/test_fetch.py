"""Fetcher test with a stubbed HTTP session (no network)."""
import json

from bbgrid.fetch import USER_AGENT, fetch_season, load_cached


class StubResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"parse": {"title": "T", "revid": 123, "text": "<table></table>"}}


class StubSession:
    def get(self, url, params, headers, timeout):
        self.params, self.headers = params, headers
        return StubResponse()


def test_fetch_writes_html_and_meta(tmp_path):
    session = StubSession()
    meta = fetch_season(26, "Big Brother 26 (American season)", cache_dir=tmp_path, session=session)
    assert session.params["page"] == "Big Brother 26 (American season)"
    assert session.params["prop"] == "text|revid" and session.params["formatversion"] == "2"
    assert session.headers["User-Agent"] == USER_AGENT
    html, cached_meta = load_cached(26, tmp_path)
    assert html == "<table></table>"
    assert cached_meta == meta and meta["revid"] == 123 and meta["fetched_at"]
    assert json.loads((tmp_path / "bb26.meta.json").read_text())["title"] == "Big Brother 26 (American season)"
