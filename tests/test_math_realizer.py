"""ADR-0118 — stepped realizer invariants.

Pins five load-bearing invariants:

1. **Every dev-set case realizes.** All 50 cases produce a
   :class:`RealizedTrace` without raising.

2. **Determinism.** Same trace produces byte-equal RealizedTrace bytes
   across two calls.

3. **Setup sentences cover every entity with initial state.** One
   setup sentence per :class:`InitialPossession`.

4. **Step sentence count equals operation count.** Exactly one step
   sentence per :class:`SolutionStep`.

5. **Answer sentence contains the resolved answer value.** Both
   numeric value and unit appear in the answer sentence.

Round-trip parseability of the rendered prose is **out of scope for
ADR-0118**; the trace is the verifiable artifact (ADR-0117), the
realizer's prose is human-readable documentation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_parser import parse_problem
from generate.math_realizer import RealizedTrace, RealizerError, realize
from generate.math_solver import REQUIRED_PACK_ID, solve


_REPO_ROOT = Path(__file__).resolve().parent.parent
_CASES_PATH = _REPO_ROOT / "evals" / "gsm8k_parser_dev" / "cases.jsonl"


def _load_cases() -> list[dict]:
    return [
        json.loads(line) for line in _CASES_PATH.read_text().splitlines() if line.strip()
    ]


def _build(case: dict) -> tuple:
    graph = parse_problem(case["problem"])
    trace = solve(graph)
    return graph, trace


class TestAllDevSetCasesRealize:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_realizes_without_error(self, case: dict) -> None:
        graph, trace = _build(case)
        result = realize(graph.initial_state, trace)
        assert isinstance(result, RealizedTrace)
        assert result.pack_id == REQUIRED_PACK_ID


class TestDeterminism:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_two_realizations_produce_byte_equal_output(self, case: dict) -> None:
        graph, trace = _build(case)
        a = realize(graph.initial_state, trace)
        b = realize(graph.initial_state, trace)
        assert a.canonical_bytes() == b.canonical_bytes()


class TestSetupSentenceCoverage:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_one_setup_sentence_per_initial_possession(self, case: dict) -> None:
        graph, trace = _build(case)
        result = realize(graph.initial_state, trace)
        assert len(result.setup_sentences) == len(graph.initial_state)


class TestStepSentenceCoverage:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_one_step_sentence_per_operation(self, case: dict) -> None:
        graph, trace = _build(case)
        result = realize(graph.initial_state, trace)
        assert len(result.step_sentences) == len(trace.steps)


class TestAnswerSentenceContainsResolvedAnswer:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_answer_value_and_unit_appear_in_answer_sentence(
        self, case: dict
    ) -> None:
        graph, trace = _build(case)
        result = realize(graph.initial_state, trace)
        # numeric value (allow integer form when value is integral)
        if isinstance(trace.answer_value, float) and trace.answer_value.is_integer():
            expected_num = str(int(trace.answer_value))
        else:
            expected_num = str(trace.answer_value)
        assert expected_num in result.answer_sentence, (
            f"answer value {expected_num!r} not in {result.answer_sentence!r}"
        )
        # unit (allow singular surface when value == 1)
        if trace.answer_value == 1:
            # singular check is approximate; the unit-stem must be in there
            stem = trace.answer_unit.rstrip("s")
            assert stem in result.answer_sentence
        else:
            assert trace.answer_unit in result.answer_sentence


class TestRealizerRefuses:
    def test_non_solution_trace_input_raises(self) -> None:
        with pytest.raises(RealizerError):
            realize((), object())  # type: ignore[arg-type]


class TestProseSurface:
    def test_simple_case_prose_is_readable(self) -> None:
        graph, trace = _build(
            {"problem": "Sam has 5 apples. He buys 3 more. How many apples does Sam have?"}
        )
        result = realize(graph.initial_state, trace)
        prose = result.as_prose()
        # Should mention the actor, the operand quantity, and the answer
        assert "Sam" in prose
        assert "5 apples" in prose
        assert "3" in prose
        assert "8" in prose

    def test_transfer_case_mentions_target(self) -> None:
        graph, trace = _build(
            {
                "problem": (
                    "Anna has 8 marbles. She gives 3 to Ben. "
                    "How many marbles does Anna have now?"
                )
            }
        )
        result = realize(graph.initial_state, trace)
        prose = result.as_prose()
        assert "Anna" in prose
        assert "Ben" in prose
        assert "3" in prose
        assert "5" in prose

    def test_total_across_question_uses_collective_phrasing(self) -> None:
        graph, trace = _build(
            {
                "problem": (
                    "Tom has 4 stickers. Sara has 7 stickers. "
                    "How many stickers do they have in total?"
                )
            }
        )
        result = realize(graph.initial_state, trace)
        assert "they have" in result.answer_sentence.lower() or "in total" in result.answer_sentence.lower()
        assert "11" in result.answer_sentence


class TestPackIdPropagates:
    @pytest.mark.parametrize("case", _load_cases()[:5], ids=lambda c: c["id"])
    def test_realized_trace_carries_same_pack_id_as_solution_trace(
        self, case: dict
    ) -> None:
        graph, trace = _build(case)
        result = realize(graph.initial_state, trace)
        assert result.pack_id == trace.pack_id == REQUIRED_PACK_ID
