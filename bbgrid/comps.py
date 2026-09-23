"""What each HOH and veto competition was like: a description and a category.

The category is worked out here, in this order:
  0. the Big Brother Wiki's page for the competition's format, whose opening
     sentence names its type ("a recurring endurance Head of Household
     competition"; see fandom.format_info);
  1. KNOWN_FORMATS / KNOWN_NAMES: recurring formats (the Big Brother Wiki's format pages,
     e.g. "The Wall") whose category is settled, and a few one-off competitions;
  2. keywords in the format page's one-line description ("Roll balls down a
     winding track ...");
  3. keywords in the competition's own description, the episode-summary
     sentence that names it ("... the last HouseGuest standing wins");
  4. the most common category among other plays of the same format.
Otherwise the category is None. The description is that sentence (and the
next, when the first is short), verbatim.
"""
import re
from collections import Counter

from .util import mentions, split_sentences

CATEGORIES = ["Endurance", "Physical", "Skill", "Mental", "Hybrid", "Puzzle", "Crapshoot"]
CATEGORY_HELP = {
    "Endurance": "last one standing",
    "Physical": "races, obstacle courses and strength",
    "Skill": "aim, stacking, balancing and steady hands",
    "Mental": "trivia, memory, booth and estimate comps",
    "Hybrid": "a question or memory test answered by running, climbing or zip-lining",
    "Puzzle": "puzzles and word or picture assembly",
    "Crapshoot": "mostly luck",
}

# Recurring formats (the Big Brother Wiki's format pages) whose category is settled,
# by category. A format and a competition of the same name both match.
_SETTLED = {
    "Endurance": [
        "The Wall", "Pressure Cooker", "What's The Hold Up", "Get A Grip", "Pose In Ivy",
        "Dizzy Discs", "Swing, Slam, Dunk", "Jetpack Attack", "Pyramid", "Rollerball",
    ],
    "Physical": [
        # Speed, running and climbing, or brute force.
        "Take It Off", "Slippery Slope", "Seesaw", "Berry Balanced", "Only One Path",
        "Somewhere Over The Veto", "Relay Race", "Item Catching", "Laser Maze", "The Haunting",
        "Feeling Knotty", "Rollin' in the Dough", "Ready, Set, Woah", "The Maze", "The Black Box",
        "Tumblin' Dice",
    ],
    "Skill": [
        # Aim, stacking and balancing: steady hands more than strength or speed.
        "Coin Stacking", "Stacking", "Microbrews", "Hourglass", "Giddy Up", "In The Balance",
        "Shootout", "Perfect Shot", "As Close As You Can", "Slingshot Aim", "Big Top Drop",
        "Roll It Down", "Carnival Quick Shot", "Golf Invitational", "Bowlerina", "Ball Roll",
        "Time Highway", "Pull Some Strings", "Caged Eggs", "Item Maze",
    ],
    "Mental": [
        "What Did They Just Do?", "Who Did What?", "What Competition Was That?", "Cover Your Days",
        "Before or After", "Will Kirby", "What The Bleep?", "Hide and Seek", "Hide and Go Veto",
        "Zingbot Competition", "Jury Statements", "Knockout", "Getting Loopy", "Snapshot Shuffle",
        "Stay or Fold", "HouseguestsOnly.com", "BB Flix & Chill",
    ],
    # OTEV: each round is a question, but you run, dig and climb for the answer, and
    # the last one back is out. BB Comics: memorize comics from a zip line, then
    # rebuild them on a board; the ride is as hard as the memory.
    "Hybrid": ["OTEV", "BB Comics"],
    "Puzzle": [
        "Kaitlyn's Puzzle", "Fitting In", "Tower of Hanoi", "Gear Puzzle", "Pipeline",
        "Spelling Search", "Blockbusters", "Faster Than A Speeding Veto",
    ],
    "Crapshoot": ["Yankee Swap", "To Drink or to Bluff", "Binary Bridge"],
}
KNOWN_FORMATS = {fmt: cat for cat, fmts in _SETTLED.items() for fmt in fmts}
# Competitions the wiki gives no format page, by name.
KNOWN_NAMES = {
    "Knight Moves": "Mental",
    "Artifact Stack": "Skill",
    "Domino Effect": "Skill",
    "Coin of Destiny (Toss)": "Crapshoot",
}

# Checked in this order; the first that matches decides.
KEYWORDS = [
    ("Endurance", re.compile(
        r"\blast (?:person|houseguest|one|player)s? (?:standing|remaining|left|to (?:hold|fall|drop|let go|keep))"
        r"|\bendurance\b|\boutlast|\bas long as (?:possible|you can)|\blongest time\b"
        r"|\b(?:hang|hold)(?:ing|s)? on(?:to)?\b|\bfalls? off\b|\bhour and \d+ minute", re.I)),
    ("Puzzle", re.compile(r"\bpuzzles?\b|\bunscrambl|\bassembl(?:e|ing)\b|\bspell", re.I)),
    ("Mental", re.compile(
        r"\bquestions?\b|\btrue(?: or |/|-)false\b|\btrivia\b|\bquiz|\bmemori[sz]|\bremember|\bmemory\b"
        r"|\bbefore or after\b|\bchronological|\border (?:they|it) occurred|\bguess|\bclosest\b|\bestimat|\bmatch(?:ed|ing)? (?:the |different )?"
        r"(?:pictures|houseguests|photos|statements|quotes)|\bday numbers?\b", re.I)),
    # Before Physical: "race to stack" is a stacking comp.
    ("Skill", re.compile(
        r"\bstack|\bbalanc(?!e beam)|\bshoot|\btoss|\bthrow|\btarget(?! number)|\bcatapult|\bputt|\baim\b"
        r"|\btweezers\b|\bslingshot|\broll(?:ed|ing|s)? (?:a |the |small |their )?balls?\b", re.I)),
    ("Physical", re.compile(
        r"\brace\b|\bfastest\b|\bquickest\b|\bballs?\b|\bslide\b|\bcatch|\bswing|\bzip ?line"
        r"|\bdig(?:ging)?\b|\bclimb|\bcarry|\btransfer|\bkick|\bpush|\bjump|\bobstacle|\bbalance beam"
        r"|\breps\b|\bexercise|\bherd", re.I)),
    ("Crapshoot", re.compile(r"\bluck\b|\brandom(?:ly)?\b|\bcrapshoot\b|\bcoin (?:flip|toss)", re.I)),
]


def _norm(text):
    return re.sub(r"[^\w]+", "", (text or "").casefold())


def sentences(episodes):
    out = []
    for ep in episodes:
        for para in (ep.get("summary") or "").split("\n"):
            out += split_sentences(para)
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


# 'earned the "Diamond Power of Veto" power', 'the "Adam and Eve" punishment from Big Brother 16'.
PRIZE_RE = re.compile(r'["“]([^"”]{2,50}?)["”]\s+(power|punishment|advantage|curse)\b', re.I)


def twist_prize(winners, sents):
    """The named power or punishment a twist gave its winner, from the summaries.

    Looks in each sentence naming a winner and the sentence after it (which
    often says "his attempt ... earned the "X" power"). Returns
    {"name", "kind"} (kind "power", "punishment", ...) or None.
    """
    for i, sent in enumerate(sents):
        if not any(mentions(sent, w) for w in winners):
            continue
        for text in (sent, sents[i + 1] if i + 1 < len(sents) else ""):
            m = PRIZE_RE.search(text)
            if m:
                return {"name": m.group(1).strip(), "kind": m.group(2).lower()}
    return None


def keyword_category(text):
    for cat, pat in KEYWORDS:
        if text and pat.search(text):
            return cat
    return None


def categorize(comps):
    """Set "category" and "category_from" on each comp dict in place.

    comps: HOH and veto comps with "format", "about" (description or None) and
    optionally "wiki_category" (from the format's wiki page). category_from is
    "wiki" (the format page's type word or description), "format" (a known
    format), "summary" (keywords in the episode summary) or "other plays"
    (the format's other plays).
    """
    by_format = {}
    for c in comps:
        c["category"], c["category_from"] = None, None
        known = (KNOWN_FORMATS.get(c["format"]) or KNOWN_NAMES.get(c["name"])
                 or KNOWN_FORMATS.get(c["name"]))
        if c.get("wiki_category"):
            c["category"], c["category_from"] = c["wiki_category"], "wiki"
        elif known:
            c["category"], c["category_from"] = known, "format"
        elif keyword_category(c.get("format_description")):
            c["category"], c["category_from"] = keyword_category(c["format_description"]), "wiki"
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
