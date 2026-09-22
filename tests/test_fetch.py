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


FANDOM_HTML = """<h2>Houseguests</h2><table><tr><td><div><b><a href="/wiki/Alex_Stone" title="Alex Stone">Alex</a></b>
</div></td><td><div><b><a href="/wiki/Robin" title="Robin">Robin</a></b></div></td></tr></table><h2>Trivia</h2>"""


class FandomSession:
    """Answers the parse call, then one query for the houseguest pages (Robin redirects)."""

    def __init__(self):
        self.calls = []

    def get(self, url, params, headers, timeout):
        self.calls.append(params)
        session = self

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                if params["action"] == "parse":
                    return {"parse": {"revid": 7, "text": FANDOM_HTML, "wikitext": "{{Season}}"}}
                assert set(params["titles"].split("|")) == {"Alex Stone", "Robin"}
                assert len(session.calls) == 2
                lead = "{{Houseguest|Place=1st}}\n'''Alex''' won.\n==Biography==\nLong text."
                return {"query": {
                    "redirects": [{"from": "Robin", "to": "Robin Park"}],
                    "pages": [{"title": "Alex Stone", "revisions": [{"revid": 11, "slots": {"main": {"content": lead}}}]},
                              {"title": "Robin Park", "revisions": [{"revid": 12, "slots": {"main": {"content": "x"}}}]}],
                }}
        return Resp()


def test_fetch_fandom_writes_page_and_houseguest_leads(tmp_path, monkeypatch):
    import bbgrid.fetch as fetch
    monkeypatch.setattr(fetch, "PAUSE", 0)
    session = FandomSession()
    meta = fetch.fetch_fandom_season(26, "Big Brother 26 (US)", cache_dir=tmp_path, session=session)
    assert session.calls[0]["prop"] == "text|revid|wikitext" and session.calls[0]["page"] == "Big Brother 26 (US)"
    assert meta["revid"] == 7 and meta["houseguest_pages"] == 2 and meta["missing_pages"] == []
    cached = fetch.load_fandom_cached(26, tmp_path)
    assert cached["wikitext"] == "{{Season}}" and cached["html"] == FANDOM_HTML
    # Only the lead section is kept, and a redirected page is stored under the asked-for title.
    assert cached["houseguests"]["Alex Stone"]["lead"] == "{{Houseguest|Place=1st}}\n'''Alex''' won.\n"
    assert cached["houseguests"]["Robin"] == {"title": "Robin Park", "revid": 12, "lead": "x"}
    assert fetch.load_fandom_cached(27, tmp_path) is None


def test_fetch_fandom_also_fetches_competition_format_pages(tmp_path, monkeypatch):
    import bbgrid.fetch as fetch
    html = FANDOM_HTML + """<h2>Competition History</h2><table class="wikitable">
<tr><th>Week</th><th>Day</th><th>Type</th><th>Name</th><th>Result</th></tr>
<tr><td>1</td><td>1</td><td>HOH</td><td><a href="/wiki/The_Wall" title="The Wall">Firewall</a></td><td>Alex<br>wins HOH</td></tr>
</table><h2>Game History</h2>"""
    monkeypatch.setattr(fetch, "PAUSE", 0)
    monkeypatch.setattr(fetch, "fetch_page", lambda *a, **k: (html, 7, "{{Season}}"))
    asked = []
    monkeypatch.setattr(fetch, "fetch_leads", lambda titles, session=None: asked.append(sorted(titles)) or {
        t: {"title": t, "revid": 1, "lead": "x"} for t in titles})
    meta = fetch.fetch_fandom_season(26, "Big Brother 26 (US)", cache_dir=tmp_path, session=object())
    assert asked == [["Alex Stone", "Robin"], ["The Wall"]]
    assert meta["format_pages"] == 1
    assert fetch.load_fandom_cached(26, tmp_path)["formats"]["The Wall"]["lead"] == "x"
