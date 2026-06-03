"""Completeness guard for the candidate-graph reader (wrong==0 firewall).

The microscope over the full real GSM8K train split (7,473 questions)
found 5 confabulations the 47-case ``train_sample`` could not see: the
reader emitted a *partial* reading (the first grounded quantity) instead
of refusing, because admissibility checked grounding + round-trip but had
no COMPLETENESS leg.

This guard adds the missing leg, mirroring the derivation reader's
``verify.py`` (grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness):

    Every numeric / multiplier quantity present in the source (all
    statement sentences + the question) must be consumed by the chosen
    reading.  An uncovered source quantity => refuse.

The guard is REFUSAL-ONLY: it can never turn a refusal into an answer,
so it cannot create a wrong answer — it can only remove confabulations.
Its entire regression surface is the graph-path correct set, which on
train_sample is exactly {0024} and on real-train is {3343} (the same
Sidney/Brooke shape).  Both MUST still solve.
"""
from __future__ import annotations

import pytest

from generate.math_candidate_graph import parse_and_solve

# The 5 real-GSM8K confabulations (exact corpus strings).  Each MUST now
# refuse (answer is None) instead of emitting a partial reading.
CONFABULATIONS = {
    553: (
        "Emma buys 2 containers of milk every school day for lunch. She does "
        "not go to school on the weekends. How many containers of milk does "
        "she buy in 3 weeks?"
    ),
    605: (
        "Ivan has 20 dice. Jerry has twice as many dice as Ivan. How many "
        "dice do they have altogether?"
    ),
    693: (
        "Ian had twenty roses. He gave six roses to his mother,  nine roses "
        "to his grandmother, four roses to his sister, and he kept the rest. "
        "How many roses did Ian keep?"
    ),
    6172: (
        "Jimmy has 18 cards. Jimmy gives three cards to Bob. If Jimmy gives "
        "Mary twice as many cards as he gave to Bob, how many cards does "
        "Jimmy have left?"
    ),
    7369: (
        "Wilfred eats 4 carrots on Tuesday and 6 carrots on Wednesday. If "
        "Wilfred wants to eat a total of 15 carrots from Tuesday to Thursday, "
        "how many carrots does Wilfred need to eat on Thursday?"
    ),
}

# The graph-path correct case the guard MUST NOT break (train_sample 0024
# == real-train 3343).
SIDNEY_BROOKE = (
    "Sidney does 20 jumping jacks on Monday, 36 on Tuesday, 40 on Wednesday, "
    "and 50 on Thursday. Brooke does three times as many jumping jacks as "
    "Sidney. How many jumping jacks did Brooke do?"
)


@pytest.mark.parametrize("idx", sorted(CONFABULATIONS))
def test_confabulation_now_refuses(idx: int) -> None:
    """Each previously-confabulated case must refuse (wrong==0 restored)."""
    res = parse_and_solve(CONFABULATIONS[idx])
    assert res.answer is None, (
        f"[{idx}] expected refusal, got answer={res.answer!r} "
        f"(refusal_reason={res.refusal_reason!r})"
    )


def test_sidney_brooke_still_solves() -> None:
    """The day-enum + comparative graph case must still solve to 438."""
    res = parse_and_solve(SIDNEY_BROOKE)
    assert res.answer == 438.0, (
        f"completeness guard over-refused the correct graph-path case: "
        f"answer={res.answer!r} refusal_reason={res.refusal_reason!r}"
    )


def test_guard_is_refusal_only_not_answer_changing() -> None:
    """A case that already solves correctly keeps its exact answer; the
    guard never rewrites an answer value (refusal-only invariant)."""
    res = parse_and_solve(SIDNEY_BROOKE)
    # Same value, same unit-bearing graph — guard does not mutate solving.
    assert res.answer == 438.0
    assert res.selected_graph is not None


@pytest.mark.parametrize(
    ("factor", "comparative"),
    [
        ("2", "as many"),
        ("3", "as many"),
        ("5", "as many"),
        ("two", "as many"),
        ("three", "as many"),
        ("five", "as many"),
        ("3", "more"),
        ("three", "more"),
        ("3", "the number of"),
        ("3", "the"),
    ],
)
def test_n_times_without_reference_refuses(
    factor: str, comparative: str
) -> None:
    """A dropped comparative multiplier must not admit as an initial
    possession of ``<N> times``.

    This is the Phase-5b hard negative: if future emission work makes
    comparative-multiplicative surfaces reach the graph, the gate must
    refuse incomplete ``<N> times ...`` clauses instead of consuming
    the scalar as an ordinary count.
    """
    res = parse_and_solve(
        "Tom has 7 apples. "
        f"Jerry has {factor} times {comparative} apples. "
        "How many apples do they have together?"
    )
    assert res.answer is None


def test_n_times_as_many_with_reference_still_solves() -> None:
    """The guard only blocks incomplete comparative clauses; a fully
    referenced compare_multiplicative graph still solves."""
    res = parse_and_solve(
        "Tom has 7 apples. Jerry has 3 times as many apples as Tom. "
        "How many apples do they have together?"
    )
    assert res.answer == 28.0


@pytest.mark.parametrize(
    "question",
    [
        "Tom has 7 apples. Jerry has twice as many apples. "
        "How many apples do they have together?",
        "Tom has 7 apples. Jerry has double the apples. "
        "How many apples do they have together?",
        "Ivan has 20 dice. Jerry has twice as many dice as Ivan. "
        "How many dice do they have altogether?",
    ],
)
def test_existing_multiplier_refusals_stay_refused(question: str) -> None:
    """Existing safe multiplier refusals must not become admissions."""
    res = parse_and_solve(question)
    assert res.answer is None
