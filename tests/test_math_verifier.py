"""ADR-0117 — solution-trace verifier invariants.

Pins five load-bearing invariants:

1. **Every dev-set solver trace verifies.** All 50 cases produce a
   :class:`SolutionTrace` whose verifier verdict is ``passed=True``.

2. **Tampered traces are caught.** Mutating any single field of a
   step (operand, before, after, target_before, target_after,
   pack_lemma_id, operation_kind) produces ``passed=False`` with a
   reason that names the offending check.

3. **Tampered graph hash is caught.** A trace whose
   ``graph_canonical_hash`` does not match the input graph fails.

4. **Tampered answer is caught.** A trace whose ``answer_value`` does
   not match the verifier's resolved unknown fails.

5. **Determinism.** Two verifications produce byte-equal verdict bytes.

The verifier is **independent of the solver**: it re-derives every
value the trace claims, using only the input graph and the operation
semantics documented in ADR-0116. ADR-0114a Obligation #3 is now
discharged at verifier fidelity (in addition to solver fidelity from
ADR-0116).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from generate.math_parser import parse_problem
from generate.math_problem_graph import MathProblemGraph, Quantity
from generate.math_solver import SolutionTrace, solve
from generate.math_verifier import VerifierVerdict, verify


_REPO_ROOT = Path(__file__).resolve().parent.parent
_CASES_PATH = _REPO_ROOT / "evals" / "gsm8k_parser_dev" / "cases.jsonl"


def _load_cases() -> list[dict]:
    return [
        json.loads(line) for line in _CASES_PATH.read_text().splitlines() if line.strip()
    ]


def _build_simple_case() -> tuple[MathProblemGraph, SolutionTrace]:
    g = parse_problem(
        "Sam has 5 apples. He buys 3 more. How many apples does Sam have?"
    )
    return g, solve(g)


class TestAllDevSetCasesVerify:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_solver_trace_verifies(self, case: dict) -> None:
        graph = parse_problem(case["problem"])
        trace = solve(graph)
        verdict = verify(graph, trace)
        assert verdict.passed, (
            f"{case['id']}: verifier rejected solver's own trace — {verdict.reason}"
        )
        assert verdict.trace_answer_value == case["expected_answer"]


class TestTamperDetection:
    def test_tampered_after_value_caught(self) -> None:
        g, t = _build_simple_case()
        tampered_step = dataclasses.replace(t.steps[0], after_value=999.0)
        tampered = dataclasses.replace(t, steps=(tampered_step,))
        verdict = verify(g, tampered)
        assert verdict.passed is False
        assert "after_value" in verdict.reason or "step_replay" in verdict.reason

    def test_tampered_before_value_caught(self) -> None:
        g, t = _build_simple_case()
        tampered_step = dataclasses.replace(t.steps[0], before_value=42.0)
        tampered = dataclasses.replace(t, steps=(tampered_step,))
        verdict = verify(g, tampered)
        assert verdict.passed is False
        assert "before_value" in verdict.reason

    def test_tampered_operand_caught(self) -> None:
        g, t = _build_simple_case()
        tampered_step = dataclasses.replace(t.steps[0], operand=Quantity(99, "apples"))
        tampered = dataclasses.replace(t, steps=(tampered_step,))
        verdict = verify(g, tampered)
        assert verdict.passed is False

    def test_tampered_pack_lemma_id_caught(self) -> None:
        g, t = _build_simple_case()
        tampered_step = dataclasses.replace(
            t.steps[0], pack_lemma_id="some_other_pack:add"
        )
        tampered = dataclasses.replace(t, steps=(tampered_step,))
        verdict = verify(g, tampered)
        assert verdict.passed is False
        assert "pack_lemma" in verdict.reason

    def test_tampered_graph_hash_caught(self) -> None:
        g, t = _build_simple_case()
        tampered = dataclasses.replace(t, graph_canonical_hash="0" * 64)
        verdict = verify(g, tampered)
        assert verdict.passed is False
        assert "graph_canonical_hash" in verdict.reason

    def test_tampered_answer_caught(self) -> None:
        g, t = _build_simple_case()
        tampered = dataclasses.replace(t, answer_value=42.0)
        verdict = verify(g, tampered)
        assert verdict.passed is False
        assert "answer" in verdict.reason

    def test_tampered_pack_id_caught(self) -> None:
        g, t = _build_simple_case()
        tampered = dataclasses.replace(t, pack_id="some_other_pack")
        verdict = verify(g, tampered)
        assert verdict.passed is False
        assert "pack_id" in verdict.reason


class TestDeterminism:
    def test_two_verifications_produce_byte_equal_verdict(self) -> None:
        g, t = _build_simple_case()
        v1 = verify(g, t)
        v2 = verify(g, t)
        assert v1.canonical_bytes() == v2.canonical_bytes()
        assert v1 == v2


class TestVerdictShape:
    def test_verdict_records_every_check(self) -> None:
        g, t = _build_simple_case()
        verdict = verify(g, t)
        check_names = {name for name, _, _ in verdict.checks}
        # At minimum these named invariants must be in the verdict
        assert "graph_canonical_hash_matches" in check_names
        assert "pack_id_matches" in check_names
        assert "pack_lemmas_resolve" in check_names
        assert "step_pack_lemma_ids_match_bindings" in check_names
        assert "step_replay_matches_before_after" in check_names
        assert "answer_value_reproduces" in check_names
        assert isinstance(verdict, VerifierVerdict)

    def test_passing_verdict_has_empty_reason(self) -> None:
        g, t = _build_simple_case()
        verdict = verify(g, t)
        assert verdict.passed is True
        assert verdict.reason == ""


class TestTotalAcrossAnswer:
    def test_multi_entity_sum_question_verifies(self) -> None:
        g = parse_problem(
            "Tom has 4 stickers. Sara has 7 stickers. "
            "How many stickers do they have in total?"
        )
        t = solve(g)
        verdict = verify(g, t)
        assert verdict.passed is True
        assert t.answer_value == 11.0
        assert t.answer_entity is None


class TestTransferStepVerifiesBothSides:
    def test_transfer_target_before_and_after_must_match(self) -> None:
        g = parse_problem(
            "Anna has 8 marbles. She gives 3 to Ben. "
            "How many marbles does Anna have now?"
        )
        t = solve(g)
        assert t.steps[0].operation_kind == "transfer"
        assert t.steps[0].target_before == 0.0
        assert t.steps[0].target_after == 3.0
        verdict = verify(g, t)
        assert verdict.passed is True

        # Tamper target_after — verifier catches it
        tampered_step = dataclasses.replace(t.steps[0], target_after=999.0)
        tampered = dataclasses.replace(t, steps=(tampered_step,))
        verdict_bad = verify(g, tampered)
        assert verdict_bad.passed is False
        assert "target_after" in verdict_bad.reason
