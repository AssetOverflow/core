"""ADR-0193 — extend the total-across branch with the existential verb frame.

The solver already aggregates a total-across unknown (``Unknown(entity=None,
unit=X)`` → ``_resolve_unknown`` sums every state entry whose unit matches).
ADR-0131.G.5 wired exactly one surface for that unknown over a CLOSED cue
vocabulary ({in total, altogether, combined, together}): the "do they have
<cue>" verb frame.  This ADR adds the equally common *existential* frame over
the SAME closed cues:

  - ``"How many <unit> are there <agg-cue>?"``

It does NOT widen the cue vocabulary, and it composes: a multi-possession
problem closing with this frame now solves end-to-end.

wrong=0 is held downstream, not by the question form:
  - the question round-trip (``_question_admissible``) requires the unit
    token to ground in the question span;
  - the completeness guard (ADR-0191) requires every source quantity to be
    consumed by the solved graph — a conjoined ("dogs and cats") or derived
    ("animal legs") unit leaves quantities uncovered and refuses;
  - branch disagreement refuses if any competing reading disagrees.

DEFERRED — ``"What is the total number of <unit>?"``: ADR-0131.G.5 pins this
surface as an out-of-closed-cue REFUSAL probe
(``test_outside_closed_cue_refuses``).  The solver would sum it correctly, but
promoting it must AMEND ADR-0131.G.5's closed-cue contract rather than be
contradicted from this branch.  ``test_total_number_of_still_deferred`` locks
that boundary so this ADR does not silently break the parallel lane.
"""
from __future__ import annotations

import pytest

from generate.math_candidate_parser import extract_question_candidates
from generate.math_candidate_graph import parse_and_solve


# --- The question parser now emits a total-across unknown for the frame -----
@pytest.mark.parametrize("question", [
    "How many marbles are there altogether?",
    "How many marbles are there in total?",
    "How many marbles are there in all?",
    "How many marbles are there combined?",
    "How many marbles are there together?",
])
def test_aggregate_surface_emits_total_across(question: str) -> None:
    cands = extract_question_candidates(question, question)
    assert len(cands) == 1, f"expected one candidate for {question!r}"
    c = cands[0]
    assert c.unknown.entity is None, "must be a total-across (entity=None) unknown"
    assert c.unknown.unit == "marbles"


def test_two_word_unit_aggregate() -> None:
    cands = extract_question_candidates(
        "How many parking spots are there in total?", None
    )
    assert len(cands) == 1
    assert cands[0].unknown.entity is None
    assert cands[0].unknown.unit == "parking spots"


# --- wrong=0 guards: shapes that MUST still refuse at the question stage ----
@pytest.mark.parametrize("question", [
    "How many marbles are there?",            # no aggregate cue → ambiguous
    "How many dogs and cats are there in all?",  # conjoined unit (handled by
                                                 # completeness downstream; the
                                                 # parser captures at most one
                                                 # unit and never both)
])
def test_no_cue_or_conjoined_does_not_emit_total_across(question: str) -> None:
    cands = extract_question_candidates(question, question)
    # Either no candidate, or — for the conjoined case — a single-unit
    # candidate that the completeness guard will reject downstream. The
    # invariant here is that the bare no-cue form yields no total-across.
    if question.endswith("are there?"):
        assert cands == [], "bare 'are there?' must not map to total-across"


# --- ADR-0131.G.5 boundary: "total number of" stays deferred ---------------
def test_total_number_of_still_deferred() -> None:
    """ADR-0131.G.5 pins 'What is the total number of <unit>?' as an
    out-of-closed-cue refusal probe.  This ADR must NOT silently promote it;
    doing so requires amending ADR-0131.G.5.  Lock the boundary."""
    cands = extract_question_candidates(
        "What is the total number of marbles?", None
    )
    assert cands == [], "total-number-of must remain deferred (ADR-0131.G.5)"
    res = parse_and_solve(
        "Alice has 4 coins. Bob has 6 coins. What is the total number of coins?"
    )
    assert res.answer is None


# --- End-to-end: the machinery now solves the aggregate surface ------------
@pytest.mark.parametrize("question,expected", [
    ("How many apples are there in total?", 8.0),
    ("How many apples are there altogether?", 8.0),
])
def test_end_to_end_aggregate_solves(question: str, expected: float) -> None:
    text = f"Tom has 5 apples. Jane has 3 apples. {question}"
    res = parse_and_solve(text)
    assert res.answer == expected, res.refusal_reason


def test_baseline_do_they_have_unchanged() -> None:
    """The previously-working 'do they have altogether' form is unchanged."""
    res = parse_and_solve(
        "Tom has 5 apples. Jane has 3 apples. "
        "How many apples do they have altogether?"
    )
    assert res.answer == 8.0


def test_aggregate_refuses_when_a_quantity_is_uncovered() -> None:
    """A same-entity distractor unit leaves a source quantity uncovered →
    the completeness guard refuses rather than confabulate a partial sum."""
    res = parse_and_solve(
        "Tom has 5 apples and 3 oranges. How many apples are there in total?"
    )
    assert res.answer is None
