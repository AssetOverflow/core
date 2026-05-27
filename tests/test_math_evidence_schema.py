"""Tests for ADR-0167 W1-A — MathReaderRefusalEvidence schema + canonical-bytes."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from generate.comprehension.audit import AuditRow, audit_problem
from teaching.math_evidence import (
    MathReaderRefusalEvidence,
    SUB_TYPE_FOR_OPERATOR,
    from_audit_row,
)

# ---------------------------------------------------------------------------
# Fixture: a concrete AuditRow for reuse
# ---------------------------------------------------------------------------

_SAMPLE_ROW = AuditRow(
    case_id="test-001",
    sentence_index=0,
    token_index=3,
    token_text="hefty",
    recognized_terms=("James", "has", "5"),
    skipped_frame="initial_state",
    missing_operator="lexicon_entry",
    refusal_reason="unknown_word",
    refusal_detail="unknown word: hefty",
)


# ---------------------------------------------------------------------------
# test_evidence_is_frozen
# ---------------------------------------------------------------------------


def test_evidence_is_frozen() -> None:
    ev = from_audit_row(_SAMPLE_ROW, "lexical")
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.case_id = "mutated"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.evidence_hash = "mutated"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.sub_type = "frame"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# test_canonical_bytes_deterministic
# ---------------------------------------------------------------------------


def test_canonical_bytes_deterministic() -> None:
    ev1 = from_audit_row(_SAMPLE_ROW, "lexical")
    ev2 = from_audit_row(_SAMPLE_ROW, "lexical")
    assert ev1.to_canonical_bytes() == ev2.to_canonical_bytes()


# ---------------------------------------------------------------------------
# test_evidence_hash_matches_canonical_bytes
# ---------------------------------------------------------------------------


def test_evidence_hash_matches_canonical_bytes() -> None:
    ev = from_audit_row(_SAMPLE_ROW, "lexical")
    expected = hashlib.sha256(ev.to_canonical_bytes()).hexdigest()
    assert ev.evidence_hash == expected


# ---------------------------------------------------------------------------
# test_evidence_hash_excludes_itself
# ---------------------------------------------------------------------------


def test_evidence_hash_excludes_itself() -> None:
    ev = from_audit_row(_SAMPLE_ROW, "lexical")
    canonical_before = ev.to_canonical_bytes()
    object.__setattr__(ev, "evidence_hash", "tampered")
    canonical_after = ev.to_canonical_bytes()
    assert canonical_before == canonical_after


# ---------------------------------------------------------------------------
# test_sub_type_table_covers_all_missing_operators
# ---------------------------------------------------------------------------


def test_sub_type_table_covers_all_missing_operators() -> None:
    artifact_path = Path(
        "evals/gsm8k_math/train_sample/v1/audit_brief_11.json"
    )
    data = json.loads(artifact_path.read_text())
    operators_in_artifact: set[str] = set()
    for case in data["per_case"]:
        op = case.get("missing_operator")
        if op is not None:
            operators_in_artifact.add(op)
    assert operators_in_artifact, "artifact has no missing_operator values"
    missing = operators_in_artifact - set(SUB_TYPE_FOR_OPERATOR)
    assert not missing, f"operators not in SUB_TYPE_FOR_OPERATOR: {sorted(missing)}"


# ---------------------------------------------------------------------------
# test_sub_type_table_covers_live_audit (against cases.jsonl)
# ---------------------------------------------------------------------------


def test_sub_type_table_covers_live_audit() -> None:
    cases_path = Path("evals/gsm8k_math/train_sample/v1/cases.jsonl")
    operators_found: set[str] = set()
    for line in cases_path.read_text().splitlines():
        c = json.loads(line)
        _result, rows = audit_problem(c["question"], case_id=c["case_id"])
        for row in rows:
            if row.missing_operator is not None:
                operators_found.add(row.missing_operator)
                assert row.missing_operator in SUB_TYPE_FOR_OPERATOR, (
                    f"live audit operator {row.missing_operator!r} "
                    f"not in SUB_TYPE_FOR_OPERATOR"
                )
    assert operators_found, "no refusals found in live audit — data may have changed"


# ---------------------------------------------------------------------------
# test_distinct_sub_types_have_distinct_hashes
# ---------------------------------------------------------------------------


def test_distinct_sub_types_have_distinct_hashes() -> None:
    ev_lexical = from_audit_row(_SAMPLE_ROW, "lexical")
    ev_frame = from_audit_row(_SAMPLE_ROW, "frame")
    assert ev_lexical.evidence_hash != ev_frame.evidence_hash
    assert ev_lexical.to_canonical_bytes() != ev_frame.to_canonical_bytes()


# ---------------------------------------------------------------------------
# test_from_audit_row_factory
# ---------------------------------------------------------------------------


def test_from_audit_row_factory() -> None:
    ev = from_audit_row(_SAMPLE_ROW, "lexical")
    assert ev.case_id == _SAMPLE_ROW.case_id
    assert ev.sentence_index == _SAMPLE_ROW.sentence_index
    assert ev.token_index == _SAMPLE_ROW.token_index
    assert ev.refusal_reason == _SAMPLE_ROW.refusal_reason
    assert ev.missing_operator == _SAMPLE_ROW.missing_operator
    assert ev.audit_row is _SAMPLE_ROW
    assert ev.sub_type == "lexical"
    assert isinstance(ev.evidence_hash, str)
    assert len(ev.evidence_hash) == 64  # sha256 hex


# ---------------------------------------------------------------------------
# test_claim_signature_default_empty_in_w1a
# ---------------------------------------------------------------------------


def test_claim_signature_default_empty_in_w1a() -> None:
    ev = from_audit_row(_SAMPLE_ROW, "lexical")
    assert ev.claim_signature == ""


# ---------------------------------------------------------------------------
# test_determinism_across_n_builds
# ---------------------------------------------------------------------------


def test_determinism_across_n_builds() -> None:
    hashes = {from_audit_row(_SAMPLE_ROW, "lexical").evidence_hash for _ in range(20)}
    assert len(hashes) == 1, f"non-deterministic hashes: {hashes}"


# ---------------------------------------------------------------------------
# test_from_audit_row_with_none_missing_operator
# ---------------------------------------------------------------------------


def test_from_audit_row_with_none_missing_operator() -> None:
    row = AuditRow(
        case_id="test-nil",
        sentence_index=1,
        token_index=0,
        token_text="?",
        recognized_terms=(),
        skipped_frame=None,
        missing_operator=None,
        refusal_reason="no_question_target",
        refusal_detail="no target found",
    )
    ev = from_audit_row(row, "slot")
    assert ev.missing_operator is None
    canonical = json.loads(ev.to_canonical_bytes())
    assert "missing_operator" not in canonical
