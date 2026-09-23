"""Step 4a: per-round consistency checks. Failures downgrade the week to `error`."""
from .util import name_key


def check_round(rnd):
    """Return a list of failed-check messages for one round."""
    failures = []
    evicted = rnd.get("evicted")
    # A round still airing (HOH but no eviction yet) is checked as far as it goes.
    required = ("hoh", "nominees_final", "evicted") if evicted else ("hoh",)
    for field in required:
        if not rnd.get(field):
            failures.append(f"missing {field}")
    finals = {name_key(n) for n in rnd.get("nominees_final") or []}
    if evicted and finals and name_key(evicted) not in finals:
        failures.append(f"evicted {evicted!r} not in final nominees {rnd['nominees_final']}")

    tally = rnd.get("tally")
    if evicted and tally and tally["type"] == "vote":
        # A vote is a vote-row cell holding exactly one final nominee's name.
        votes = [name_key(c[0]) for c in rnd.get("_vote_cells", []) if len(c) == 1 and name_key(c[0]) in finals]
        to_evict = votes.count(name_key(evicted))
        if to_evict != tally["votes_to_evict"]:
            failures.append(f"vote rows show {to_evict} votes to evict {evicted}, tally says {tally['votes_to_evict']}")
        if len(votes) != tally["votes_cast"]:
            failures.append(f"vote rows show {len(votes)} votes cast, tally says {tally['votes_cast']}")
    return failures


def validate_week(record):
    """Run checks on every modeled round; mutate the record's status/note on failure."""
    failures = []
    multi = len(record["rounds"]) > 1
    for i, rnd in enumerate(record["rounds"], 1):
        for msg in check_round(rnd):
            failures.append(f"Round {i}: {msg}" if multi else msg)
    if failures:
        record["status"] = "error"
        record["note"] = "; ".join(filter(None, [record["note"], "Validation failed: " + "; ".join(failures)]))
    return failures
