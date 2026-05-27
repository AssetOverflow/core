"""Tests for ADR-0167 W2-A — audit-to-evidence adapter."""

from __future__ import annotations

import json
from pathlib import Path

from generate.comprehension.audit import AuditRow
from teaching.math_contemplation import audit_problem_to_evidence, audit_to_evidence
from teaching.math_evidence import SUB_TYPE_FOR_OPERATOR


def _row_from_artifact_case(case: dict[str, object]) -> AuditRow:
    return AuditRow(
        case_id=str(case["case_id"]),
        sentence_index=int(case["sentence_index"]),
        token_index=int(case["token_index"]),
        token_text=str(case["token_text"]),
        recognized_terms=tuple(str(t) for t in case["recognized_terms"]),
        skipped_frame=(
            None
            if case["skipped_frame"] is None
            else str(case["skipped_frame"])
        ),
        missing_operator=(
            None
            if case["missing_operator"] is None
            else str(case["missing_operator"])
        ),
        refusal_reason=str(case["refusal_reason"]),
        refusal_detail=str(case["refusal_detail"]),
    )


def _load_artifact_rows() -> list[AuditRow]:
    artifact = json.loads(
        Path("evals/gsm8k_math/train_sample/v1/audit_brief_11.json").read_text()
    )
    return [_row_from_artifact_case(case) for case in artifact["per_case"]]


def test_adapter_round_trips_full_audit_artifact() -> None:
    rows = _load_artifact_rows()
    out = audit_to_evidence(rows)
    expected = sum(1 for row in rows if row.missing_operator is not None)
    assert len(out) == expected


def test_adapter_is_deterministic() -> None:
    rows = _load_artifact_rows()
    baseline = audit_to_evidence(rows)
    for _ in range(10):
        assert audit_to_evidence(rows) == baseline


def test_skips_none_operator_rows() -> None:
    rows = [
        AuditRow(
            case_id="a",
            sentence_index=0,
            token_index=0,
            token_text="?",
            recognized_terms=(),
            skipped_frame=None,
            missing_operator=None,
            refusal_reason="no_question_target",
            refusal_detail="none",
        )
    ]
    assert audit_to_evidence(rows) == ()


def test_every_missing_operator_maps_to_a_sub_type() -> None:
    rows = _load_artifact_rows()
    for row in rows:
        if row.missing_operator is not None:
            assert row.missing_operator in SUB_TYPE_FOR_OPERATOR
    assert len(audit_to_evidence(rows)) > 0


def test_evidence_hashes_distinct_across_cases() -> None:
    row1 = AuditRow(
        case_id="case-1",
        sentence_index=0,
        token_index=0,
        token_text="crayons",
        recognized_terms=("She", "has"),
        skipped_frame="descriptive_frame",
        missing_operator="lexicon_entry",
        refusal_reason="unknown_word",
        refusal_detail="no primitive or lexicon match for 'crayons'",
    )
    row2 = AuditRow(
        case_id="case-2",
        sentence_index=0,
        token_index=0,
        token_text="crayons",
        recognized_terms=("She", "has"),
        skipped_frame="descriptive_frame",
        missing_operator="lexicon_entry",
        refusal_reason="unknown_word",
        refusal_detail="no primitive or lexicon match for 'crayons'",
    )
    out1 = audit_to_evidence([row1])[0]
    out2 = audit_to_evidence([row2])[0]
    assert out1.evidence_hash != out2.evidence_hash


def test_empty_audit_returns_empty_tuple() -> None:
    assert audit_to_evidence([]) == ()


def test_adapter_preserves_input_order() -> None:
    rows = [
        AuditRow(
            case_id="x-1",
            sentence_index=0,
            token_index=1,
            token_text="a",
            recognized_terms=("one",),
            skipped_frame="initial_state",
            missing_operator="lexicon_entry",
            refusal_reason="unknown_word",
            refusal_detail="a",
        ),
        AuditRow(
            case_id="x-2",
            sentence_index=1,
            token_index=2,
            token_text="b",
            recognized_terms=("two",),
            skipped_frame="operation_frame",
            missing_operator="question_target_slot",
            refusal_reason="no_question_target",
            refusal_detail="b",
        ),
    ]
    out = audit_to_evidence(rows)
    assert [ev.case_id for ev in out] == ["x-1", "x-2"]


def test_audit_problem_to_evidence_round_trip() -> None:
    out = audit_problem_to_evidence(
        "Tom opens an amusement park. How many days?",
        case_id="probe",
    )
    assert len(out) >= 1
    assert all(ev.case_id == "probe" for ev in out)
