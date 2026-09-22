"""What each HOH and veto competition was like: a description and a category.

The category is worked out here, in this order:
  0. the Big Brother Wiki's page for the competition's format, whose opening
     sentence names its type ("a recurring endurance Head of Household
     competition"; see fandom.format_info);
  1. KNOWN_FORMATS / KNOWN_NAMES: recurring formats (the Big Brother Wiki's format pages,
     e.g. "The Wall") whose category is settled;
  2. keywords in the competition's own description, the episode-summary
     sentence that names it ("... the last HouseGuest standing wins");
  3. the most common category among other plays of the same format.
Otherwise the category is None. The description is that sentence (and the
next, when the first is short), verbatim.
"""
import re
from collections import Counter

from .details import SENTENCE_SPLIT

CATEGORIES = ["Endurance", "Physical", "Mental", "Puzzle", "Crapshoot"]
CATEGORY_HELP = {
    "Endurance": "last one standing",
    "Physical": "races, skill and aim",
    "Mental": "trivia, memory, booth and estimate comps",
    "Puzzle": "puzzles and word or picture assembly",
    "Crapshoot": "mostly luck",
}

KNOWN_FORMATS = {
    "The Wall": "Endurance",
    "Pressure Cooker": "Endurance",
    "Take It Off": "Endurance",
    "What Did They Just Do?": "Mental",
    "Who Did What?": "Mental",
    "What Competition Was That?": "Mental",
    "Cover Your Days": "Mental",
    "Before or After": "Mental",
    "Will Kirby": "Mental",
    "What The Bleep?": "Mental",
    "As Close As You Can": "Mental",
    "Kaitlyn's Puzzle": "Puzzle",
    "Fitting In": "Puzzle",
    "Roll It Down": "Physical",
    "Coin Stacking": "Physical",
    "Microbrews": "Physical",
    "Golf Invitational": "Physical",
    "In The Balance": "Physical",
    "Slippery Slope": "Physical",
    "Shootout": "Physical",
    "Yankee Swap": "Crapshoot",
    "To Drink or to Bluff": "Crapshoot",
    "What's The Hold Up": "Endurance",
    "Hide and Seek": "Mental",
    "Zingbot Competition": "Mental",
    "Jury Statements": "Mental",
    "Seesaw": "Physical",
    "Carnival Quick Shot": "Physical",
    "Hourglass": "Physical",
}
# Recurring competitions the wiki gives no format page, by name.
KNOWN_NAMES = {
    "BB Comics": "Mental",
    "What The Bleep?": "Mental",
}

# Checked in this order; the first that matches decides.
KEYWORDS = [
    ("Endurance", re.compile(
        r"\blast (?:person|houseguest|one|player|remaining)s?\b|\bendurance\b|\boutlast|\blongest\b"
        r"|\b(?:hang|hold)(?:ing|s)? on(?:to)?\b|\bfalls? off\b|\bhour and \d+ minute", re.I)),
    ("Puzzle", re.compile(r"\bpuzzles?\b|\bunscrambl|\bassembl(?:e|ing)\b", re.I)),
    ("Mental", re.compile(
        r"\bquestions?\b|\btrue(?: or |/|-)false\b|\btrivia\b|\bquiz|\bmemori[sz]|\bremember|\bmemory\b"
        r"|\bbefore or after\b|\bguess|\bclosest\b|\bestimat|\bmatch(?:ed|ing)? (?:the |different )?"
        r"(?:pictures|houseguests|photos|statements|quotes)|\bday numbers?\b", re.I)),
    ("Physical", re.compile(
        r"\brace\b|\bfastest\b|\bquickest\b|\broll(?:ed|ing|s)?\b|\bballs?\b|\bshoot|\btoss|\bthrow"
        r"|\bstack|\bbalanc|\bslide\b|\bcatch|\bswing|\bzip ?line|\bdig(?:ging)?\b|\btarget|\bclimb"
        r"|\bcatapult|\bputt|\bcarry|\btransfer|\bkick|\bpush|\bjump", re.I)),
    ("Crapshoot", re.compile(r"\bluck\b|\brandom(?:ly)?\b|\bcrapshoot\b|\bcoin flip", re.I)),
]


def _norm(text):
    return re.sub(r"[^\w]+", "", (text or "").casefold())


def sentences(episodes):
    out = []
    for ep in episodes:
        for para in (ep.get("summary") or "").split("\n"):
            out += [x.strip() for x in SENTENCE_SPLIT.split(para) if x.strip()]
    return out


# Words that say how a competition is played ("HouseGuests must ...", "had to ...").
HOW_RE = re.compile(r"\b(must|had to|have to|has to|needed to|need to|were given|were asked|in which|where)\b", re.I)


def describe(name, sents):
    """The summary sentence naming the competition, plus the next when that one
    says how it's played and the first doesn't (or the first is short)."""
    key = _norm(name)
    if len(key) < 3:
        return None
    for i, sent in enumerate(sents):
        if key in _norm(sent):
            text = sent
            nxt = sents[i + 1] if i + 1 < len(sents) else ""
            if nxt and (len(sent.split()) < 25 or (not HOW_RE.search(sent) and HOW_RE.search(nxt))):
                text += " " + nxt
            return text
    return None


def explains(text):
    """True if a description says how the competition is played."""
    return bool(text and HOW_RE.search(text))


def keyword_category(text):
    for cat, pat in KEYWORDS:
        if text and pat.search(text):
            return cat
    return None


def categorize(comps):
    """Set "category" and "category_from" on each comp dict in place.

    comps: HOH and veto comps with "format", "about" (description or None) and
    optionally "wiki_category" (from the format's wiki page). category_from is
    "wiki" (the format's page), "format" (a known format), "summary" (keywords
    in the description) or "other plays" (the format's other plays).
    """
    by_format = {}
    for c in comps:
        c["category"], c["category_from"] = None, None
        known = KNOWN_FORMATS.get(c["format"]) or KNOWN_NAMES.get(c["name"])
        if c.get("wiki_category"):
            c["category"], c["category_from"] = c["wiki_category"], "wiki"
        elif known:
            c["category"], c["category_from"] = known, "format"
        else:
            cat = keyword_category(c["about"])
            if cat:
                c["category"], c["category_from"] = cat, "summary"
        if c["format"] and c["category"]:
            by_format.setdefault(c["format"], Counter())[c["category"]] += 1
    for c in comps:
        if c["category"] is None and c["format"] in by_format:
            c["category"] = by_format[c["format"]].most_common(1)[0][0]
            c["category_from"] = "other plays"
