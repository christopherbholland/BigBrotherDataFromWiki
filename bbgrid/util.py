"""Small helpers shared by several steps. Nothing here knows about wikis or Big Brother."""
import re
from datetime import datetime, timezone

DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y")  # "July 17, 2024", "Jul 17, 2024"


def name_key(name):
    """A name for comparing within one wiki's table: case and spacing ignored."""
    return " ".join(name.split()).casefold()


def mentions(text, name):
    """True if name appears in text as a whole word (or words)."""
    return re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text) is not None


def parse_date(text):
    """A date written out in words ("July 17, 2024"), or None."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            pass
    return None


def utc_now():
    """The current time as an ISO 8601 string, to the second: the timestamps in cache/ and web/."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
