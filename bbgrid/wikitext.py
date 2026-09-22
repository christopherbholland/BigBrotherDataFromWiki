"""Read template parameters (infoboxes) out of MediaWiki source text.

Knows wikitext syntax only, nothing about Big Brother. Used for the Big Brother
Wiki's {{Season}} and {{Houseguest}} infoboxes, whose fields are easier to read
from the source than from the rendered page.
"""
import re
from datetime import date

COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
# Whole elements whose contents are never plain field text.
DROP_ELEMENTS_RE = re.compile(r"<(gallery|tabber|ref)\b[^>]*>.*?</\1\s*>|<ref\b[^>]*/>", re.S | re.I)
BR_RE = re.compile(r"<br\s*/?>", re.I)
TAG_RE = re.compile(r"</?[a-z][^>]*>", re.I)
LINK_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|([^\[\]]*))?\]\]")
BIRTH_RE = re.compile(r"\{\{\s*birth date(?: and age)?\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", re.I)


def _split_top(body):
    """Split a template body on "|" that isn't inside {{...}} or [[...]]."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ("{{", "[["):
            depth += 1
            i += 2
            continue
        if two in ("}}", "]]"):
            depth -= 1
            i += 2
            continue
        if body[i] == "|" and depth == 0:
            parts.append(body[start:i])
            start = i + 1
        i += 1
    parts.append(body[start:])
    return parts


def _template_body(text, start):
    """The text between "{{" at start and its matching "}}", or None."""
    depth, i = 0, start
    while i < len(text):
        two = text[i:i + 2]
        if two == "{{":
            depth += 1
            i += 2
        elif two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return text[start + 2:i - 2]
        else:
            i += 1
    return None


def template_params(text, name):
    """Named parameters of the first {{name ...}} in text, as raw strings; None if absent.

    Matches "{{Name", "{{name" and "{{Template:Name". Positional parameters are
    keyed "1", "2", ...
    """
    text = DROP_ELEMENTS_RE.sub("", COMMENT_RE.sub("", text))
    pat = re.compile(r"\{\{\s*(?:template:)?" + re.escape(name) + r"\s*(?=\||\}\}|\n)", re.I)
    m = pat.search(text)
    if not m:
        return None
    body = _template_body(text, m.start())
    if body is None:
        return None
    params, n = {}, 0
    for part in _split_top(body)[1:]:
        key, eq, value = part.partition("=")
        # "=" inside a link or template belongs to the value, not a key.
        if eq and "{{" not in key and "[[" not in key:
            params[key.strip()] = value.strip()
        else:
            n += 1
            params[str(n)] = part.strip()
    return params


def links(value):
    """Page titles linked from a value, in order: "[[A|B]] and [[C]]" -> ["A", "C"]."""
    return [m.group(1).strip() for m in LINK_RE.finditer(value or "")]


def _drop_templates(text):
    """Replace remaining {{...}} with their single visible argument, or nothing."""
    out, i = [], 0
    while i < len(text):
        if text.startswith("{{", i):
            body = _template_body(text, i)
            if body is None:
                out.append(text[i:])
                break
            parts = _split_top(body)
            name = parts[0].strip().lower()
            # {{nowrap|x}}, {{bb12|Brendon}}: show the one argument. Anything else is dropped.
            if len(parts) == 2 and "=" not in parts[1] and name not in ("otherfandom",):
                out.append(_drop_templates(parts[1]))
            i += len(body) + 4
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def plain(value):
    """A value as display text: links and markup removed, <br> kept as newlines."""
    if not value:
        return ""
    text = COMMENT_RE.sub("", value)
    text = DROP_ELEMENTS_RE.sub("", text)
    text = BR_RE.sub("\n", text)
    text = _drop_templates(text)
    text = LINK_RE.sub(lambda m: (m.group(2) if m.group(2) is not None else m.group(1).split(":")[-1]), text)
    text = TAG_RE.sub("", text)
    text = re.sub(r"'{2,}", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def lines(value):
    """A value split into its display lines: "A<br>B" -> ["A", "B"]."""
    return [x for x in plain(value).split("\n") if x]


def birth_date(value):
    """The date in {{Birth date and age|YYYY|M|D}}, or None."""
    m = BIRTH_RE.search(value or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def bold_lead(text):
    """The first '''bold''' phrase after the infobox: usually the subject's full name."""
    text = DROP_ELEMENTS_RE.sub("", COMMENT_RE.sub("", text))
    # Skip templates at the top (the infobox), whose fields may hold bold text too.
    while text.lstrip().startswith("{{"):
        start = len(text) - len(text.lstrip())
        body = _template_body(text, start)
        if body is None:
            break
        text = text[start + len(body) + 4:]
    m = re.search(r"'''(?!')(.+?)'''", text)
    return plain(m.group(1)) if m else None
