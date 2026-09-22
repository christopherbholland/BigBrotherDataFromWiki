"""Retake the screenshots in docs/screenshots/ from the page in web/.

Serves web/ on a local port, opens each view in headless Chromium and saves a PNG
at 2x. Each shot keeps the scene, size and theme that the README and wiki captions
describe, so after a style change you can rerun this and commit the images.

    pip install playwright
    playwright install chromium        # skip if you already have Chromium
    python scripts/screenshots.py      # all shots
    python scripts/screenshots.py grid-note mobile-week   # just these

Set CHROMIUM=/path/to/chrome (or pass --chromium) to use a browser that's already
installed instead of Playwright's own download.
"""

import argparse
import functools
import http.server
import os
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
OUT = ROOT / "docs" / "screenshots"

DESKTOP_GRID = (1320, 740)
DESKTOP_TALL = (1320, 900)
PHONE = (390, 800)

# name: (color scheme, viewport, hash, what to do once the page has loaded)
SHOTS = {
    "grid-double-eviction": ("light", DESKTOP_GRID, "", ("hover", 26, 10)),
    "grid-split-house-dark": ("dark", DESKTOP_GRID, "", ("hover", 24, 7)),
    "grid-note": ("light", DESKTOP_GRID, "", ("hover", 21, 3)),
    "details-week": ("light", DESKTOP_TALL, "#week=26/Week%204", ("drawer",)),
    "details-player": ("light", DESKTOP_TALL, "#player=26/Angela", ("drawer",)),
    "players-dark": ("dark", DESKTOP_TALL, "#players=28", ("players",)),
    "mobile-week": ("dark", PHONE, "", ()),
    "mobile-details": ("dark", PHONE, "#week=26/Week%2010", ("drawer",)),
}


def serve():
    """Serve web/ on a free port in a background thread; returns the base URL."""
    handler = functools.partial(QuietHandler, directory=str(WEB))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def hover_cell(page, season, week):
    """Move the mouse over one grid cell so its tooltip shows."""
    box = page.evaluate(
        """([season, week]) => {
          const cols = [...document.querySelectorAll('.grid thead th')].map(t => t.textContent.trim());
          const ci = cols.indexOf('Wk ' + week);
          const row = [...document.querySelectorAll('.grid tbody tr')]
            .find(r => r.querySelector('th').textContent.trim() === 'BB' + season);
          if (!row || ci < 0) return null;
          const r = row.children[ci].querySelector('.cell').getBoundingClientRect();
          return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }""",
        [season, week],
    )
    if box is None:
        raise SystemExit(f"No grid cell for BB{season} week {week}")
    page.mouse.move(box["x"], box["y"])
    page.wait_for_selector("#tip", state="visible")


def take(browser, base, name):
    scheme, (width, height), hash_, action = SHOTS[name]
    page = browser.new_page(
        viewport={"width": width, "height": height}, device_scale_factor=2, color_scheme=scheme
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + hash_)
    page.wait_for_selector(".cell", state="attached")
    if action and action[0] == "hover":
        hover_cell(page, *action[1:])
    elif action and action[0] == "drawer":
        page.wait_for_function(
            "() => !document.querySelector('#drawer').hidden"
            " && !/Loading/.test(document.querySelector('#drawer-body').textContent)"
        )
    elif action and action[0] == "players":
        page.wait_for_selector("table.players")
    page.wait_for_timeout(200)  # let hover and focus styles settle
    page.screenshot(path=str(OUT / f"{name}.png"))
    page.close()
    if errors:
        raise SystemExit(f"{name}: page error: {errors[0]}")
    print(f"docs/screenshots/{name}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("names", nargs="*", metavar="name", help=f"shots to take (default: all): {', '.join(SHOTS)}")
    parser.add_argument("--chromium", default=os.environ.get("CHROMIUM"), help="path to a Chromium binary")
    args = parser.parse_args()
    unknown = [n for n in args.names if n not in SHOTS]
    if unknown:
        parser.error(f"unknown shot(s): {', '.join(unknown)}")

    OUT.mkdir(parents=True, exist_ok=True)
    base = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium) if args.chromium else p.chromium.launch()
        try:
            for name in args.names or SHOTS:
                take(browser, base, name)
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
