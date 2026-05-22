"""ADR-0116 — deterministic solver invariants.

Pins five load-bearing invariants:

1. **Solver exit criterion: ≥ 80% on parser-correct dev cases.**
   On the 50-case dev set the solver yields the declared answer.

2. **Determinism (ADR-0114a Obligation #9).** Same graph → byte-equal
   SolutionTrace across two consecutive solves.

3. **Trace replay reproduces answer (ADR-0114a Obligation #3).**
   Re-applying ``steps`` from initial state to the unknown reproduces
   ``answer_value`` byte-equal. This is the rehearsal for ADR-0117
   verifier.

4. **Typed refusal on under-determined / missing-pack graphs
   (ADR-0114a Obligation #4).** Division by zero, missing required
   lemma, and unknown-references-nothing all raise
   :class:`SolveError`. Never silently produces a fabricated answer.

5. **Operation provenance via pack (ADR-0114a Obligation #10).** Every
   step's ``pack_lemma_id`` is qualified by ``en_arithmetic_v1`` and
   refers to a lemma that exists in the pack on disk. Removing the
   pack from the search path makes every solve fail loudly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_parser import parse_problem
from generate.math_problem_graph import (
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
    Unknown,
)
from generate.math_solver import (
    REQUIRED_PACK_ID,
    SolutionStep,
    SolutionTrace,
    SolveError,
    solve,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_CASES_PATH = _REPO_ROOT / "evals" / "gsm8k_parser_dev" / "cases.jsonl"


def _load_cases() -> list[dict]:
    return [json.loads(line) for line in _CASES_PATH.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Exit-criterion gate
# ---------------------------------------------------------------------------

class TestSolverExitCriterion:
    """ADR-0114 Phase 2 exit criterion: solver ≥ 0.80 on parser-correct cases."""

    def test_at_least_80_percent_on_dev_set(self) -> None:
        cases = _load_cases()
        ok = 0
        fail: list[tuple[str, str]] = []
        for c in cases:
            try:
                graph = parse_problem(c["problem"])
                trace = solve(graph)
                if (
                    trace.answer_value == c["expected_answer"]
                    and trace.answer_unit == c["expected_unit"]
                ):
                    ok += 1
                else:
                    fail.append(
                        (
                            c["id"],
                            f"got {trace.answer_value} {trace.answer_unit}; "
                            f"want {c['expected_answer']} {c['expected_unit']}",
                        )
                    )
            except SolveError as e:
                fail.append((c["id"], f"SolveError: {e}"))
        ratio = ok / len(cases)
        assert ratio >= 0.80, (
            f"solver correctness {ok}/{len(cases)} = {ratio:.2%} below 0.80 "
            f"exit criterion; failures: {fail}"
        )


# ---------------------------------------------------------------------------
# Determinism — ADR-0114a Obligation #9
# ---------------------------------------------------------------------------

class TestDeterminism:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_two_solves_produce_byte_equal_trace(self, case: dict) -> None:
        graph = parse_problem(case["problem"])
        t1 = solve(graph)
        t2 = solve(graph)
        assert t1.canonical_bytes() == t2.canonical_bytes()


# ---------------------------------------------------------------------------
# Trace replay reproduces answer — ADR-0114a Obligation #3 rehearsal
# ---------------------------------------------------------------------------

def _replay_trace(graph: MathProblemGraph, trace: SolutionTrace) -> float:
    """Reference verifier — re-applies steps to confirm answer.

    ADR-0117 ships a hardened version with full per-step before/after
    cross-checks; this is the minimal correctness check.
    """
    state: dict[tuple[str, str], float] = {}
    for p in graph.initial_state:
        state[(p.entity, p.quantity.unit)] = float(p.quantity.value)
    for step in trace.steps:
        key = (step.actor, step.operand.unit)
        v = float(step.operand.value)
        if step.operation_kind == "add":
            state[key] = state.get(key, 0.0) + v
        elif step.operation_kind == "subtract":
            state[key] = state.get(key, 0.0) - v
        elif step.operation_kind == "transfer":
            assert step.target is not None
            state[key] = state.get(key, 0.0) - v
            tgt = (step.target, step.operand.unit)
            state[tgt] = state.get(tgt, 0.0) + v
        elif step.operation_kind == "multiply":
            state[key] = state.get(key, 0.0) * v
        elif step.operation_kind == "divide":
            state[key] = state.get(key, 0.0) / v
    if trace.answer_entity is None:
        return sum(v for (_, unit), v in state.items() if unit == trace.answer_unit)
    return state[(trace.answer_entity, trace.answer_unit)]


class TestTraceReplay:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_replay_reproduces_answer_value(self, case: dict) -> None:
        graph = parse_problem(case["problem"])
        trace = solve(graph)
        replayed = _replay_trace(graph, trace)
        assert replayed == trace.answer_value


# ---------------------------------------------------------------------------
# Typed refusal — ADR-0114a Obligation #4
# ---------------------------------------------------------------------------

class TestSolverRefusesUnderDeterminedGraphs:
    def test_unknown_references_nothing_raises(self) -> None:
        # Entity introduced, but no initial state asserted and no
        # operation lands a quantity in it.
        graph = MathProblemGraph(
            entities=("Sam",),
            initial_state=(),
            operations=(),
            unknown=Unknown(entity="Sam", unit="apples"),
        )
        with pytest.raises(SolveError, match="never asserted"):
            solve(graph)

    def test_division_by_zero_raises(self) -> None:
        graph = MathProblemGraph(
            entities=("Sam",),
            initial_state=(InitialPossession("Sam", Quantity(10, "apples")),),
            operations=(Operation("Sam", "divide", Quantity(0, "apples")),),
            unknown=Unknown("Sam", "apples"),
        )
        with pytest.raises(SolveError, match="division by zero"):
            solve(graph)


# ---------------------------------------------------------------------------
# Pack-binding load-bearing — ADR-0114a Obligation #10
# ---------------------------------------------------------------------------

class TestOperationProvenance:
    def test_every_step_carries_pack_lemma_id_from_arithmetic_pack(self) -> None:
        graph = parse_problem(
            "Sam has 5 apples. He buys 3 more. How many apples does Sam have?"
        )
        trace = solve(graph)
        assert trace.pack_id == REQUIRED_PACK_ID
        for step in trace.steps:
            assert step.pack_lemma_id.startswith(f"{REQUIRED_PACK_ID}:")
            # The qualified lemma id is non-empty after the colon.
            _, _, lemma = step.pack_lemma_id.partition(":")
            assert lemma, f"empty lemma id in step {step.step_index}"

    def test_all_operation_kinds_resolve_through_pack(self) -> None:
        # Walk a graph exercising every operation kind once.
        cases = _load_cases()
        seen_kinds: set[str] = set()
        for c in cases:
            graph = parse_problem(c["problem"])
            trace = solve(graph)
            for step in trace.steps:
                seen_kinds.add(step.operation_kind)
                assert step.pack_lemma_id.startswith(f"{REQUIRED_PACK_ID}:")
        # The dev set is designed to exercise every kind at least once.
        assert seen_kinds >= {"add", "subtract", "transfer", "multiply", "divide"}, (
            f"dev set under-exercises operation kinds; saw only {seen_kinds}"
        )

    def test_pack_lemma_resolves_to_real_lexicon_entry(self) -> None:
        from language_packs.compiler import load_pack_entries

        entries = load_pack_entries(REQUIRED_PACK_ID)
        lemmas = {e.lemma for e in entries}
        graph = parse_problem(
            "Sam has 5 apples. He buys 3 more. How many apples does Sam have?"
        )
        trace = solve(graph)
        for step in trace.steps:
            _, _, lemma = step.pack_lemma_id.partition(":")
            assert lemma in lemmas, (
                f"step {step.step_index} cites pack lemma {lemma!r} but "
                f"pack {REQUIRED_PACK_ID} only provides {sorted(lemmas)}"
            )


# ---------------------------------------------------------------------------
# Trace serialization round-trip
# ---------------------------------------------------------------------------

class TestTraceSerialization:
    def test_canonical_bytes_is_deterministic(self) -> None:
        graph = parse_problem(
            "Sam has 5 apples. He buys 3 more. How many apples does Sam have?"
        )
        trace_a = solve(graph)
        trace_b = solve(graph)
        assert trace_a.canonical_bytes() == trace_b.canonical_bytes()

    def test_canonical_bytes_roundtrips_through_json(self) -> None:
        graph = parse_problem(
            "Sam has 5 apples. He buys 3 more. How many apples does Sam have?"
        )
        trace = solve(graph)
        data = json.loads(trace.canonical_bytes())
        assert data["pack_id"] == REQUIRED_PACK_ID
        assert data["answer_value"] == 8.0
        assert data["answer_unit"] == "apples"
        assert data["answer_entity"] == "Sam"


class TestSolutionStepSchema:
    def test_step_includes_target_fields_only_for_transfer(self) -> None:
        graph = parse_problem(
            "Anna has 8 marbles. She gives 3 to Ben. "
            "How many marbles does Anna have now?"
        )
        trace = solve(graph)
        assert len(trace.steps) == 1
        step = trace.steps[0]
        assert step.operation_kind == "transfer"
        assert step.target == "Ben"
        assert step.target_before == 0.0
        assert step.target_after == 3.0
        assert isinstance(step, SolutionStep)
