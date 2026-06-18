"""Candidate-graph integration for Gate A2a unit_partition injection."""

from __future__ import annotations

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.math_problem_graph import Operation, PartitionChunk
from generate.math_solver import SolveError, _apply_unit_partition
from generate.recognizer_anchor_inject import inject_from_match
from generate.recognizer_match import match
from generate.recognizer_registry import load_ratified_registry


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def test_unit_partition_solver_lower_level_integration():
    """Prove unit_partition apply writes chunk count under result_unit."""
    chunk = PartitionChunk(value=25.0, unit="feet", result_unit="sections")
    op = Operation(actor="Jan", kind="unit_partition", operand=chunk)
    state = {("Jan", "feet"): 1000.0}
    pack_bindings = {"unit_partition": "en_arithmetic_v1:divide"}

    step = _apply_unit_partition(op, index=0, state=state, pack_bindings=pack_bindings)

    assert step.operation_kind == "unit_partition"
    assert state[("Jan", "sections")] == 40.0
    assert state[("Jan", "feet")] == 1000.0


def test_partition_stmt_injects_on_lead_exemplar_pair():
    registry = load_ratified_registry()
    stmt = "She splits it up into 25-foot sections."
    m = match(stmt, registry)
    assert m is not None
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1
    assert emitted[0].op.kind == "unit_partition"


def test_stmt_only_partition_refuses_end_to_end():
    res = _run("She splits it into 25-foot sections.")
    assert res.answer is None
    assert res.refusal_reason is not None


def test_pronoun_partition_refuses_without_antecedent():
    res = _run("She splits it into 25-foot sections. How many sections does she have?")
    assert res.answer is None
    assert res.refusal_reason is not None


def test_pronoun_partition_refuses_multi_actor_ambiguity():
    text = (
        "Jan buys 1000 feet of cable. "
        "Bob buys 200 feet of rope. "
        "She splits it into 25-foot sections. "
        "How many sections does Jan have?"
    )
    res = _run(text)
    assert res.answer is None
    assert res.refusal_reason is not None


def test_non_exact_quotient_refuses_at_solver():
    chunk = PartitionChunk(value=30.0, unit="feet", result_unit="sections")
    op = Operation(actor="Jan", kind="unit_partition", operand=chunk)
    state = {("Jan", "feet"): 1000.0}
    pack_bindings = {"unit_partition": "en_arithmetic_v1:divide"}

    with pytest.raises(SolveError):
        _apply_unit_partition(op, index=0, state=state, pack_bindings=pack_bindings)


def test_unit_mismatch_surface_does_not_solve():
    text = "Jan buys 1000 feet of cable. Jan cuts 1000 feet into 25-inch sections."
    res = _run(text)
    assert res.answer is None


def test_full_0002_still_refuses_without_composition():
    text = (
        "Jan buys 1000 feet of cable. "
        "She splits it up into 25-foot sections. "
        "She gives 1/4 of that to a friend. "
        "She then puts half of the rest in storage. "
        "How much does she keep on hand?"
    )
    res = _run(text)
    assert res.answer is None
    assert res.refusal_reason is not None


def test_duration_confuser_does_not_inject_unit_partition():
    res = _run("It is a 2-hour drive.")
    assert res.answer is None


def test_injected_unit_partition_does_not_create_wrong_on_isolated_rate():
    for stmt in [
        "Tina makes $18.00 an hour.",
        "Alexa has a lemonade stand where she sells lemonade for $2 for one cup.",
    ]:
        res = parse_and_solve(stmt, sealed=False)
        assert res.answer is None
        assert res.refusal_reason is not None
