"""Activation ledger for verified edge/cloud sync artifacts.

Activation is separate from download, validation, signature integrity, and
epistemic admissibility.  This module is pure and performs no object-store I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.sync.artifacts import ArtifactType
from core.sync.manifest import ManifestCheck, SyncManifest


@dataclass(frozen=True, slots=True)
class ActivationRecord:
    """Audit metadata for one activation decision."""

    artifact_id: str
    artifact_type: ArtifactType
    artifact_version: str | None
    content_digest: str | None
    previous_artifact_id: str | None
    active_artifact_id: str | None
    reason: str
    activated: bool
    default_epistemic_status: str
    admissible_as_evidence: bool


@dataclass(frozen=True, slots=True)
class ActivationDecision:
    """Result of an activation attempt."""

    activated: bool
    reason: str
    previous_artifact_id: str | None = None
    active_artifact_id: str | None = None
    audit_record: ActivationRecord | None = None


@dataclass(slots=True)
class ActivationLedger:
    """Tracks active runtime-affecting artifacts by artifact class.

    The ledger only activates manifests that already passed validation.  It does
    not interpret artifact contents and does not promote any claim to coherent.
    """

    _active: dict[ArtifactType, SyncManifest] = field(default_factory=dict)
    _audit_log: list[ActivationRecord] = field(default_factory=list)

    def active_for(self, artifact_type: ArtifactType | str) -> SyncManifest | None:
        """Return the active manifest for an artifact class, if any."""

        normalized = artifact_type if isinstance(artifact_type, ArtifactType) else ArtifactType(artifact_type)
        return self._active.get(normalized)

    @property
    def audit_log(self) -> tuple[ActivationRecord, ...]:
        """Immutable view of activation audit records."""

        return tuple(self._audit_log)

    def activate(self, check: ManifestCheck) -> ActivationDecision:
        """Activate a validated runtime-affecting manifest.

        A successful validation is required, but validation alone does not change
        active state.  Non-runtime artifacts are intentionally not activated.
        """

        if not check.accepted or check.manifest is None:
            return ActivationDecision(False, "validation_failed")

        manifest = check.manifest
        if not manifest.authority.runtime_affecting:
            record = self._record_for(
                manifest,
                activated=False,
                reason="not_runtime_affecting",
                previous=None,
                active=None,
            )
            self._audit_log.append(record)
            return ActivationDecision(
                False,
                "not_runtime_affecting",
                audit_record=record,
            )

        if manifest.authority.requires_activation is False:
            record = self._record_for(
                manifest,
                activated=False,
                reason="activation_not_required",
                previous=None,
                active=None,
            )
            self._audit_log.append(record)
            return ActivationDecision(
                False,
                "activation_not_required",
                audit_record=record,
            )

        previous = self._active.get(manifest.artifact_type)
        previous_id = previous.artifact_id if previous is not None else None
        self._active[manifest.artifact_type] = manifest
        record = self._record_for(
            manifest,
            activated=True,
            reason="activated",
            previous=previous_id,
            active=manifest.artifact_id,
        )
        self._audit_log.append(record)
        return ActivationDecision(
            True,
            "activated",
            previous_artifact_id=previous_id,
            active_artifact_id=manifest.artifact_id,
            audit_record=record,
        )

    def rollback(self, manifest: SyncManifest) -> ActivationDecision:
        """Restore a previously verified manifest as the active release.

        Rollback still records an activation event and still does not confer
        epistemic admissibility.
        """

        if not manifest.authority.runtime_affecting:
            return ActivationDecision(False, "not_runtime_affecting")
        previous = self._active.get(manifest.artifact_type)
        previous_id = previous.artifact_id if previous is not None else None
        self._active[manifest.artifact_type] = manifest
        record = self._record_for(
            manifest,
            activated=True,
            reason="rollback_activated",
            previous=previous_id,
            active=manifest.artifact_id,
        )
        self._audit_log.append(record)
        return ActivationDecision(
            True,
            "rollback_activated",
            previous_artifact_id=previous_id,
            active_artifact_id=manifest.artifact_id,
            audit_record=record,
        )

    def _record_for(
        self,
        manifest: SyncManifest,
        *,
        activated: bool,
        reason: str,
        previous: str | None,
        active: str | None,
    ) -> ActivationRecord:
        return ActivationRecord(
            artifact_id=manifest.artifact_id,
            artifact_type=manifest.artifact_type,
            artifact_version=manifest.artifact_version,
            content_digest=manifest.content_digest,
            previous_artifact_id=previous,
            active_artifact_id=active,
            reason=reason,
            activated=activated,
            default_epistemic_status=manifest.default_epistemic_status,
            admissible_as_evidence=manifest.admissible_as_evidence,
        )

    def audit_dicts(self) -> tuple[dict[str, Any], ...]:
        """Return JSON-serializable audit records."""

        return tuple(
            {
                "artifact_id": record.artifact_id,
                "artifact_type": record.artifact_type.value,
                "artifact_version": record.artifact_version,
                "content_digest": record.content_digest,
                "previous_artifact_id": record.previous_artifact_id,
                "active_artifact_id": record.active_artifact_id,
                "reason": record.reason,
                "activated": record.activated,
                "default_epistemic_status": record.default_epistemic_status,
                "admissible_as_evidence": record.admissible_as_evidence,
            }
            for record in self._audit_log
        )
