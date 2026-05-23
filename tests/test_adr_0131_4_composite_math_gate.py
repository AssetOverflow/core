"""ADR-0131.4 — Composite math-expert promotion gate tests.

Pins the load-bearing invariants of the gate:
  - thresholds are pinned (changing them requires a new ADR)
  - heterogeneous lane-report shapes (counts vs metrics) both parse
  - gate refuses (passed=False) on any single benchmark failing
  - missing report files refuse cleanly with a typed reason
  - claim_digest is reproducible across calls (deterministic)
  - GSM8K honest disclosure is present but does NOT gate
  - artifact emission is byte-equal across two calls

These tests run against fixture data so they don't depend on the
current state of the committed B-lane reports.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.capability.composite_math_gate import (
    CORRECT_RATE_MIN,
    WRONG_MAX,
    BenchmarkVerdict,
    CompositeMathGateVerdict,
    DEFAULT_GSM8K_PROBE,
    emit_expert_claims_artifact,
    evaluate_composite_math_gate,
)


# ---------------------------------------------------------------------------
# Fixture report builders
# ---------------------------------------------------------------------------


def _write_b1b2_shape(path: Path, *, correct: int, wrong: int, total: int) -> None:
    """B1 + B2 use ``counts: {correct, wrong, refused}`` + top-level
    ``correct_rate``."""
    rate = correct / total if total else 0.0
    path.write_text(
        json.dumps({
            "adr": "0131.1",
            "counts": {"correct": correct, "wrong": wrong, "refused": total - correct - wrong},
            "sample_count": total,
            "correct_rate": rate,
            "exit_criterion": {"passed": wrong == 0 and rate >= 0.95, "wrong_max": 0},
        }, indent=2),
        encoding="utf-8",
    )


def _write_b3_shape(path: Path, *, correct: int, wrong: int, total: int) -> None:
    """B3 uses ``metrics: {correct, wrong, cases_total, correct_rate}``."""
    rate = correct / total if total else 0.0
    path.write_text(
        json.dumps({
            "adr": "0131.3",
            "metrics": {
                "correct": correct,
                "wrong": wrong,
                "cases_total": total,
                "correct_rate": rate,
                "wrong_count_is_zero": wrong == 0,
            },
        }, indent=2),
        encoding="utf-8",
    )


def _write_probe_shape(path: Path, *, admission: int = 0, wrong: int = 0, total: int = 50) -> None:
    path.write_text(
        json.dumps({
            "adr": "0131.G",
            "substrate": "candidate_graph",
            "metrics": {
                "cases_total": total,
                "admitted_solved": admission,
                "admitted_wrong": wrong,
                "refused": total - admission - wrong,
                "admission_rate": admission / total if total else 0.0,
                "safety_rail_intact": wrong == 0,
            },
        }, indent=2),
        encoding="utf-8",
    )


@pytest.fixture
def fixture_lane_paths(tmp_path: Path) -> dict[str, Path]:
    """Build a complete set of passing fixture reports."""
    p = {
        "b1p": tmp_path / "b1_public.json",
        "b1s": tmp_path / "b1_sealed.json",
        "b2": tmp_path / "b2.json",
        "b3": tmp_path / "b3.json",
        "probe": tmp_path / "probe.json",
    }
    _write_b1b2_shape(p["b1p"], correct=185, wrong=0, total=185)
    _write_b1b2_shape(p["b1s"], correct=14, wrong=0, total=14)
    _write_b1b2_shape(p["b2"], correct=40, wrong=0, total=40)
    _write_b3_shape(p["b3"], correct=50, wrong=0, total=50)
    _write_probe_shape(p["probe"], admission=0, wrong=0, total=50)
    return p


# ---------------------------------------------------------------------------
# Threshold pinning
# ---------------------------------------------------------------------------


def test_thresholds_pinned() -> None:
    """ADR-0131 pins the composite gate at 0.95 / wrong==0. Changing
    these requires a new ADR amendment."""
    assert CORRECT_RATE_MIN == 0.95
    assert WRONG_MAX == 0


# ---------------------------------------------------------------------------
# Heterogeneous shape handling
# ---------------------------------------------------------------------------


def test_b1b2_counts_shape_parses(fixture_lane_paths: dict[str, Path]) -> None:
    p = fixture_lane_paths
    v = evaluate_composite_math_gate(
        b1_public_path=p["b1p"], b1_sealed_path=p["b1s"],
        b2_path=p["b2"], b3_path=p["b3"], gsm8k_probe_path=p["probe"],
    )
    by_id = {b.benchmark_id: b for b in v.benchmarks}
    assert by_id["B1_public"].correct == 185
    assert by_id["B1_public"].wrong == 0
    assert by_id["B2_teaching_corpus"].correct == 40


def test_b3_metrics_shape_parses(fixture_lane_paths: dict[str, Path]) -> None:
    p = fixture_lane_paths
    v = evaluate_composite_math_gate(
        b1_public_path=p["b1p"], b1_sealed_path=p["b1s"],
        b2_path=p["b2"], b3_path=p["b3"], gsm8k_probe_path=p["probe"],
    )
    by_id = {b.benchmark_id: b for b in v.benchmarks}
    assert by_id["B3_bounded_grammar"].correct == 50
    assert by_id["B3_bounded_grammar"].cases_total == 50
    assert by_id["B3_bounded_grammar"].correct_rate == 1.0


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------


def test_gate_passes_when_all_benchmarks_pass(fixture_lane_paths: dict[str, Path]) -> None:
    v = evaluate_composite_math_gate(**{
        f"{k}_path" if k.startswith("b") else f"gsm8k_{k}_path": fixture_lane_paths[short]
        for k, short in [
            ("b1_public", "b1p"), ("b1_sealed", "b1s"),
            ("b2", "b2"), ("b3", "b3"), ("probe", "probe"),
        ]
    })
    assert v.composite_gate_passed is True
    assert v.all_benchmarks_passed is True
    assert v.refusal_reason == ""


def test_gate_refuses_when_b1_correct_rate_below_threshold(
    fixture_lane_paths: dict[str, Path], tmp_path: Path,
) -> None:
    p = dict(fixture_lane_paths)
    # B1 public dropped to 0.94 — just under threshold
    _write_b1b2_shape(p["b1p"], correct=94, wrong=0, total=100)
    v = evaluate_composite_math_gate(
        b1_public_path=p["b1p"], b1_sealed_path=p["b1s"],
        b2_path=p["b2"], b3_path=p["b3"], gsm8k_probe_path=p["probe"],
    )
    assert v.composite_gate_passed is False
    assert "B1_public" in v.refusal_reason


def test_gate_refuses_when_any_benchmark_has_wrong_answer(
    fixture_lane_paths: dict[str, Path],
) -> None:
    p = dict(fixture_lane_paths)
    _write_b3_shape(p["b3"], correct=49, wrong=1, total=50)
    v = evaluate_composite_math_gate(
        b1_public_path=p["b1p"], b1_sealed_path=p["b1s"],
        b2_path=p["b2"], b3_path=p["b3"], gsm8k_probe_path=p["probe"],
    )
    assert v.composite_gate_passed is False
    by_id = {b.benchmark_id: b for b in v.benchmarks}
    assert by_id["B3_bounded_grammar"].passed is False
    assert by_id["B3_bounded_grammar"].wrong_count_is_zero is False


def test_gate_refuses_when_report_missing(
    fixture_lane_paths: dict[str, Path], tmp_path: Path,
) -> None:
    missing = tmp_path / "does_not_exist.json"
    v = evaluate_composite_math_gate(
        b1_public_path=missing,
        b1_sealed_path=fixture_lane_paths["b1s"],
        b2_path=fixture_lane_paths["b2"],
        b3_path=fixture_lane_paths["b3"],
        gsm8k_probe_path=fixture_lane_paths["probe"],
    )
    assert v.composite_gate_passed is False
    by_id = {b.benchmark_id: b for b in v.benchmarks}
    assert by_id["B1_public"].passed is False
    assert "missing" in by_id["B1_public"].refusal_reason.lower()


# ---------------------------------------------------------------------------
# Honest disclosure (GSM8K reported but does NOT gate)
# ---------------------------------------------------------------------------


def test_gsm8k_honest_disclosure_does_not_gate(
    fixture_lane_paths: dict[str, Path],
) -> None:
    """Even with 0/50 admission, the composite gate passes — GSM8K is
    reported as honest disclosure, never gates per ADR-0131."""
    v = evaluate_composite_math_gate(**{
        "b1_public_path": fixture_lane_paths["b1p"],
        "b1_sealed_path": fixture_lane_paths["b1s"],
        "b2_path": fixture_lane_paths["b2"],
        "b3_path": fixture_lane_paths["b3"],
        "gsm8k_probe_path": fixture_lane_paths["probe"],
    })
    assert v.composite_gate_passed is True
    assert v.honest_disclosure["admission_rate"] == 0.0
    assert v.honest_disclosure["available"] is True


def test_gsm8k_disclosure_handles_missing_probe(
    fixture_lane_paths: dict[str, Path], tmp_path: Path,
) -> None:
    v = evaluate_composite_math_gate(
        b1_public_path=fixture_lane_paths["b1p"],
        b1_sealed_path=fixture_lane_paths["b1s"],
        b2_path=fixture_lane_paths["b2"],
        b3_path=fixture_lane_paths["b3"],
        gsm8k_probe_path=tmp_path / "missing_probe.json",
    )
    # Composite gate still passes — probe is disclosure-only.
    assert v.composite_gate_passed is True
    assert v.honest_disclosure["available"] is False


# ---------------------------------------------------------------------------
# Determinism + artifact byte-equality
# ---------------------------------------------------------------------------


def test_claim_digest_reproducible(fixture_lane_paths: dict[str, Path]) -> None:
    v1 = evaluate_composite_math_gate(
        b1_public_path=fixture_lane_paths["b1p"],
        b1_sealed_path=fixture_lane_paths["b1s"],
        b2_path=fixture_lane_paths["b2"],
        b3_path=fixture_lane_paths["b3"],
        gsm8k_probe_path=fixture_lane_paths["probe"],
    )
    v2 = evaluate_composite_math_gate(
        b1_public_path=fixture_lane_paths["b1p"],
        b1_sealed_path=fixture_lane_paths["b1s"],
        b2_path=fixture_lane_paths["b2"],
        b3_path=fixture_lane_paths["b3"],
        gsm8k_probe_path=fixture_lane_paths["probe"],
    )
    assert v1.claim_digest == v2.claim_digest
    assert len(v1.claim_digest) == 64  # SHA-256 hex


def test_artifact_emission_byte_equal(
    fixture_lane_paths: dict[str, Path], tmp_path: Path,
) -> None:
    v = evaluate_composite_math_gate(
        b1_public_path=fixture_lane_paths["b1p"],
        b1_sealed_path=fixture_lane_paths["b1s"],
        b2_path=fixture_lane_paths["b2"],
        b3_path=fixture_lane_paths["b3"],
        gsm8k_probe_path=fixture_lane_paths["probe"],
    )
    out1 = tmp_path / "claims1.json"
    out2 = tmp_path / "claims2.json"
    emit_expert_claims_artifact(v, out1)
    emit_expert_claims_artifact(v, out2)
    assert out1.read_bytes() == out2.read_bytes()


# ---------------------------------------------------------------------------
# Dry-run against current main state (verifies committed lane reports
# satisfy the gate today). This is the actual ADR-0131.4 verdict.
# ---------------------------------------------------------------------------


def test_committed_main_state_satisfies_composite_gate() -> None:
    """Snapshot test of the ADR-0131.4 promotion verdict: as of this
    PR, all four B-lane reports committed to main produce a PASSING
    composite gate. If this test ever fails, the math expert promotion
    is no longer ratifiable — investigate the failing benchmark."""
    v = evaluate_composite_math_gate()
    assert v.composite_gate_passed is True, (
        f"composite gate failed: {v.refusal_reason}\n"
        f"benchmarks: {[(b.benchmark_id, b.passed, b.correct_rate, b.wrong) for b in v.benchmarks]}"
    )
