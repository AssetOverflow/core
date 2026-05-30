from __future__ import annotations

from core.sync.activation import ActivationLedger
from core.sync.artifacts import ArtifactType
from core.sync.manifest import validate_manifest


def _manifest(artifact_id: str, artifact_type: str, *, signature: str | None = "sig") -> dict:
    raw = {
        "schema_version": 1,
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "artifact_version": "v1",
        "content": {
            "uri": "s3://bucket/path/object.zst",
            "digest": "sha256:test",
        },
        "authority": {},
        "epistemic": {},
        "compatibility": {
            "min_runtime_version": "0.0.0",
            "max_runtime_version": None,
        },
    }
    if signature is not None:
        raw["signature"] = {"signature": signature, "algorithm": "test", "key_id": "test"}
    return raw


def test_downloaded_valid_manifest_is_inert_until_activated() -> None:
    check = validate_manifest(_manifest("pack-v1", ArtifactType.PACK_RELEASE.value))
    assert check.accepted

    ledger = ActivationLedger()
    assert ledger.active_for(ArtifactType.PACK_RELEASE) is None
    assert ledger.audit_log == ()


def test_activation_requires_validated_manifest() -> None:
    ledger = ActivationLedger()
    bad = validate_manifest(_manifest("pack-v1", ArtifactType.PACK_RELEASE.value, signature=None))
    decision = ledger.activate(bad)

    assert not decision.activated
    assert decision.reason == "validation_failed"
    assert ledger.active_for(ArtifactType.PACK_RELEASE) is None
    assert ledger.audit_log == ()


def test_non_runtime_artifact_does_not_activate_but_is_audited() -> None:
    ledger = ActivationLedger()
    check = validate_manifest(_manifest("trace-1", ArtifactType.TRACE.value, signature=None))
    decision = ledger.activate(check)

    assert not decision.activated
    assert decision.reason == "not_runtime_affecting"
    assert ledger.active_for(ArtifactType.TRACE) is None
    assert len(ledger.audit_log) == 1
    assert ledger.audit_log[0].reason == "not_runtime_affecting"


def test_runtime_artifact_activates_after_validation() -> None:
    ledger = ActivationLedger()
    check = validate_manifest(_manifest("pack-v1", ArtifactType.PACK_RELEASE.value))
    decision = ledger.activate(check)

    assert decision.activated
    assert decision.reason == "activated"
    assert decision.previous_artifact_id is None
    assert decision.active_artifact_id == "pack-v1"
    active = ledger.active_for("pack_release")
    assert active is not None
    assert active.artifact_id == "pack-v1"


def test_activation_replaces_previous_release_and_records_previous_id() -> None:
    ledger = ActivationLedger()
    first = validate_manifest(_manifest("pack-v1", ArtifactType.PACK_RELEASE.value))
    second = validate_manifest(_manifest("pack-v2", ArtifactType.PACK_RELEASE.value))

    first_decision = ledger.activate(first)
    second_decision = ledger.activate(second)

    assert first_decision.activated
    assert second_decision.activated
    assert second_decision.previous_artifact_id == "pack-v1"
    assert second_decision.active_artifact_id == "pack-v2"
    assert ledger.active_for(ArtifactType.PACK_RELEASE).artifact_id == "pack-v2"  # type: ignore[union-attr]


def test_activation_does_not_confer_evidence_authority() -> None:
    ledger = ActivationLedger()
    check = validate_manifest(_manifest("policy-v1", ArtifactType.POLICY_RELEASE.value))
    decision = ledger.activate(check)

    assert decision.activated
    assert decision.audit_record is not None
    assert decision.audit_record.default_epistemic_status == "speculative"
    assert not decision.audit_record.admissible_as_evidence


def test_activation_writes_json_serializable_audit_record() -> None:
    ledger = ActivationLedger()
    check = validate_manifest(_manifest("compiler-v1", ArtifactType.MODALITY_COMPILER_RELEASE.value))
    decision = ledger.activate(check)

    assert decision.activated
    audit = ledger.audit_dicts()
    assert len(audit) == 1
    assert audit[0]["artifact_id"] == "compiler-v1"
    assert audit[0]["artifact_type"] == "modality_compiler_release"
    assert audit[0]["reason"] == "activated"
    assert audit[0]["activated"] is True
    assert audit[0]["default_epistemic_status"] == "speculative"
    assert audit[0]["admissible_as_evidence"] is False


def test_rollback_restores_previous_verified_manifest_as_activation_event() -> None:
    ledger = ActivationLedger()
    first = validate_manifest(_manifest("pack-v1", ArtifactType.PACK_RELEASE.value))
    second = validate_manifest(_manifest("pack-v2", ArtifactType.PACK_RELEASE.value))
    assert first.manifest is not None

    ledger.activate(first)
    ledger.activate(second)
    rollback = ledger.rollback(first.manifest)

    assert rollback.activated
    assert rollback.reason == "rollback_activated"
    assert rollback.previous_artifact_id == "pack-v2"
    assert rollback.active_artifact_id == "pack-v1"
    assert ledger.active_for(ArtifactType.PACK_RELEASE).artifact_id == "pack-v1"  # type: ignore[union-attr]
    assert ledger.audit_log[-1].reason == "rollback_activated"
