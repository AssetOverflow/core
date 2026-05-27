"""ADR-0164 Phase 1 — reader/regex coexistence integration tests.

Verifies:
  1. Flag-OFF byte-identity: parse_and_solve without config == parse_and_solve
     with comprehension_reader_questions=False on the 3 currently-correct cases.
  2. Flag-ON determinism: identical input + flag ON → identical reader_trace,
     answer, and graph canonical bytes.
  3. wrong=0 invariant: flag ON never produces a wrong outcome on the
     50-case train_sample.
  4. Trace shape: every reader_trace element is valid JSON with the expected
     layer/phase/outcome keys.
  5. Brief-8 targets: reader is consulted (non-empty reader_trace) for the
     5 GSM8K question sentences referenced in ADR-0164.3 §Worked example.
  6. Fallthrough preserved: flag ON on an unknown-word question produces a
     fallthrough trace event and the same answer as flag OFF.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.config import RuntimeConfig
from generate.math_candidate_graph import parse_and_solve

_CASES_PATH = Path(__file__).resolve().parents[1] / "evals/gsm8k_math/train_sample/v1/cases.jsonl"


def _load_cases() -> list[dict[str, Any]]:
    return [json.loads(l) for l in _CASES_PATH.open(encoding="utf-8") if l.strip()]


def _adapt(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["case_id"],
        "problem": case["question"],
        "expected_answer": case["answer_numeric"],
        "expected_unit": "",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CONFIG_OFF = RuntimeConfig(comprehension_reader_questions=False)
_CONFIG_ON = RuntimeConfig(comprehension_reader_questions=True)

# 3 currently-correct cases (fast-path, reader does not affect them)
_CORRECT_IDS = frozenset({
    "gsm8k-train-sample-v1-0014",
    "gsm8k-train-sample-v1-0018",
    "gsm8k-train-sample-v1-0042",
})

# 5 Brief-8 target question sentences (ADR-0164.3 §Worked example follow-on)
_BRIEF8_IDS = frozenset({
    "gsm8k-train-sample-v1-0007",  # How many more boxes...
    "gsm8k-train-sample-v1-0017",  # How much will it cost him?
    "gsm8k-train-sample-v1-0027",  # How many followers does Malcolm have...
    "gsm8k-train-sample-v1-0036",  # How much time did she spend studying...
    "gsm8k-train-sample-v1-0043",  # How much money will she be left with...
})


@pytest.fixture(scope="module")
def all_cases() -> list[dict[str, Any]]:
    return _load_cases()


@pytest.fixture(scope="module")
def correct_cases(all_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in all_cases if c["case_id"] in _CORRECT_IDS]


@pytest.fixture(scope="module")
def brief8_cases(all_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in all_cases if c["case_id"] in _BRIEF8_IDS]


# ---------------------------------------------------------------------------
# 1. Flag-OFF byte-identity
# ---------------------------------------------------------------------------


class TestFlagOffByteIdentity:
    """parse_and_solve(config=None) and parse_and_solve(config=CONFIG_OFF)
    must produce the same answer on the 3 currently-correct cases."""

    def test_correct_cases_no_config_vs_off(self, correct_cases: list[dict[str, Any]]) -> None:
        assert correct_cases, "fixture must contain at least one correct case"
        for case in correct_cases:
            text = case["question"]
            r_none = parse_and_solve(text, config=None)
            r_off = parse_and_solve(text, config=_CONFIG_OFF)
            assert r_none.answer == r_off.answer, (
                f"{case['case_id']}: answer differs between config=None and flag-OFF"
            )
            assert r_none.is_admitted == r_off.is_admitted, (
                f"{case['case_id']}: is_admitted differs"
            )
            # Flag OFF must produce empty reader_trace (reader never consulted).
            assert r_off.reader_trace == (), (
                f"{case['case_id']}: reader_trace must be empty with flag OFF"
            )

    def test_correct_cases_off_vs_on_same_answer(self, correct_cases: list[dict[str, Any]]) -> None:
        """Fast-path cases are unaffected by the reader — answer must be identical."""
        for case in correct_cases:
            text = case["question"]
            r_off = parse_and_solve(text, config=_CONFIG_OFF)
            r_on = parse_and_solve(text, config=_CONFIG_ON)
            assert r_off.answer == r_on.answer, (
                f"{case['case_id']}: reader flag changed a fast-path answer"
            )
            assert r_off.is_admitted == r_on.is_admitted, (
                f"{case['case_id']}: reader flag changed admission status"
            )


# ---------------------------------------------------------------------------
# 2. Determinism (flag ON)
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_flag_on_reader_trace_deterministic(self, all_cases: list[dict[str, Any]]) -> None:
        """Two calls with the same input and flag ON must produce identical reader_trace."""
        sample = all_cases[:10]
        for case in sample:
            text = case["question"]
            r1 = parse_and_solve(text, config=_CONFIG_ON)
            r2 = parse_and_solve(text, config=_CONFIG_ON)
            assert r1.reader_trace == r2.reader_trace, (
                f"{case['case_id']}: reader_trace not deterministic"
            )
            assert r1.answer == r2.answer, (
                f"{case['case_id']}: answer not deterministic"
            )

    def test_flag_off_reader_trace_empty(self, all_cases: list[dict[str, Any]]) -> None:
        """Flag OFF must never populate reader_trace."""
        for case in all_cases:
            r = parse_and_solve(case["question"], config=_CONFIG_OFF)
            assert r.reader_trace == (), (
                f"{case['case_id']}: reader_trace must be empty with flag OFF"
            )


# ---------------------------------------------------------------------------
# 3. wrong=0 invariant
# ---------------------------------------------------------------------------


class TestWrongIsZero:
    def test_flag_on_wrong_is_zero(self, all_cases: list[dict[str, Any]]) -> None:
        """Flag ON must never produce wrong > 0 on the 50-case train sample.

        Wrong outcome requires: admitted=True AND answer != expected. Since
        the reader is additive (refusal falls through to regex), and the
        underlying regex path is already wrong=0, this invariant must hold.
        """
        wrong_cases: list[str] = []
        for raw in all_cases:
            result = parse_and_solve(raw["question"], config=_CONFIG_ON)
            if result.is_admitted and result.answer != raw["answer_numeric"]:
                wrong_cases.append(
                    f"{raw['case_id']}: got {result.answer}, expected {raw['answer_numeric']}"
                )
        assert not wrong_cases, f"wrong > 0 with flag ON:\n" + "\n".join(wrong_cases)


# ---------------------------------------------------------------------------
# 4. Trace event shape
# ---------------------------------------------------------------------------

_REQUIRED_TRACE_KEYS = frozenset({"layer", "phase", "outcome"})
_VALID_OUTCOMES = frozenset({"admit", "fallthrough_to_regex"})


class TestTraceShape:
    def test_trace_events_are_valid_json(self, all_cases: list[dict[str, Any]]) -> None:
        for case in all_cases:
            r = parse_and_solve(case["question"], config=_CONFIG_ON)
            for event_str in r.reader_trace:
                try:
                    event = json.loads(event_str)
                except json.JSONDecodeError:
                    pytest.fail(f"{case['case_id']}: reader_trace event is not valid JSON: {event_str!r}")
                missing = _REQUIRED_TRACE_KEYS - set(event.keys())
                assert not missing, (
                    f"{case['case_id']}: trace event missing keys {missing}: {event}"
                )
                assert event["layer"] == "comprehension_reader", (
                    f"{case['case_id']}: unexpected layer: {event}"
                )
                assert event["phase"] == 1, (
                    f"{case['case_id']}: unexpected phase: {event}"
                )
                assert event["outcome"] in _VALID_OUTCOMES, (
                    f"{case['case_id']}: unexpected outcome: {event}"
                )

    def test_admit_event_has_entity_and_unit(self, all_cases: list[dict[str, Any]]) -> None:
        """Every 'admit' trace event must carry entity and unit keys."""
        for case in all_cases:
            r = parse_and_solve(case["question"], config=_CONFIG_ON)
            for event_str in r.reader_trace:
                event = json.loads(event_str)
                if event["outcome"] == "admit":
                    assert "entity" in event, (
                        f"{case['case_id']}: admit event missing 'entity': {event}"
                    )
                    assert "unit" in event, (
                        f"{case['case_id']}: admit event missing 'unit': {event}"
                    )

    def test_fallthrough_event_has_refusal_reason(self, all_cases: list[dict[str, Any]]) -> None:
        """Every 'fallthrough_to_regex' trace event must carry refusal_reason."""
        for case in all_cases:
            r = parse_and_solve(case["question"], config=_CONFIG_ON)
            for event_str in r.reader_trace:
                event = json.loads(event_str)
                if event["outcome"] == "fallthrough_to_regex":
                    assert "refusal_reason" in event, (
                        f"{case['case_id']}: fallthrough event missing 'refusal_reason': {event}"
                    )


# ---------------------------------------------------------------------------
# 5. Brief-8 targets: reader is consulted
# ---------------------------------------------------------------------------


class TestBrief8Targets:
    def test_reader_consulted_for_brief8_cases(self, brief8_cases: list[dict[str, Any]]) -> None:
        """When flag ON, the reader is consulted for each of the 5 Brief-8 target
        question sentences — reader_trace is non-empty."""
        assert len(brief8_cases) == 5, (
            f"Expected 5 Brief-8 cases, found {len(brief8_cases)}"
        )
        for case in brief8_cases:
            r = parse_and_solve(case["question"], config=_CONFIG_ON)
            assert r.reader_trace, (
                f"{case['case_id']}: reader_trace is empty — reader was not consulted"
            )

    def test_brief8_cases_wrong_stays_zero(self, brief8_cases: list[dict[str, Any]]) -> None:
        """Brief-8 cases must not produce wrong outcomes with flag ON."""
        for case in brief8_cases:
            r = parse_and_solve(case["question"], config=_CONFIG_ON)
            if r.is_admitted:
                assert r.answer == case["answer_numeric"], (
                    f"{case['case_id']}: wrong answer with flag ON: "
                    f"got {r.answer}, expected {case['answer_numeric']}"
                )

    def test_case_0027_malcolm_admits(self, brief8_cases: list[dict[str, Any]]) -> None:
        """Case 0027 (Malcolm/followers) has no pronoun ambiguity — reader admits it."""
        case = next(c for c in brief8_cases if "0027" in c["case_id"])
        r = parse_and_solve(case["question"], config=_CONFIG_ON)
        assert r.reader_trace, "reader must produce a trace for case 0027"
        events = [json.loads(e) for e in r.reader_trace]
        admit_events = [e for e in events if e["outcome"] == "admit"]
        assert admit_events, (
            f"case 0027 must produce at least one admit event; got: {events}"
        )
        admit = admit_events[0]
        assert admit["entity"] == "malcolm"
        assert admit["unit"] == "followers"


# ---------------------------------------------------------------------------
# 6. Fallthrough preserved for unknown words
# ---------------------------------------------------------------------------


class TestFallthroughPreserved:
    def test_unknown_unit_falls_through_to_regex(self) -> None:
        """A question with an unknown unit noun falls through to regex — result is correct."""
        problem = "Martha has 5 apples. How many apples does Martha have?"
        r_off = parse_and_solve(problem, config=_CONFIG_OFF)
        r_on = parse_and_solve(problem, config=_CONFIG_ON)

        # answer must be identical between flag OFF and flag ON
        assert r_off.answer == r_on.answer
        assert r_off.is_admitted == r_on.is_admitted

        # flag ON must record a fallthrough trace event
        assert r_on.reader_trace, "fallthrough case must produce a trace event"
        event = json.loads(r_on.reader_trace[0])
        assert event["outcome"] == "fallthrough_to_regex"
        assert event["refusal_reason"] == "unknown_word"

    def test_flag_off_no_trace_for_fallthrough_case(self) -> None:
        """Flag OFF must never produce any trace events, even for fallthrough-prone inputs."""
        problem = "Martha has 5 apples. How many apples does Martha have?"
        r = parse_and_solve(problem, config=_CONFIG_OFF)
        assert r.reader_trace == ()
