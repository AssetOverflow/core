"""Tier-2 reasoning evidence spine tests."""

from __future__ import annotations

import dataclasses
import json

import pytest

from core.contemplation.miners.learning_arena import mine_learning_arena_report
from core.reasoning import (
    COMMITMENT_DISAGREEMENT,
    DUPLICATE_STRUCTURAL_SIGNATURE,
    MISSING_COMMITMENT,
    TIER2_VERIFIED,
    EvidenceBundle,
    OperatorEvidence,
    verify_tier2_agreement,
)


def _ev(
    *,
    signature: str = "shape-a",
    commitment: str = "answer:42",
    outcome: str = "verified",
) -> OperatorEvidence:
    return OperatorEvidence(
        domain="mathematics_logic",
        operator="unit_test_operator",
        outcome=outcome,
        reason="test",
        input_keys=("input-a",),
        check_keys=("check-a",),
        commitment_key=commitment,
        structural_signature=signature,
        payload={"nested": {"values": [1, 2, "x"]}},
    )


def test_operator_evidence_is_frozen_and_payload_is_immutable() -> None:
    ev = _ev()
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.domain = "mutated"  # type: ignore[misc]
    with pytest.raises(TypeError):
        ev.payload["nested"] = {}  # type: ignore[index]


def test_canonical_json_and_hash_are_deterministic() -> None:
    ev1 = _ev()
    ev2 = _ev()
    assert ev1.canonical_json() == ev2.canonical_json()
    assert ev1.evidence_hash == ev2.evidence_hash
    assert json.loads(ev1.canonical_json())["payload"]["nested"]["values"] == [1, 2, "x"]


def test_evidence_bundle_hash_is_ordered_and_stable() -> None:
    bundle = EvidenceBundle((_ev(signature="a"), _ev(signature="b")))
    same = EvidenceBundle((_ev(signature="a"), _ev(signature="b")))
    swapped = EvidenceBundle((_ev(signature="b"), _ev(signature="a")))
    assert bundle.evidence_hash == same.evidence_hash
    assert bundle.evidence_hash != swapped.evidence_hash


def test_tier2_verifies_two_distinct_structures_same_commitment() -> None:
    verdict = verify_tier2_agreement((
        _ev(signature="shape-a"),
        _ev(signature="shape-b"),
    ))
    assert verdict.verified is True
    assert verdict.reason == TIER2_VERIFIED
    assert verdict.commitment_key == "answer:42"
    assert verdict.structural_signatures == ("shape-a", "shape-b")


def test_tier2_refuses_duplicate_signature() -> None:
    verdict = verify_tier2_agreement((
        _ev(signature="same"),
        _ev(signature="same"),
    ))
    assert verdict.verified is False
    assert verdict.reason == DUPLICATE_STRUCTURAL_SIGNATURE


def test_tier2_refuses_disagreeing_commitments() -> None:
    verdict = verify_tier2_agreement((
        _ev(signature="shape-a", commitment="answer:42"),
        _ev(signature="shape-b", commitment="answer:41"),
    ))
    assert verdict.verified is False
    assert verdict.reason == COMMITMENT_DISAGREEMENT


def test_tier2_refuses_missing_commitment() -> None:
    verdict = verify_tier2_agreement((
        _ev(signature="shape-a", commitment=""),
        _ev(signature="shape-b", commitment="answer:42"),
    ))
    assert verdict.verified is False
    assert verdict.reason == MISSING_COMMITMENT


def test_learning_arena_miner_emits_speculative_findings(tmp_path) -> None:
    report = {
        "per_class": {
            "alpha": {
                "committed": 2,
                "coverage": 0.2,
                "t2_verified": 0,
            }
        },
        "elimination_records": [
            {
                "case_id": "c-wrong",
                "class_name": "alpha",
                "gold": 10.0,
                "reason": "answer mismatch",
            }
        ],
    }
    path = tmp_path / "learning_report.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    findings = mine_learning_arena_report(path, substrate_hash="substrate")

    predicates = {finding.predicate for finding in findings}
    assert predicates == {"weak_coverage", "missing_tier2_evidence", "wrong_attempt"}
    assert all(finding.epistemic_status.value == "speculative" for finding in findings)
