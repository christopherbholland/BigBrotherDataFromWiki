# Notes for Claude

- Any change to `web/index.html`'s look or copy follows `docs/style-guide.md`: use the
  tokens and the shared components, and don't hard-code colors, sizes, weights, letter
  spacing or radii. `pytest -q tests/test_style.py` checks this.
- Check UI changes at desktop and 390px wide, in light and `?theme=dark`
  (`python tools/screenshots.py` retakes the README's screenshots).
