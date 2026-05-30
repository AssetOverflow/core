"""Manifest parsing and validation for edge/cloud sync artifacts.

This module is pure: it performs no network access and imports no object-store
client.  It validates local manifest dictionaries and optional content bytes
against the artifact authority contract.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from core.sync.artifacts import ArtifactAuthority, ArtifactType, authority_for

SUPPORTED_SCHEMA_VERSION = 1
KNOWN_EPISTEMIC_STATUSES = frozenset({"speculative", "coherent", "contested", "falsified"})


@dataclass(frozen=True, slots=True)
class SyncManifest:
    """Typed view of an edge/cloud sync artifact manifest."""

    schema_version: int
    artifact_id: str
    artifact_type: ArtifactType
    artifact_version: str | None
    content_digest: str | None
    authority: ArtifactAuthority
    default_epistemic_status: str
    admissible_as_evidence: bool
    promotion_required: bool
    signature_present: bool


@dataclass(frozen=True, slots=True)
class ManifestCheck:
    """Result of validating a manifest."""

    accepted: bool
    reason: str
    manifest: SyncManifest | None = None


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _coerce_bool(value: object, *, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _normalize_epistemic_status(value: object) -> str:
    if isinstance(value, str) and value in KNOWN_EPISTEMIC_STATUSES:
        return value
    return "speculative"


def _digest_for(content_bytes: bytes) -> str:
    return "sha256:" + hashlib.sha256(content_bytes).hexdigest()


def parse_manifest(raw: Mapping[str, Any]) -> ManifestCheck:
    """Parse and validate a manifest without checking external content bytes."""

    return validate_manifest(raw, content_bytes=None)


def validate_manifest(
    raw: Mapping[str, Any],
    *,
    content_bytes: bytes | None = None,
    runtime_version: str | None = None,
) -> ManifestCheck:
    """Validate a sync artifact manifest.

    Args:
        raw: Manifest dictionary.
        content_bytes: Optional bytes used to verify the declared content digest.
        runtime_version: Reserved for future semantic compatibility checks.  The
            current contract only checks malformed structural compatibility fields.

    Returns:
        ManifestCheck with stable rejection reasons suitable for tests and audit.
    """

    schema_version = raw.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        return ManifestCheck(False, "unsupported_schema_version")

    artifact_id = raw.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id:
        return ManifestCheck(False, "missing_artifact_id")

    try:
        artifact_type = ArtifactType(raw.get("artifact_type"))
    except ValueError:
        return ManifestCheck(False, "unknown_artifact_type")

    contract_authority = authority_for(artifact_type)
    content = _as_mapping(raw.get("content"))
    content_digest = content.get("digest")
    if content_digest is not None and not isinstance(content_digest, str):
        return ManifestCheck(False, "malformed_content_digest")

    if content_bytes is not None:
        if not content_digest:
            return ManifestCheck(False, "missing_content_digest")
        if _digest_for(content_bytes) != content_digest:
            return ManifestCheck(False, "hash_mismatch")

    declared_authority = _as_mapping(raw.get("authority"))
    runtime_affecting = _coerce_bool(
        declared_authority.get("runtime_affecting"),
        default=contract_authority.runtime_affecting,
    )
    hot_path_allowed = _coerce_bool(
        declared_authority.get("hot_path_allowed"),
        default=contract_authority.hot_path_allowed,
    )
    requires_signature = _coerce_bool(
        declared_authority.get("requires_signature"),
        default=contract_authority.requires_signature,
    )
    requires_activation = _coerce_bool(
        declared_authority.get("requires_activation"),
        default=contract_authority.requires_activation,
    )
    requires_review_or_proof = _coerce_bool(
        declared_authority.get("requires_review_or_proof"),
        default=contract_authority.requires_review_or_proof,
    )

    if runtime_affecting != contract_authority.runtime_affecting:
        return ManifestCheck(False, "authority_profile_weakened")
    if hot_path_allowed or hot_path_allowed != contract_authority.hot_path_allowed:
        return ManifestCheck(False, "authority_profile_weakened")
    if contract_authority.requires_signature and not requires_signature:
        return ManifestCheck(False, "authority_profile_weakened")
    if contract_authority.requires_activation and not requires_activation:
        return ManifestCheck(False, "authority_profile_weakened")
    if contract_authority.requires_review_or_proof and not requires_review_or_proof:
        return ManifestCheck(False, "authority_profile_weakened")

    epistemic = _as_mapping(raw.get("epistemic"))
    default_status = _normalize_epistemic_status(epistemic.get("default_status"))
    admissible_as_evidence = _coerce_bool(
        epistemic.get("admissible_as_evidence"),
        default=contract_authority.admissible_as_evidence,
    )
    promotion_required = _coerce_bool(epistemic.get("promotion_required"), default=True)
    if admissible_as_evidence and not contract_authority.admissible_as_evidence:
        return ManifestCheck(False, "authority_profile_weakened")

    signature = _as_mapping(raw.get("signature"))
    signature_present = bool(signature.get("signature"))
    if contract_authority.requires_signature and not signature_present:
        return ManifestCheck(False, "missing_signature")

    compatibility = _as_mapping(raw.get("compatibility"))
    min_runtime = compatibility.get("min_runtime_version")
    max_runtime = compatibility.get("max_runtime_version")
    if min_runtime is not None and not isinstance(min_runtime, str):
        return ManifestCheck(False, "runtime_incompatible")
    if max_runtime is not None and not isinstance(max_runtime, str):
        return ManifestCheck(False, "runtime_incompatible")
    _ = runtime_version  # Future semantic version comparison hook.

    manifest = SyncManifest(
        schema_version=schema_version,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        artifact_version=raw.get("artifact_version") if isinstance(raw.get("artifact_version"), str) else None,
        content_digest=content_digest,
        authority=contract_authority,
        default_epistemic_status=default_status,
        admissible_as_evidence=admissible_as_evidence,
        promotion_required=promotion_required,
        signature_present=signature_present,
    )
    return ManifestCheck(True, "accepted", manifest)
