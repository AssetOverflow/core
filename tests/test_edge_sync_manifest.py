from __future__ import annotations

import hashlib

from core.sync.artifacts import ArtifactType
from core.sync.manifest import validate_manifest


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _manifest(
    artifact_type: str = ArtifactType.TRACE.value,
    *,
    signature: str | None = None,
    content_digest: str | None = None,
    authority: dict | None = None,
    epistemic: dict | None = None,
) -> dict:
    raw: dict = {
        "schema_version": 1,
        "artifact_id": "artifact-1",
        "artifact_type": artifact_type,
        "artifact_version": "v1",
        "content": {
            "uri": "s3://bucket/path/object.jsonl.zst",
        },
        "authority": authority or {},
        "epistemic": epistemic or {},
        "compatibility": {
            "min_runtime_version": "0.0.0",
            "max_runtime_version": None,
        },
    }
    if content_digest is not None:
        raw["content"]["digest"] = content_digest
    if signature is not None:
        raw["signature"] = {"signature": signature, "algorithm": "test", "key_id": "test"}
    return raw


def test_trace_manifest_accepts_without_signature() -> None:
    check = validate_manifest(_manifest())
    assert check.accepted
    assert check.reason == "accepted"
    assert check.manifest is not None
    assert check.manifest.artifact_type is ArtifactType.TRACE
    assert check.manifest.default_epistemic_status == "speculative"
    assert not check.manifest.admissible_as_evidence


def test_runtime_affecting_manifest_requires_signature() -> None:
    check = validate_manifest(_manifest(ArtifactType.PACK_RELEASE.value))
    assert not check.accepted
    assert check.reason == "missing_signature"


def test_runtime_affecting_manifest_accepts_with_signature() -> None:
    check = validate_manifest(
        _manifest(ArtifactType.PACK_RELEASE.value, signature="signed-by-release-key")
    )
    assert check.accepted
    assert check.manifest is not None
    assert check.manifest.signature_present
    assert check.manifest.artifact_type is ArtifactType.PACK_RELEASE


def test_unknown_artifact_type_rejects() -> None:
    check = validate_manifest(_manifest("cloud_says_true"))
    assert not check.accepted
    assert check.reason == "unknown_artifact_type"


def test_unsupported_schema_version_rejects() -> None:
    raw = _manifest()
    raw["schema_version"] = 999
    check = validate_manifest(raw)
    assert not check.accepted
    assert check.reason == "unsupported_schema_version"


def test_hash_mismatch_rejects() -> None:
    check = validate_manifest(
        _manifest(content_digest=_digest(b"expected")),
        content_bytes=b"actual",
    )
    assert not check.accepted
    assert check.reason == "hash_mismatch"


def test_hash_match_accepts() -> None:
    payload = b"trace bytes"
    check = validate_manifest(
        _manifest(content_digest=_digest(payload)),
        content_bytes=payload,
    )
    assert check.accepted


def test_missing_digest_rejects_when_content_bytes_supplied() -> None:
    check = validate_manifest(_manifest(), content_bytes=b"payload")
    assert not check.accepted
    assert check.reason == "missing_content_digest"


def test_manifest_cannot_claim_hot_path_authority() -> None:
    check = validate_manifest(_manifest(authority={"hot_path_allowed": True}))
    assert not check.accepted
    assert check.reason == "authority_profile_weakened"


def test_manifest_cannot_disable_required_signature() -> None:
    check = validate_manifest(
        _manifest(
            ArtifactType.PACK_RELEASE.value,
            authority={"requires_signature": False},
        )
    )
    assert not check.accepted
    assert check.reason == "authority_profile_weakened"


def test_manifest_cannot_make_fleet_observations_evidence() -> None:
    check = validate_manifest(
        _manifest(
            ArtifactType.FLEET_OBSERVATION_BATCH.value,
            epistemic={"admissible_as_evidence": True},
        )
    )
    assert not check.accepted
    assert check.reason == "authority_profile_weakened"


def test_malformed_epistemic_status_defaults_speculative() -> None:
    check = validate_manifest(_manifest(epistemic={"default_status": "institutionally_certified"}))
    assert check.accepted
    assert check.manifest is not None
    assert check.manifest.default_epistemic_status == "speculative"


def test_malformed_compatibility_rejects() -> None:
    raw = _manifest()
    raw["compatibility"] = {"min_runtime_version": 123}
    check = validate_manifest(raw)
    assert not check.accepted
    assert check.reason == "runtime_incompatible"
