"""ADR-0115 Phase 1.1 — math problem graph schema invariants.

Pins:

1. The five seed cases in ``evals/gsm8k_parser_dev/cases.jsonl`` round-trip
   through ``graph_from_dict`` → ``as_json`` without changing bytes.

2. ``MathProblemGraph.canonical_bytes()`` is deterministic: same logical
   graph constructed twice produces identical bytes.

3. Construction-time validation refuses malformed graphs.

4. Pyhand-solving each seed case from its ground-truth graph reproduces the
   ``expected_answer`` — this catches mis-authored ground-truth graphs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_problem_graph import (
    InitialPossession,
    MathGraphError,
    MathProblemGraph,
    Operation,
    Quantity,
    Unknown,
    graph_from_dict,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_CASES = _REPO_ROOT / "evals" / "gsm8k_parser_dev" / "cases.jsonl"


def _load_cases() -> list[dict]:
    return [json.loads(line) for line in _CASES.read_text().splitlines() if line.strip()]


class TestSeedCasesRoundTrip:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_graph_loads(self, case: dict) -> None:
        graph = graph_from_dict(case["ground_truth_graph"])
        assert isinstance(graph, MathProblemGraph)

    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_round_trip_byte_equal(self, case: dict) -> None:
        graph = graph_from_dict(case["ground_truth_graph"])
        reloaded = graph_from_dict(graph.as_json())
        assert graph.canonical_bytes() == reloaded.canonical_bytes()


class TestCanonicalBytesDeterminism:
    def test_two_identical_graphs_produce_identical_bytes(self) -> None:
        g1 = MathProblemGraph(
            entities=("Sam",),
            initial_state=(
                InitialPossession("Sam", Quantity(5, "apples")),
            ),
            operations=(Operation("Sam", "add", Quantity(3, "apples")),),
            unknown=Unknown("Sam", "apples"),
        )
        g2 = MathProblemGraph(
            entities=("Sam",),
            initial_state=(
                InitialPossession("Sam", Quantity(5, "apples")),
            ),
            operations=(Operation("Sam", "add", Quantity(3, "apples")),),
            unknown=Unknown("Sam", "apples"),
        )
        assert g1.canonical_bytes() == g2.canonical_bytes()
        assert g1 == g2


class TestSchemaRejectsMalformed:
    def test_quantity_rejects_string_value(self) -> None:
        with pytest.raises(MathGraphError):
            Quantity("5", "apples")  # type: ignore[arg-type]

    def test_quantity_rejects_empty_unit(self) -> None:
        with pytest.raises(MathGraphError):
            Quantity(5, "")

    def test_operation_rejects_unknown_kind(self) -> None:
        with pytest.raises(MathGraphError):
            Operation("Sam", "explode", Quantity(3, "apples"))

    def test_transfer_requires_target(self) -> None:
        with pytest.raises(MathGraphError):
            Operation("Sam", "transfer", Quantity(3, "apples"))

    def test_non_transfer_rejects_target(self) -> None:
        with pytest.raises(MathGraphError):
            Operation("Sam", "add", Quantity(3, "apples"), target="Tom")

    def test_transfer_self_rejected(self) -> None:
        with pytest.raises(MathGraphError):
            Operation("Sam", "transfer", Quantity(3, "apples"), target="Sam")

    def test_graph_rejects_duplicate_entities(self) -> None:
        with pytest.raises(MathGraphError):
            MathProblemGraph(
                entities=("Sam", "Sam"),
                initial_state=(),
                operations=(),
                unknown=Unknown("Sam", "apples"),
            )

    def test_graph_rejects_unknown_entity_in_initial(self) -> None:
        with pytest.raises(MathGraphError):
            MathProblemGraph(
                entities=("Sam",),
                initial_state=(InitialPossession("Tom", Quantity(5, "apples")),),
                operations=(),
                unknown=Unknown("Sam", "apples"),
            )

    def test_graph_rejects_unknown_entity_in_question(self) -> None:
        with pytest.raises(MathGraphError):
            MathProblemGraph(
                entities=("Sam",),
                initial_state=(),
                operations=(),
                unknown=Unknown("Tom", "apples"),
            )


def _hand_solve(graph: MathProblemGraph) -> tuple[float, str]:
    """Reference solver — ADR-0116 supersedes this with a real solver.

    Used here only to falsify mis-authored ground-truth graphs in the seed
    set. Sufficient for the patterns Phase 1.1 covers.
    """
    state: dict[tuple[str, str], float] = {}
    for p in graph.initial_state:
        state[(p.entity, p.quantity.unit)] = float(p.quantity.value)
    for op in graph.operations:
        key = (op.actor, op.operand.unit)
        cur = state.get(key, 0.0)
        v = float(op.operand.value)
        if op.kind == "add":
            state[key] = cur + v
        elif op.kind == "subtract":
            state[key] = cur - v
        elif op.kind == "transfer":
            assert op.target is not None
            state[key] = cur - v
            tgt_key = (op.target, op.operand.unit)
            state[tgt_key] = state.get(tgt_key, 0.0) + v
        elif op.kind == "multiply":
            state[key] = cur * v
        elif op.kind == "divide":
            state[key] = cur / v
    if graph.unknown.entity is None:
        total = sum(
            v for (_, unit), v in state.items() if unit == graph.unknown.unit
        )
        return total, graph.unknown.unit
    return state[(graph.unknown.entity, graph.unknown.unit)], graph.unknown.unit


class TestGroundTruthGraphsAgreeWithExpectedAnswers:
    """Falsifies mis-authored seed cases.

    For each seed case, hand-solving the ground-truth graph using the
    documented operation semantics must reproduce ``expected_answer`` and
    ``expected_unit``.
    """

    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_hand_solve_matches_expected(self, case: dict) -> None:
        graph = graph_from_dict(case["ground_truth_graph"])
        computed, unit = _hand_solve(graph)
        assert unit == case["expected_unit"], (
            f"{case['id']}: unit mismatch — graph says {unit!r}, "
            f"expected {case['expected_unit']!r}"
        )
        # Accept int/float equivalence; problems are integer-valued.
        assert computed == case["expected_answer"], (
            f"{case['id']}: hand-solve produced {computed} but case "
            f"declared expected_answer={case['expected_answer']}"
        )


class TestCaseIdsAreSequential:
    def test_ids_are_gpd_zero_padded_sequential(self) -> None:
        cases = _load_cases()
        for i, c in enumerate(cases, start=1):
            assert c["id"] == f"gpd-{i:03d}", (
                f"case {i}: expected id 'gpd-{i:03d}', got {c['id']!r}"
            )
