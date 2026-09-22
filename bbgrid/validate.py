"""Step 4a: per-round consistency checks. Failures downgrade the week to `error`."""


def _key(name):
    return " ".join(name.split()).casefold()


def check_round(rnd):
    """Return a list of failed-check messages for one round."""
    failures = []
    for field in ("hoh", "nominees_final", "evicted"):
        if not rnd.get(field):
            failures.append(f"missing {field}")
    evicted = rnd.get("evicted")
    finals = {_key(n) for n in rnd.get("nominees_final") or []}
    if evicted and finals and _key(evicted) not in finals:
        failures.append(f"evicted {evicted!r} not in final nominees {rnd['nominees_final']}")

    tally = rnd.get("tally")
    if evicted and tally and tally["type"] == "vote":
        # A vote is a vote-row cell holding exactly one final nominee's name.
        votes = [_key(c[0]) for c in rnd.get("_vote_cells", []) if len(c) == 1 and _key(c[0]) in finals]
        to_evict = votes.count(_key(evicted))
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
