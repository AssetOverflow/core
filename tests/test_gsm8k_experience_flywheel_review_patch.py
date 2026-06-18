"""Regression tests for PR #816 review hardening."""

from __future__ import annotations

from dataclasses import replace

from evals.gsm8k_math.runner import CaseOutcome
from evals.gsm8k_math.train_sample.v1.experience import (
    ExperienceRecord,
    build_experience_report,
    compact_records,
    compute_record_id,
)
from evals.gsm8k_math.train_sample.v1.scout import build_scout_row

_RECOGNIZED_DCS = (
    "candidate_graph: recognizer matched but produced no injection "
    "(category=discrete_count_statement)"
)


def _outcome(
    *,
    case_id: str,
    outcome: str,
    reason: str = "",
    actual: float | None = None,
    expected: float = 0.0,
) -> CaseOutcome:
    return CaseOutcome(
        case_id=case_id,
        outcome=outcome,  # type: ignore[arg-type]
        reason=reason,
        expected_answer=expected,
        expected_unit="",
        actual_answer=actual,
        actual_unit=None,
        trace_hash=None,
        realized_prose=None,
    )


def _recognized_row(
    *,
    case_id: str,
    sealed_outcome: str,
    sealed_actual: float,
    expected: float,
):
    raw = {
        "case_id": case_id,
        "question": "Recognized DCS surface",
        "answer_numeric": expected,
        "answer_expression": f"#### {expected:g}",
    }
    served = _outcome(
        case_id=case_id,
        outcome="refused",
        reason=_RECOGNIZED_DCS,
        expected=expected,
    )
    sealed = _outcome(
        case_id=case_id,
        outcome=sealed_outcome,
        reason="resolve_pooled",
        actual=sealed_actual,
        expected=expected,
    )
    return build_scout_row(raw, served, sealed)


def _scout_summary_from_rows(rows) -> dict:
    return {
        "schema_version": 1,
        "adr": "0175",
        "regime": "sealed_attempt_scout",
        "cases_source": "fixture",
        "sample_count": len(rows),
        "serving_counts": {"correct": 0, "wrong": 0, "refused": len(rows)},
        "sealed_counts": {"correct": 1, "wrong": 1, "refused": 0},
        "delta_counts": {},
        "lift_recommendations": [],
        "rows": [r.as_dict() for r in rows],
    }


def test_matching_sealed_wrong_blocks_lift_family_candidate():
    lift = _recognized_row(
        case_id="gsm8k-train-sample-v1-0003",
        sealed_outcome="correct",
        sealed_actual=864.0,
        expected=864.0,
    )
    sealed_wrong = _recognized_row(
        case_id="gsm8k-train-sample-v1-0345",
        sealed_outcome="wrong",
        sealed_actual=6720.0,
        expected=595.0,
    )
    report = build_experience_report(_scout_summary_from_rows((lift, sealed_wrong)))
    families = {row["family"]: row for row in report["family_summaries"]}

    family = families["relation_hypothesis:discrete_count_statement"]
    assert family["refused_to_correct_count"] == 1
    assert family["blocked_count"] == 1
    assert family["promotion_status"] == "blocked_by_wrong_risk"


def _record(
    *,
    source_run_id: str,
    serving_status: str,
    promotion_status: str,
) -> ExperienceRecord:
    rec = ExperienceRecord(
        record_id="",
        case_id="gsm8k-train-sample-v1-0003",
        serving_status=serving_status,  # type: ignore[arg-type]
        sealed_status="correct",
        gold_answer="864",
        sealed_answer="864",
        serving_refusal_family="lift_family",
        sealed_failure_family="lift_family",
        candidate_family="relation_hypothesis:discrete_count_statement",
        first_missing_primitive="relation_hypothesis",
        arithmetic_chain_signature="lift_refused_to_correct|multiplicative|recognizer_injection|same",
        positive_evidence_refs=(f"scout:run={source_run_id}",),
        negative_evidence_refs=(),
        hazard_tags=(),
        recommended_action="action",
        promotion_status=promotion_status,  # type: ignore[arg-type]
        source_run_id=source_run_id,
        source_report_hash=f"hash-{source_run_id}",
    )
    return replace(rec, record_id=compute_record_id(rec))


def test_compact_records_preserves_caller_order_not_hash_order():
    old = _record(
        source_run_id="z-old",
        serving_status="refused",
        promotion_status="candidate",
    )
    new = _record(
        source_run_id="a-new",
        serving_status="correct",
        promotion_status="promoted_in_pr",
    )

    compacted = compact_records((old, new))
    assert compacted[0].first_seen_run_id == "z-old"
    assert compacted[0].last_seen_run_id == "a-new"
    assert compacted[0].promotion_status == "promoted_in_pr"
    assert compacted[0].status_transitions == (
        "refused/correct:candidate",
        "correct/correct:promoted_in_pr",
    )

    reversed_compacted = compact_records((new, old))
    assert reversed_compacted[0].first_seen_run_id == "a-new"
    assert reversed_compacted[0].last_seen_run_id == "z-old"
    assert reversed_compacted[0].promotion_status == "candidate"
    assert reversed_compacted[0].status_transitions == (
        "correct/correct:promoted_in_pr",
        "refused/correct:candidate",
    )
