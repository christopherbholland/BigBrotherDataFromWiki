"""Retake the README's screenshots (docs/screenshots/*.png) from web/.

    pip install playwright && playwright install chromium
    python tools/screenshots.py                 # all of them
    python tools/screenshots.py grid-note       # just some

Serves web/ on a local port and drives Chromium through each view. Houseguest
photos are blocked on purpose, so faces show as initials: the photos are CBS's
images, and the repository links to them rather than copying them (see
docs/licensing.md). Set CHROMIUM to use a browser that's already installed.
"""
import functools
import http.server
import os
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
PHOTO_HOST = "**/static.wikia.nocookie.net/**"

DESKTOP = {"width": 1320, "height": 900}
GRID = {"width": 1320, "height": 740}
PHONE = {"width": 390, "height": 800}

# name: (viewport, URL after the host, grid cell to hover as (season, week label) or None)
SHOTS = {
    "grid-double-eviction": (GRID, "", (26, "Week 10")),
    "grid-split-house-dark": (GRID, "?theme=dark", (24, "Week 7")),
    "grid-note": (GRID, "", (21, "Week 3")),
    "mobile-week": (PHONE, "", None),
    "details-week": (DESKTOP, "#week=26/Week%204", None),
    "players-dark": (DESKTOP, "?theme=dark#players=28", None),
    "details-player": (DESKTOP, "#player=26/Angela", None),
    "comps": (DESKTOP, "#comps=28", None),
    "comp-format": (DESKTOP, "#comp=The%20Wall", None),
    "endgame": (DESKTOP, "#endgame=26", None),
    "mobile-details": (PHONE, "#week=26/Week%2010", None),
}

# True once every face picture on screen has given way to initials.
FACES_SETTLED = """() => [...document.querySelectorAll('img.face')].every(i => {
  const r = i.getBoundingClientRect();
  return !r.width || r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth;
})"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def take(browser, base, name, viewport, path, hover):
    phone = viewport is PHONE
    ctx = browser.new_context(viewport=viewport, device_scale_factor=2, is_mobile=phone, has_touch=phone)
    page = ctx.new_page()
    page.route(PHOTO_HOST, lambda route: route.abort())
    page.goto(base + path)
    page.wait_for_selector("table.grid", state="attached")
    for view in ("players", "comps", "endgame"):
        if f"#{view}=" in path:
            page.wait_for_selector(f"#{view}-panel table")
    if "#week=" in path or "#player=" in path or "#comp=" in path:
        page.wait_for_selector("#drawer:not([hidden])")
        page.wait_for_function("!document.querySelector('#drawer-body').innerText.includes('Loading')")
    if hover:
        season, label = hover
        index = page.evaluate("([s, l]) => DATA.weeks.findIndex(w => w.season === s && w.week_label === l)",
                              [season, label])
        page.hover(f'button.cell[data-i="{index}"]')
        page.wait_for_selector("#tip", state="visible")
    page.wait_for_function(FACES_SETTLED, timeout=10000)
    page.wait_for_timeout(300)  # let transitions finish
    page.screenshot(path=OUT / f"{name}.png")
    ctx.close()


def main(names):
    unknown = [n for n in names if n not in SHOTS]
    if unknown:
        sys.exit(f"unknown screenshots: {unknown}; choose from {list(SHOTS)}")
    server = serve(ROOT / "web")
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
            for name in names or SHOTS:
                viewport, path, hover = SHOTS[name]
                take(browser, base, name, viewport, path, hover)
                print(f"wrote docs/screenshots/{name}.png")
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main(sys.argv[1:])
