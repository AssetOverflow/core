"""ADR-0194 — labeled-container subject entity shape.

GSM8K routinely labels containers/regions with a trailing single-letter or
short-numeric label: "Jar A has 28 marbles.", "Section G has 15 rows.",
"District 2 has 19 voters.".  The initial-possession parser's entity slot
(``_ENTITY = (?:[A-Z]\\w+|[Tt]he\\s+\\w+)``) captures only "Jar" and then
expects the possession verb, so the label breaks the match and the statement
produces no candidate.

This adds a SEPARATE sibling pattern ``_INITIAL_HAS_LABELED_RE`` (mirroring
ADR-0136.S.4's ``_INITIAL_HAS_INDEF_RE`` localisation) that REQUIRES a label,
so it never duplicates the bare-subject main pattern.  The global ``_ENTITY``
is unchanged.  wrong=0 is held downstream by the completeness guard
(ADR-0191) + round-trip + branch disagreement — the label widening only makes
a statement *parse*; a mis-parse leaves quantities uncovered and refuses.

SUBSTRATE: 0 real-corpus metric flip (the one real multi-container aggregate,
"Jar A has 28 marbles. Jar B has 12 more than jar A. Jar C has twice as many
as jar B. ...altogether?", additionally needs comparative + multiplicative
reading).  Its value is the entity-shape generalisation + that it composes
with the ADR-0193 aggregate question (proven below).
"""
from __future__ import annotations

import pytest

from generate.math_candidate_parser import extract_initial_candidates
from generate.math_candidate_graph import parse_and_solve


# --- Labeled-container subjects now parse as initial possessions -----------
@pytest.mark.parametrize("sentence,entity,value,unit", [
    ("Jar A has 28 marbles.", "Jar A", 28.0, "marbles"),
    ("Box B has 15 marbles.", "Box B", 15.0, "marbles"),
    ("Section G has 10 cars.", "Section G", 10.0, "cars"),
    ("District 2 has 19 voters.", "District 2", 19.0, "voters"),
    ("Tank 1 has 40 liters.", "Tank 1", 40.0, "liters"),
])
def test_labeled_container_parses(sentence, entity, value, unit) -> None:
    cands = extract_initial_candidates(sentence)
    assert len(cands) == 1, f"expected one candidate for {sentence!r}"
    c = cands[0]
    assert c.initial.entity == entity
    assert c.initial.quantity.value == value
    assert c.initial.quantity.unit == unit


# --- No duplicate candidates for bare (unlabeled) subjects -----------------
def test_bare_subject_single_candidate_unchanged() -> None:
    """The labeled pattern requires a label, so 'Jamie has 28 marbles'
    still yields exactly one candidate (from the main pattern only)."""
    cands = extract_initial_candidates("Jamie has 28 marbles.")
    assert len(cands) == 1
    assert cands[0].initial.entity == "Jamie"


# --- The label must not swallow a following content word -------------------
@pytest.mark.parametrize("sentence", [
    "Jar Apple has 5 marbles.",     # 'Apple' is not a single-letter label
    "Box Set has 12 items.",         # 'Set' is not a label
])
def test_multiword_noun_not_a_label(sentence: str) -> None:
    cands = extract_initial_candidates(sentence)
    assert cands == [], f"{sentence!r} must not parse as a labeled container"


# --- Composes with the ADR-0193 aggregate question -------------------------
def test_composes_with_aggregate_question() -> None:
    res = parse_and_solve(
        "Jar A has 28 marbles. Jar B has 12 marbles. "
        "How many marbles are there in total?"
    )
    assert res.answer == 40.0, res.refusal_reason


def test_composes_three_containers() -> None:
    res = parse_and_solve(
        "Jar A has 5 marbles. Jar B has 3 marbles. Jar C has 2 marbles. "
        "How many marbles are there altogether?"
    )
    assert res.answer == 10.0, res.refusal_reason
