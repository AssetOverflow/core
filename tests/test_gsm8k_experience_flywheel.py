"""Tests for GSM8K bounded experience flywheel (PR-1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.gsm8k_math.runner import CaseOutcome
from evals.gsm8k_math.train_sample.v1.experience import (
    build_experience_report,
    compact_records,
    compute_dedupe_key,
    compute_record_id,
    compute_report_hash,
    compute_run_id,
    load_compacted_from_report,
    merge_compacted_runs,
    records_from_scout_rows,
    scout_row_to_experience_record,
    should_retain_row,
    write_experience_json,
)
from evals.gsm8k_math.train_sample.v1.scout import (
    SealedAttemptScoutRow,
    build_scout_row,
    build_scout_summary,
    classify_delta_kind,
)
from formation.hashing import canonical_json

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/report.json"
_FIXTURE_CASES = _REPO_ROOT / "tests/fixtures/gsm8k_experience_flywheel_cases.jsonl"


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


def _lift_row(case_id: str = "gsm8k-train-sample-v1-0003") -> SealedAttemptScoutRow:
    raw = {
        "case_id": case_id,
        "question": "Revenue question",
        "answer_numeric": 864,
        "answer_expression": "#### 864",
    }
    served = _outcome(
        case_id=case_id,
        outcome="refused",
        reason=(
            "candidate_graph: recognizer matched but produced no injection "
            "(category=discrete_count_statement)"
        ),
        expected=864.0,
    )
    sealed = _outcome(
        case_id=case_id,
        outcome="correct",
        reason="resolve_pooled",
        actual=864.0,
        expected=864.0,
    )
    return build_scout_row(raw, served, sealed)


def _sealed_wrong_row(case_id: str = "gsm8k-train-sample-v1-0011") -> SealedAttemptScoutRow:
    raw = {
        "case_id": case_id,
        "question": "Elimination hazard",
        "answer_numeric": 50,
        "answer_expression": "#### 50",
    }
    served = _outcome(
        case_id=case_id,
        outcome="refused",
        reason="candidate_graph: no admissible candidate for statement",
        expected=50.0,
    )
    sealed = _outcome(
        case_id=case_id,
        outcome="wrong",
        reason="resolve_pooled",
        actual=3200.0,
        expected=50.0,
    )
    return build_scout_row(raw, served, sealed)


def _joint_refusal_row(
    case_id: str,
    failure_family: str = "joint_skill_gap_no_admissible_statement",
) -> SealedAttemptScoutRow:
    raw = {
        "case_id": case_id,
        "question": "Joint refusal",
        "answer_numeric": 10,
        "answer_expression": "#### 10",
    }
    served = _outcome(
        case_id=case_id,
        outcome="refused",
        reason="candidate_graph: no admissible candidate for statement",
        expected=10.0,
    )
    sealed = _outcome(
        case_id=case_id,
        outcome="refused",
        reason="resolve_pooled: no resolution",
        expected=10.0,
    )
    row = build_scout_row(raw, served, sealed)
    return SealedAttemptScoutRow(
        case_id=row.case_id,
        served_status=row.served_status,
        aggressive_status=row.aggressive_status,
        aggressive_answer=row.aggressive_answer,
        gold_answer=row.gold_answer,
        refusal_reason=row.refusal_reason,
        failure_family=failure_family,
        candidate_lift_family=row.candidate_lift_family,
        first_failed_step=row.first_failed_step,
        trace_key=row.trace_key,
    )


def _scout_summary_from_rows(rows: tuple[SealedAttemptScoutRow, ...]) -> dict:
    return {
        "schema_version": 1,
        "adr": "0175",
        "regime": "sealed_attempt_scout",
        "cases_source": "fixture",
        "sample_count": len(rows),
        "serving_counts": {"correct": 0, "wrong": 0, "refused": len(rows)},
        "sealed_counts": {"correct": 0, "wrong": 0, "refused": len(rows)},
        "delta_counts": {"joint_refusal": len(rows)},
        "lift_recommendations": [],
        "rows": [r.as_dict() for r in rows],
    }


def test_record_id_is_deterministic():
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    recs = records_from_scout_rows((row,), scout_summary=scout, cases_by_id={})
    assert len(recs) == 1
    a = compute_record_id(recs[0])
    b = compute_record_id(recs[0])
    assert a == b
    assert recs[0].record_id == a


def test_run_id_and_report_hash_deterministic():
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    assert compute_run_id(scout) == compute_run_id(scout)
    assert compute_report_hash(scout) == compute_report_hash(scout)


def test_refused_to_correct_retained_as_candidate():
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    recs = records_from_scout_rows((row,), scout_summary=scout)
    assert len(recs) == 1
    assert recs[0].promotion_status == "candidate"
    assert recs[0].candidate_family is not None
    assert recs[0].first_missing_primitive == "relation_hypothesis"


def test_sealed_wrong_retained_as_blocked():
    row = _sealed_wrong_row()
    scout = _scout_summary_from_rows((row,))
    recs = records_from_scout_rows((row,), scout_summary=scout)
    assert len(recs) == 1
    assert recs[0].promotion_status == "blocked_by_wrong_risk"
    assert "sealed_wrong" in recs[0].hazard_tags
    assert recs[0].negative_evidence_refs


def test_low_signal_joint_refusal_dropped():
    row = _joint_refusal_row("gsm8k-train-sample-v1-9001")
    delta = classify_delta_kind(row.served_status, row.aggressive_status)
    assert delta == "joint_refusal"
    assert not should_retain_row(row, delta_kind=delta, high_freq_joint_families=set())


def test_high_frequency_joint_refusal_retained():
    fam = "joint_skill_gap_no_admissible_statement"
    rows = tuple(_joint_refusal_row(f"gsm8k-train-sample-v1-90{i:02d}", fam) for i in range(3))
    scout = _scout_summary_from_rows(rows)
    recs = records_from_scout_rows(rows, scout_summary=scout)
    assert len(recs) == 3


def test_duplicate_compaction_collapses_count():
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    recs = records_from_scout_rows((row, row), scout_summary=scout)
    compacted = compact_records(recs)
    assert len(compacted) == 1
    assert compacted[0].count == 2
    assert compacted[0].first_seen_run_id == compacted[0].last_seen_run_id


def test_merge_compacted_runs_increments_count():
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    first = compact_records(records_from_scout_rows((row,), scout_summary=scout))
    second_recs = records_from_scout_rows((row,), scout_summary=scout)
    merged = merge_compacted_runs(first, second_recs)
    assert len(merged) == 1
    assert merged[0].count == 2


def test_blocked_family_cannot_be_candidate_in_summary():
    rows = (_lift_row("gsm8k-train-sample-v1-0003"), _sealed_wrong_row())
    scout = _scout_summary_from_rows(rows)
    report = build_experience_report(scout, include_raw_records=False)
    families = {f["family"]: f for f in report["family_summaries"]}
    blocked_fams = [
        f for f in report["family_summaries"] if f["promotion_status"] == "candidate"
    ]
    for fam in blocked_fams:
        assert fam["blocked_count"] == 0
    assert any(f["promotion_status"] == "blocked_by_wrong_risk" for f in families.values())


def test_experience_report_hash_stable():
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    a = build_experience_report(scout)
    b = build_experience_report(scout)
    assert a["experience_report_hash"] == b["experience_report_hash"]


def test_canonical_json_roundtrip(tmp_path: Path):
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    report = build_experience_report(scout)
    out = tmp_path / "experience.json"
    write_experience_json(report, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["experience_report_hash"] == report["experience_report_hash"]
    compacted = load_compacted_from_report(loaded)
    assert len(compacted) == 1


def test_report_json_mtime_unchanged_by_experience_import():
    before = _REPORT.stat().st_mtime_ns
    _ = compute_record_id
    after = _REPORT.stat().st_mtime_ns
    assert before == after


def test_live_experience_report_determinism():
    a = build_experience_report()
    b = build_experience_report()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_live_serving_wrong_remains_zero_in_experience():
    report = build_experience_report()
    assert report["scout_serving_counts"]["wrong"] == 0


def test_no_floats_in_hashed_payloads():
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    recs = records_from_scout_rows((row,), scout_summary=scout)
    for rec in recs:
        canonical_json(rec.as_dict())


def test_promoted_in_pr_for_served_correct():
    raw = {
        "case_id": "gsm8k-train-sample-v1-0002",
        "question": "Already served",
        "answer_numeric": 18,
        "answer_expression": "#### 18",
    }
    served = _outcome(case_id=raw["case_id"], outcome="correct", actual=18.0, expected=18.0)
    sealed = _outcome(case_id=raw["case_id"], outcome="correct", actual=18.0, expected=18.0)
    row = build_scout_row(raw, served, sealed)
    scout = _scout_summary_from_rows((row,))
    recs = records_from_scout_rows((row,), scout_summary=scout)
    assert len(recs) == 1
    assert recs[0].promotion_status == "promoted_in_pr"


def test_dedupe_key_ignores_run_id():
    row = _lift_row()
    scout = _scout_summary_from_rows((row,))
    cases_by_id = {
        row.case_id: {
            "case_id": row.case_id,
            "answer_expression": "#### 864",
        }
    }
    recs = records_from_scout_rows(
        (row,), scout_summary=scout, cases_by_id=cases_by_id
    )
    key_a = compute_dedupe_key(recs[0])
    op_class = recs[0].arithmetic_chain_signature.split("|")[1]
    rec_b = scout_row_to_experience_record(
        row,
        source_run_id="different-run",
        source_report_hash="different-hash",
        operation_class=op_class,
        category="discrete_count_statement",
        high_freq_joint_families=set(),
    )
    assert rec_b is not None
    assert compute_dedupe_key(rec_b) == key_a


@pytest.fixture
def injected_scout_summary():
    cases = [
        {
            "case_id": "gsm8k-train-sample-v1-0003",
            "question": "Q",
            "answer_numeric": 864,
            "answer_expression": "#### 864",
        },
        {
            "case_id": "gsm8k-train-sample-v1-0011",
            "question": "Q2",
            "answer_numeric": 50,
            "answer_expression": "#### 50",
        },
    ]

    def serving(adapted: dict) -> CaseOutcome:
        if "0003" in adapted["id"]:
            return _outcome(
                case_id=adapted["id"],
                outcome="refused",
                reason=(
                    "candidate_graph: recognizer matched but produced no injection "
                    "(category=discrete_count_statement)"
                ),
                expected=864.0,
            )
        return _outcome(
            case_id=adapted["id"],
            outcome="refused",
            reason="candidate_graph: no admissible candidate for statement",
            expected=50.0,
        )

    def sealed(adapted: dict) -> CaseOutcome:
        if "0003" in adapted["id"]:
            return _outcome(
                case_id=adapted["id"],
                outcome="correct",
                actual=864.0,
                expected=864.0,
            )
        return _outcome(
            case_id=adapted["id"],
            outcome="wrong",
            actual=3200.0,
            expected=50.0,
        )

    return build_scout_summary(
        cases, cases_source="fixture", serving_scorer=serving, sealed_scorer=sealed
    )


def test_injected_scout_adapter_produces_retained_records(injected_scout_summary):
    report = build_experience_report(injected_scout_summary)
    assert report["retained_record_count"] >= 2
    statuses = {r["promotion_status"] for r in report["case_records"]}
    assert "candidate" in statuses
    assert "blocked_by_wrong_risk" in statuses