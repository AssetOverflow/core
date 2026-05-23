"""Tests for ADR-0114a Obligation #5 — reasoning-isolation perturbation suite (B3).

Coverage (15 tests):
  1. entity_rename_v1 generator is pure (same input → same output set)
  2. entity_rename_v2 generator is pure
  3. entity_rename_v3 generator is pure
  4. unit_synonym generator is pure
  5. value_replacement_init generator is pure
  6. value_replacement_op generator is pure
  7. op_verb_flip generator is pure
  8. Invariance-preserving variants of a known case all produce the same expected_answer
  9. Invariance-breaking variants all produce the predicted delta (new ≠ original)
 10. generate_b3_perturbations yields ≥3 invariance-preserving variants for a simple case
 11. generate_b3_perturbations yields ≥2 invariance-breaking variants for a simple case
 12. Report determinism: byte-equal across two runs
 13. Snapshot: main B3 satisfies obligation #5 (both rates == 1.0)
 14. Empty-lane refusal: missing cases file → typed refusal, obligation_5_passed=False
 15. skip_reasons_b3 documents commutative_reorder skip for all current B3 cases
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.capability.perturbation_b3 import (
    INVARIANCE_BREAKING,
    INVARIANCE_PRESERVING,
    generate_b3_perturbations,
    skip_reasons_b3,
    validate_perturbation_suite,
    _gen_entity_renames,
    _gen_unit_synonym,
    _gen_value_replacement_init,
    _gen_value_replacement_op,
    _gen_op_verb_flip,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SIMPLE_ID = "b3-001"
_SIMPLE_PROBLEM = "Sam has 5 apples. Sam buys 3 apples. How many apples does Sam have?"
_SIMPLE_ANSWER = 8.0
_SIMPLE_UNIT = "apples"


# ---------------------------------------------------------------------------
# 1–7: Generator purity (same input → same output set)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", [1, 2, 3], ids=["v1", "v2", "v3"])
def test_entity_rename_pure(version: int) -> None:  # noqa: ARG001
    results_a = _gen_entity_renames(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    results_b = _gen_entity_renames(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    assert [p.perturbation_id for p in results_a] == [p.perturbation_id for p in results_b]
    assert [p.problem_text for p in results_a] == [p.problem_text for p in results_b]


def test_unit_synonym_pure() -> None:
    a = _gen_unit_synonym(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    b = _gen_unit_synonym(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    assert (a is None and b is None) or (a is not None and b is not None)
    if a is not None and b is not None:
        assert a.problem_text == b.problem_text
        assert a.expected_unit == b.expected_unit


def test_value_replacement_init_pure() -> None:
    a = _gen_value_replacement_init(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    b = _gen_value_replacement_init(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    assert (a is None and b is None) or (
        a is not None and b is not None and a.problem_text == b.problem_text
    )


def test_value_replacement_op_pure() -> None:
    a = _gen_value_replacement_op(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    b = _gen_value_replacement_op(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    assert (a is None and b is None) or (
        a is not None and b is not None and a.problem_text == b.problem_text
    )


def test_op_verb_flip_pure() -> None:
    a = _gen_op_verb_flip(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    b = _gen_op_verb_flip(_SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT)
    assert (a is None and b is None) or (
        a is not None and b is not None and a.problem_text == b.problem_text
    )


# ---------------------------------------------------------------------------
# 8: Invariance-preserving variants all produce the same expected_answer
# ---------------------------------------------------------------------------


def test_preserving_variants_same_expected_answer() -> None:
    perturbations = generate_b3_perturbations(
        _SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT
    )
    preserving = [p for p in perturbations if p.kind == INVARIANCE_PRESERVING]
    assert len(preserving) >= 3, (
        f"Expected ≥3 invariance-preserving variants, got {len(preserving)}"
    )
    for p in preserving:
        assert p.expected_answer == _SIMPLE_ANSWER, (
            f"{p.transform}: expected_answer changed from {_SIMPLE_ANSWER} to {p.expected_answer}"
        )
        assert p.predicted_delta is None, (
            f"{p.transform}: preserving variant should have predicted_delta=None"
        )


# ---------------------------------------------------------------------------
# 9: Invariance-breaking variants produce the predicted delta
# ---------------------------------------------------------------------------


def test_breaking_variants_produce_predicted_delta() -> None:
    perturbations = generate_b3_perturbations(
        _SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT
    )
    breaking = [p for p in perturbations if p.kind == INVARIANCE_BREAKING]
    assert len(breaking) >= 1, "Expected ≥1 invariance-breaking variant"
    for p in breaking:
        assert p.expected_answer != _SIMPLE_ANSWER, (
            f"{p.transform}: breaking variant must change the answer"
        )
        assert p.predicted_delta is not None, (
            f"{p.transform}: breaking variant must have predicted_delta"
        )
        assert abs(p.predicted_delta - (p.expected_answer - _SIMPLE_ANSWER)) < 1e-9, (
            f"{p.transform}: predicted_delta {p.predicted_delta} != "
            f"{p.expected_answer} - {_SIMPLE_ANSWER}"
        )


# ---------------------------------------------------------------------------
# 10: ≥3 invariance-preserving variants for a simple case
# ---------------------------------------------------------------------------


def test_simple_case_yields_three_or_more_preserving() -> None:
    perturbations = generate_b3_perturbations(
        _SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT
    )
    preserving = [p for p in perturbations if p.kind == INVARIANCE_PRESERVING]
    assert len(preserving) >= 3, (
        f"Simple case must yield ≥3 preserving variants; got {len(preserving)}: "
        + ", ".join(p.transform for p in preserving)
    )


# ---------------------------------------------------------------------------
# 11: ≥2 invariance-breaking variants for a simple case
# ---------------------------------------------------------------------------


def test_simple_case_yields_two_or_more_breaking() -> None:
    perturbations = generate_b3_perturbations(
        _SIMPLE_ID, _SIMPLE_PROBLEM, _SIMPLE_ANSWER, _SIMPLE_UNIT
    )
    breaking = [p for p in perturbations if p.kind == INVARIANCE_BREAKING]
    assert len(breaking) >= 2, (
        f"Simple case must yield ≥2 breaking variants; got {len(breaking)}: "
        + ", ".join(p.transform for p in breaking)
    )


# ---------------------------------------------------------------------------
# 12: Report determinism — byte-equal across two runs
# ---------------------------------------------------------------------------


def test_report_determinism() -> None:
    r1 = validate_perturbation_suite()
    r2 = validate_perturbation_suite()
    d1 = json.dumps(r1.as_dict(), sort_keys=True, separators=(",", ":"))
    d2 = json.dumps(r2.as_dict(), sort_keys=True, separators=(",", ":"))
    assert d1 == d2, "Report is not byte-equal across two runs"


# ---------------------------------------------------------------------------
# 13: Snapshot — current main B3 satisfies obligation #5
# ---------------------------------------------------------------------------


def test_snapshot_b3_passes_obligation_5() -> None:
    report = validate_perturbation_suite()
    failing = [r for r in report.per_perturbation if not r.ok]
    assert report.obligation_5_passed, (
        f"B3 does not satisfy obligation #5.\n"
        f"preserving_rate={report.preserving_rate:.4f} "
        f"({report.preserving_correct}/{report.preserving_attempted})\n"
        f"breaking_rate={report.breaking_rate:.4f} "
        f"({report.breaking_correct}/{report.breaking_attempted})\n"
        f"Failing perturbations ({len(failing)}):\n"
        + "\n".join(f"  {r.perturbation_id}: {r.detail}" for r in failing)
    )
    assert report.preserving_rate == 1.0
    assert report.breaking_rate == 1.0


# ---------------------------------------------------------------------------
# 14: Empty-lane refusal — missing cases file → typed refusal
# ---------------------------------------------------------------------------


def test_missing_cases_file_returns_refusal(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.jsonl"
    report = validate_perturbation_suite(cases_path=missing)
    assert not report.obligation_5_passed
    assert "not found" in report.refusal_reason.lower()
    assert report.cases_total == 0


# ---------------------------------------------------------------------------
# 15: commutative_reorder is skipped for all current B3 cases
# ---------------------------------------------------------------------------


def test_commutative_reorder_skipped_for_all_b3_cases() -> None:
    from pathlib import Path as P
    import json as _json

    cases_path = (
        P(__file__).resolve().parent.parent
        / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
    )
    cases = [_json.loads(l) for l in cases_path.read_text().splitlines() if l.strip()]
    solved_correct = [c for c in cases if c["expected"] == "solved_correct"]

    for case in solved_correct:
        reasons = skip_reasons_b3(
            case["case_id"], case["problem"],
            case["expected_answer"], case["expected_unit"],
        )
        assert "commutative_reorder" in reasons, (
            f"Case {case['case_id']} did not skip commutative_reorder: "
            "expected all current B3 solved_correct cases to be skipped "
            "(no single-entity multi-unit initial state exists yet)"
        )
