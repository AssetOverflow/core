"""ADR-0190 — fractional partition operation.

Failing-under-violation guards for the partition operation that flipped
gsm8k train_sample 0046 (serving 4/46/0 → 5/45/0, wrong=0). Each test
fails if exactly one of the partition guards is silently weakened.
"""

from __future__ import annotations

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import (
    _partition_candidates,
    split_partition_clauses,
)
from generate.math_problem_graph import (
    InitialPossession,
    MathProblemGraph,
    Operation,
    Partition,
    Quantity,
    Unknown,
)
from generate.math_roundtrip import roundtrip_admissible
from generate.math_solver import SolveError, solve


# ---------------------------------------------------------------------------
# End-to-end: the case that motivated the operation.
# ---------------------------------------------------------------------------


def test_0046_solves_via_partition_chain() -> None:
    r = parse_and_solve(
        "A school has 100 students. "
        "Half of the students are girls, the other half are boys.  "
        "20% of the girls have dogs at home and 10% of the boys have dogs at home.  "
        "How many students own dogs?"
    )
    assert r.answer == 15.0
    assert r.refusal_reason is None


# ---------------------------------------------------------------------------
# Solver guards — each refuses (→ no answer), never a wrong number.
# ---------------------------------------------------------------------------


def _graph(ops, unknown, *, entities, initial):
    return MathProblemGraph(
        entities=entities, initial_state=initial, operations=ops, unknown=unknown
    )


def test_partition_unit_change_scales_base() -> None:
    g = _graph(
        (Operation(actor="girls", kind="partition",
                   operand=Partition(base_unit="students", subset_unit="girls", factor=0.5)),),
        Unknown(entity="girls", unit="girls"),
        entities=("school", "girls"),
        initial=(InitialPossession("school", Quantity(100, "students")),),
    )
    assert solve(g).answer_value == 50.0


def test_partition_no_base_refuses() -> None:
    g = _graph(
        (Operation(actor="girls", kind="partition",
                   operand=Partition(base_unit="students", subset_unit="girls", factor=0.5)),),
        Unknown(entity="girls", unit="girls"),
        entities=("school", "girls"),
        initial=(InitialPossession("school", Quantity(100, "apples")),),  # no 'students'
    )
    with pytest.raises(SolveError):
        solve(g)


def test_partition_ambiguous_base_refuses() -> None:
    # Two entities hold the base unit → refuse rather than guess.
    g = _graph(
        (Operation(actor="girls", kind="partition",
                   operand=Partition(base_unit="students", subset_unit="girls", factor=0.5)),),
        Unknown(entity="girls", unit="girls"),
        entities=("school_a", "school_b", "girls"),
        initial=(
            InitialPossession("school_a", Quantity(100, "students")),
            InitialPossession("school_b", Quantity(80, "students")),
        ),
    )
    with pytest.raises(SolveError):
        solve(g)


def test_partition_factor_must_be_positive() -> None:
    with pytest.raises(Exception):
        Partition(base_unit="students", subset_unit="girls", factor=0.0)


# ---------------------------------------------------------------------------
# Round-trip guards — factor + both population units must ground.
# ---------------------------------------------------------------------------


def test_word_percent_slash_factors_admit() -> None:
    for s in [
        "Half of the students are girls",
        "20% of the girls have dogs",
        "3/4 of the boys have phones",
    ]:
        cands = _partition_candidates(s)
        assert cands, s
        assert all(roundtrip_admissible(c) for c in cands), s


def test_partition_refuses_when_subset_unit_ungrounded() -> None:
    # A partition whose subset unit does not appear in the source must NOT
    # pass the round-trip filter (the wrong=0 firewall).
    op = Operation(actor="girls", kind="partition",
                   operand=Partition(base_unit="students", subset_unit="aliens", factor=0.5))
    from generate.math_roundtrip import CandidateOperation
    c = CandidateOperation(
        op=op, source_span="Half of the students are girls",
        matched_verb="half", matched_value_token="half",
        matched_unit_token="aliens", matched_actor_token="girls",
    )
    assert roundtrip_admissible(c) is False


def test_same_unit_partition_refuses() -> None:
    # "half of the X are X" is a misparse, not a partition.
    assert _partition_candidates("Half of the apples are apples") == []


# ---------------------------------------------------------------------------
# Clause-split — only fires when every clause is partition-shaped.
# ---------------------------------------------------------------------------


def test_clause_split_only_on_partition_conjunctions() -> None:
    # Partition conjunction splits into per-clause slots…
    parts = split_partition_clauses(
        "20% of the girls have dogs and 10% of the boys have dogs"
    )
    assert len(parts) == 2
    # …an ordinary conjunction does NOT.
    assert split_partition_clauses("Sam has 5 apples and 3 oranges") == [
        "Sam has 5 apples and 3 oranges"
    ]


def test_other_half_clause_inherits_base() -> None:
    parts = split_partition_clauses(
        "Half of the students are girls, the other half are boys"
    )
    assert any("students" in p and "boys" in p for p in parts), parts
