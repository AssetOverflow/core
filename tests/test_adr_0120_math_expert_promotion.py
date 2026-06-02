"""ADR-0120 math-expert promotion composer tests.

Pins:
  - each per-obligation inline evaluator (#1, #3, #4, #7, #9)
  - composer integration: every obligation + composite gate pass on
    current main; technical_pass = True; reviewer signature absent →
    promote_admitted = False (the load-bearing initial state)
  - claim_digest reproducible
  - reviewer-signature path: matching digest → admitted; mismatched
    digest → refused with explicit reason
  - artifact emission byte-equal
  - snapshot: today's evidence yields the expected (awaiting-
    signature) verdict
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from core.capability.expert_promotion_math import (
    DOMAIN_ID,
    EXPERT_CLAIMS_KEY,
    _compute_claim_digest,
    _evaluate_obligation_1,
    _evaluate_obligation_3,
    _evaluate_obligation_4,
    _evaluate_obligation_7,
    _evaluate_obligation_9,
    ObligationVerdict,
    emit_promotion_artifact,
    evaluate_math_expert_promotion,
)


# ---------------------------------------------------------------------------
# Inline per-obligation evaluators
# ---------------------------------------------------------------------------


def test_obligation_1_passes_with_clean_sealed_report(tmp_path: Path) -> None:
    sealed = tmp_path / "sealed.json"
    sealed.write_text(json.dumps({
        "counts": {"correct": 14, "wrong": 0, "refused": 0},
        "exit_criterion": {"passed": True, "wrong_max": 0},
    }), encoding="utf-8")
    v = _evaluate_obligation_1(sealed)
    assert v.passed is True
    assert v.obligation_id == "1"


def test_obligation_1_refuses_on_missing_report(tmp_path: Path) -> None:
    v = _evaluate_obligation_1(tmp_path / "missing.json")
    assert v.passed is False
    assert "missing" in v.refusal_reason.lower()


def test_obligation_1_refuses_when_wrong_nonzero(tmp_path: Path) -> None:
    sealed = tmp_path / "sealed.json"
    sealed.write_text(json.dumps({
        "counts": {"correct": 13, "wrong": 1, "refused": 0},
        "exit_criterion": {"passed": False, "wrong_max": 0},
    }), encoding="utf-8")
    v = _evaluate_obligation_1(sealed)
    assert v.passed is False
    assert "wrong=1" in v.refusal_reason


def _b_lane_report(correct: int = 5, wrong: int = 0, with_trace_hash: bool = True) -> dict:
    return {
        "counts": {"correct": correct, "wrong": wrong, "refused": 0},
        "per_case": [
            {
                "case_id": f"case-{i}",
                "outcome": "correct",
                "trace_hash": f"hash-{i}" if with_trace_hash else "",
            }
            for i in range(correct)
        ],
    }


def test_obligation_3_passes_when_every_correct_case_has_trace_hash(tmp_path: Path) -> None:
    p = tmp_path / "lane.json"
    p.write_text(json.dumps(_b_lane_report(correct=3)), encoding="utf-8")
    v = _evaluate_obligation_3((p,))
    assert v.passed is True


def test_obligation_3_refuses_when_a_correct_case_lacks_trace_hash(tmp_path: Path) -> None:
    p = tmp_path / "lane.json"
    p.write_text(json.dumps(_b_lane_report(correct=2, with_trace_hash=False)), encoding="utf-8")
    v = _evaluate_obligation_3((p,))
    assert v.passed is False
    assert "trace_hash" in v.refusal_reason


def test_obligation_4_passes_when_all_lanes_wrong_zero(tmp_path: Path) -> None:
    paths: list[Path] = []
    for i in range(3):
        p = tmp_path / f"l{i}.json"
        p.write_text(json.dumps({"counts": {"correct": 10, "wrong": 0, "refused": 0}}), encoding="utf-8")
        paths.append(p)
    v = _evaluate_obligation_4(tuple(paths))
    assert v.passed is True


def test_obligation_4_refuses_on_any_wrong(tmp_path: Path) -> None:
    p1 = tmp_path / "l1.json"
    p1.write_text(json.dumps({"counts": {"correct": 9, "wrong": 1, "refused": 0}}), encoding="utf-8")
    v = _evaluate_obligation_4((p1,))
    assert v.passed is False
    assert "wrong=1" in v.refusal_reason


def test_obligation_7_passes_when_frontier_dir_has_artifacts(tmp_path: Path) -> None:
    frontier = tmp_path / "frontier"
    frontier.mkdir()
    (frontier / "comparison_v1.json").write_text("{}", encoding="utf-8")
    v = _evaluate_obligation_7(frontier)
    assert v.passed is True


def test_obligation_7_refuses_when_frontier_dir_missing(tmp_path: Path) -> None:
    v = _evaluate_obligation_7(tmp_path / "nope")
    assert v.passed is False
    assert "missing" in v.refusal_reason.lower()


def test_obligation_7_refuses_when_frontier_dir_empty(tmp_path: Path) -> None:
    frontier = tmp_path / "frontier"
    frontier.mkdir()
    v = _evaluate_obligation_7(frontier)
    assert v.passed is False
    assert "no frontier" in v.refusal_reason.lower()


def test_obligation_9_passes_when_all_lanes_parse(tmp_path: Path) -> None:
    p = tmp_path / "lane.json"
    p.write_text(json.dumps({"counts": {"correct": 1, "wrong": 0}}), encoding="utf-8")
    v = _evaluate_obligation_9((p,))
    assert v.passed is True


def test_obligation_9_refuses_when_a_lane_is_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "lane.json"
    p.write_text("not json", encoding="utf-8")
    v = _evaluate_obligation_9((p,))
    assert v.passed is False
    assert "invalid json" in v.refusal_reason.lower()


# ---------------------------------------------------------------------------
# Composer integration — current main
# ---------------------------------------------------------------------------


def test_composer_runs_on_current_main_with_all_obligations_passing() -> None:
    """Fail-closed revert snapshot (ADR-0200). On current main every
    obligation auditor passes, the composite gate passes, technical_pass is
    True, and the reviewer signature is present — but a non-gating GSM8K
    coverage metric drifted after signing, so the signature no longer matches
    the evidence-derived digest. The composer therefore refuses:
    promote_admitted is False with a digest-mismatch reason. This is
    ADR-0120's load-bearing fail-closed safety property.
    """
    v = evaluate_math_expert_promotion()
    assert v.all_obligations_passed is True, (
        f"obligation regressions: "
        f"{[(o.obligation_id, o.refusal_reason) for o in v.obligations if not o.passed]}"
    )
    assert v.composite_gate_passed is True
    assert v.technical_pass is True
    assert v.reviewer_signature is not None
    assert v.reviewer_signature.get("signed_by") == "shay-j"
    assert v.reviewer_signature_matches is False
    assert v.promote_admitted is False
    assert "mismatch" in v.refusal_reason.lower()
    assert v.claim_digest  # non-empty
    assert len(v.claim_digest) == 64  # SHA-256 hex


def test_promote_admitted_when_signature_matches(tmp_path: Path) -> None:
    """Synthetic reviewers.yaml with a matching claim_digest entry —
    composer flips to promote_admitted = True."""
    # First, compute today's digest by running the composer with the
    # real (empty) reviewers.yaml.
    baseline = evaluate_math_expert_promotion()
    digest = baseline.claim_digest

    # Build a tmp reviewers.yaml carrying a matching entry.
    fake_yaml = tmp_path / "reviewers.yaml"
    fake_yaml.write_text(yaml.safe_dump({
        "schema_version": 1,
        "reviewers": [
            {
                "reviewer_id": "shay-j",
                "display_name": "Joshua Shay",
                "role": "primary",
                "domains": ["*"],
                "review_scope": ["pack", "proposal", "chain", "eval"],
                "provenance": "test",
            }
        ],
        EXPERT_CLAIMS_KEY: [
            {
                "domain_id": DOMAIN_ID,
                "signed_by": "shay-j",
                "claim_digest": digest,
            }
        ],
    }), encoding="utf-8")

    v = evaluate_math_expert_promotion(reviewers_path=fake_yaml)
    assert v.reviewer_signature_matches is True
    assert v.promote_admitted is True
    assert v.refusal_reason == ""


def test_promote_refuses_on_digest_mismatch(tmp_path: Path) -> None:
    fake_yaml = tmp_path / "reviewers.yaml"
    fake_yaml.write_text(yaml.safe_dump({
        "schema_version": 1,
        "reviewers": [],
        EXPERT_CLAIMS_KEY: [
            {
                "domain_id": DOMAIN_ID,
                "signed_by": "shay-j",
                "claim_digest": "0" * 64,  # deliberately wrong
            }
        ],
    }), encoding="utf-8")
    v = evaluate_math_expert_promotion(reviewers_path=fake_yaml)
    assert v.reviewer_signature is not None
    assert v.reviewer_signature_matches is False
    assert v.promote_admitted is False
    assert "mismatch" in v.refusal_reason


# ---------------------------------------------------------------------------
# Digest reproducibility + artifact byte-equality
# ---------------------------------------------------------------------------


def test_claim_digest_reproducible_across_calls() -> None:
    v1 = evaluate_math_expert_promotion()
    v2 = evaluate_math_expert_promotion()
    assert v1.claim_digest == v2.claim_digest


def test_artifact_byte_equal_across_calls(tmp_path: Path) -> None:
    v = evaluate_math_expert_promotion()
    out1 = tmp_path / "a.json"
    out2 = tmp_path / "b.json"
    emit_promotion_artifact(v, out1)
    emit_promotion_artifact(v, out2)
    assert out1.read_bytes() == out2.read_bytes()


def test_claim_digest_changes_when_obligation_evidence_pointer_changes() -> None:
    """Sanity: digest is sensitive to its inputs."""
    o1 = (ObligationVerdict("1", "x", True, "/a"),)
    o2 = (ObligationVerdict("1", "x", True, "/b"),)
    d1 = _compute_claim_digest(o1, "composite-digest")
    d2 = _compute_claim_digest(o2, "composite-digest")
    assert d1 != d2
