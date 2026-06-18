"""Gate A2b — fraction_portion + keep-on-hand question composition."""

from __future__ import annotations

from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import extract_operation_candidates
from generate.math_problem_graph import FractionPortion, Operation, PartitionChunk
from generate.math_roundtrip import roundtrip_admissible
from generate.math_solver import _apply_fraction_portion, _apply_unit_partition


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def test_fraction_give_extracts_and_roundtrips():
    stmt = "She gives 1/4 of that to a friend."
    cands = extract_operation_candidates(stmt)
    assert len(cands) == 1
    cand = cands[0]
    assert cand.op.kind == "fraction_portion"
    assert isinstance(cand.op.operand, FractionPortion)
    assert cand.op.operand.numerator == 1
    assert cand.op.operand.denominator == 4
    assert roundtrip_admissible(cand)


def test_half_rest_extracts_and_roundtrips():
    stmt = "She then puts half of the rest in storage."
    cands = extract_operation_candidates(stmt)
    assert len(cands) == 1
    cand = cands[0]
    assert cand.op.kind == "fraction_portion"
    assert cand.op.operand.numerator == 1
    assert cand.op.operand.denominator == 2
    assert cand.op.operand.referent == "rest"
    assert roundtrip_admissible(cand)


def test_fraction_give_without_of_that_does_not_extract():
    stmt = "She gives 1/4 to a friend."
    assert extract_operation_candidates(stmt) == []


def test_fraction_portion_solver_chain():
    pack_bindings = {"unit_partition": "en_arithmetic_v1:divide", "fraction_portion": "en_arithmetic_v1:subtract"}
    state = {("Jan", "feet"): 1000.0}
    last_count_unit: dict[str, str] = {}

    _apply_unit_partition(
        Operation(
            actor="Jan",
            kind="unit_partition",
            operand=PartitionChunk(value=25.0, unit="feet", result_unit="sections"),
        ),
        index=0,
        state=state,
        pack_bindings=pack_bindings,
        last_count_unit=last_count_unit,
    )
    assert state[("Jan", "sections")] == 40.0

    _apply_fraction_portion(
        Operation(
            actor="Jan",
            kind="fraction_portion",
            operand=FractionPortion(1, 4, "that"),
        ),
        index=1,
        state=state,
        pack_bindings=pack_bindings,
        last_count_unit=last_count_unit,
    )
    assert state[("Jan", "sections")] == 30.0

    _apply_fraction_portion(
        Operation(
            actor="Jan",
            kind="fraction_portion",
            operand=FractionPortion(1, 2, "rest"),
        ),
        index=2,
        state=state,
        pack_bindings=pack_bindings,
        last_count_unit=last_count_unit,
    )
    assert state[("Jan", "sections")] == 15.0


def test_train_sample_0002_end_to_end():
    text = (
        "Jan buys 1000 feet of cable. "
        "She splits it up into 25-foot sections. "
        "She gives 1/4 of that to a friend. "
        "She then puts half of the rest in storage. "
        "How much does she keep on hand?"
    )
    res = _run(text)
    assert res.answer == 15.0
    assert res.refusal_reason is None


def test_confuser_v1_0007_still_refuses():
    text = (
        "Jan buys 1000 feet of cable. "
        "She splits it into 25-foot sections. "
        "She gives 1/4 to a friend. "
        "She puts half of the rest in storage. "
        "How much does she keep on hand?"
    )
    res = _run(text)
    assert res.answer is None
    assert res.refusal_reason is not None


def test_sibling_bob_rope_one_third_half_rest():
    """Different actor, total, chunk size, unit, and fraction (1/3)."""
    text = (
        "Bob buys 900 feet of rope. "
        "He splits it into 30-foot sections. "
        "He gives 1/3 of that to a friend. "
        "He then puts half of the rest in storage. "
        "How much does he keep on hand?"
    )
    res = _run(text)
    assert res.answer == 10.0
    assert res.refusal_reason is None


def test_sibling_alice_ribbon_one_fifth_half_rest():
    """Female actor, inches/pieces, 1/5 fraction — not the 0002 surface."""
    text = (
        "Alice buys 480 inches of ribbon. "
        "She splits it into 12-inch pieces. "
        "She gives 1/5 of that to a friend. "
        "She then puts half of the rest in storage. "
        "How much does she keep on hand?"
    )
    res = _run(text)
    assert res.answer == 16.0
    assert res.refusal_reason is None


def test_refuses_slash_fraction_without_grounded_referent():
    assert extract_operation_candidates("She gives 1/4 to a friend.") == []


def test_refuses_that_fraction_without_partition_chain():
    text = (
        "Jan buys 100 feet of cable. "
        "She gives 1/4 of that to a friend. "
        "How much does she keep on hand?"
    )
    res = _run(text)
    assert res.answer is None
    assert res.refusal_reason is not None


def test_refuses_multi_actor_pronoun_on_fraction_chain():
    text = (
        "Jan buys 1000 feet of cable. "
        "Bob buys 200 feet of rope. "
        "She splits it up into 25-foot sections. "
        "She gives 1/4 of that to a friend. "
        "She then puts half of the rest in storage. "
        "How much does she keep on hand?"
    )
    res = _run(text)
    assert res.answer is None
    assert res.refusal_reason is not None
