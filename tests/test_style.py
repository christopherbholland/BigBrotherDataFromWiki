"""web/index.html follows docs/style-guide.md: values come from the tokens.

Every color, font size, font weight, letter spacing and corner radius is a token
(a custom property in the top :root block), so a new rule can't drift from the
rest of the page. Each test names the rule it checks; the guide says what to use.
"""
import re
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")
_style = re.search(r"<style>(.*?)</style>", PAGE, re.S)
CSS = _style.group(1)
CSS_FIRST_LINE = PAGE.count("\n", 0, _style.start(1)) + 1  # so failures name lines of index.html
SCRIPT = PAGE[PAGE.index("<script>"):]

COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(")


def declarations(css=CSS):
    """(property, value, line number) for each declaration, comments removed."""
    css = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), css, flags=re.S)
    for m in re.finditer(r"([-\w]+)\s*:\s*([^;{}]+)", css):
        prop, value = m.group(1), m.group(2).strip()
        # Skip selectors that look like declarations (a:hover, th:first-child ...).
        if css[m.end():m.end() + 1] == "{" or re.match(r"(hover|focus|first|last|nth|not|has|only|focus-visible)\b", value):
            continue
        yield prop, value, CSS_FIRST_LINE + css.count("\n", 0, m.start())


def offenders(check):
    return [f"web/index.html:{line}: {prop}: {value} (use a token, see docs/style-guide.md)" for prop, value, line in declarations()
            if not prop.startswith("--") and check(prop, value)]


def test_colors_are_tokens():
    """Colors (hex, rgb(), hsl()) are written only in custom properties."""
    assert offenders(lambda p, v: COLOR.search(v)) == []


def test_font_sizes_are_tokens():
    """font-size, and the size in a font shorthand, is a --fs-* token."""
    def bad(prop, value):
        if prop == "font-size":
            return not re.fullmatch(r"var\(--fs-[\w]+\)", value)
        if prop == "font":
            return value != "inherit" and "var(--fs-" not in value
        return False
    assert offenders(bad) == []


def test_font_weights_are_tokens():
    assert offenders(lambda p, v: p == "font-weight" and not re.fullmatch(r"var\(--fw-\w+\)", v)) == []


def test_letter_spacing_is_a_token():
    assert offenders(lambda p, v: p == "letter-spacing" and v != "0" and not re.fullmatch(r"var\(--track-\w+\)", v)) == []


def test_radii_are_tokens():
    """border-radius is made of --r-* tokens (or 0), one per corner at most."""
    def bad(prop, value):
        return prop == "border-radius" and not all(
            part == "0" or re.fullmatch(r"var\(--r-[\w]+\)", part) for part in value.split())
    assert offenders(bad) == []


def test_every_token_used_is_defined():
    """A var(--name) with a typo would silently fall back to nothing."""
    defined = set(re.findall(r"(--[\w-]+)\s*:", CSS)) | {"--strip"}  # --strip is set inline by the script
    # A name the script completes (var(--cat-${...})) is checked by its prefix.
    used = {n for n in re.findall(r"var\((--[\w-]+)", PAGE) if not n.endswith("-")}
    assert all(any(d.startswith(n) for d in defined) for n in re.findall(r"var\((--[\w-]+-)\$", PAGE))
    assert used - defined == set()


def test_dark_blocks_match():
    """The system dark theme and ?theme=dark set exactly the same values."""
    system = re.search(r'@media \(prefers-color-scheme: dark\) \{\s*:root:not\(\[data-theme="light"\]\) \{(.*?)\}\s*\}', CSS, re.S)
    pinned = re.search(r':root\[data-theme="dark"\] \{(.*?)\}', CSS, re.S)
    assert system and pinned
    norm = lambda block: sorted(re.findall(r"([-\w]+)\s*:\s*([^;]+);", block))
    assert norm(system.group(1)) == norm(pinned.group(1))


def test_light_theme_defines_every_dark_token():
    """A token that only exists in the dark theme would be unset in light mode."""
    light = re.search(r":root \{(.*?)\n\}", CSS, re.S).group(1)
    dark = re.search(r':root\[data-theme="dark"\] \{(.*?)\}', CSS, re.S).group(1)
    names = lambda block: set(re.findall(r"(--[\w-]+)\s*:", block))
    assert names(dark) - names(light) == set()


def test_inline_styles_only_carry_data():
    """style="..." in the markup only passes data (a series color, a bar's size, a
    custom property); everything else is a class, so it follows the tokens too."""
    allowed = {"background", "width", "height"}
    bad = []
    for m in re.finditer(r'style="([^"]*)"', PAGE):
        for decl in filter(None, (d.strip() for d in m.group(1).split(";"))):
            prop = decl.split(":", 1)[0].strip()
            if not (prop.startswith("--") or prop in allowed):
                bad.append(f"web/index.html:{PAGE.count(chr(10), 0, m.start()) + 1}: {decl}")
    assert bad == []


def test_script_writes_no_colors():
    """Colors reach the markup as var(--token), never as literals in the script."""
    assert [m.group() for m in COLOR.finditer(SCRIPT)] == []
