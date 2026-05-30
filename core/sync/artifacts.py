"""Artifact authority model for edge/cloud synchronization.

The model is pure and has no object-store dependency.  It encodes the
contract from docs/architecture/edge-sync-artifact-contract.md so tests
can prove that storage, signature, activation, and evidence authority
remain separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ArtifactType(str, Enum):
    """Closed artifact classes allowed at the edge/cloud boundary."""

    TRACE = "trace"
    REPLAY_BUNDLE = "replay_bundle"
    SEALED_EVAL_RESULT = "sealed_eval_result"
    FLEET_OBSERVATION_BATCH = "fleet_observation_batch"
    CURRICULUM_BUNDLE = "curriculum_bundle"
    PACK_RELEASE = "pack_release"
    POLICY_RELEASE = "policy_release"
    MODALITY_COMPILER_RELEASE = "modality_compiler_release"
    COLD_VAULT_SNAPSHOT = "cold_vault_snapshot"


@dataclass(frozen=True, slots=True)
class ArtifactAuthority:
    """Authority profile for one artifact class.

    These fields are intentionally independent.  A signed artifact may
    prove integrity without becoming evidence; an activated artifact may
    participate in runtime behavior without making every contained claim
    coherent.
    """

    runtime_affecting: bool
    hot_path_allowed: bool
    requires_signature: bool
    requires_activation: bool
    requires_review_or_proof: bool
    default_epistemic_status: str
    admissible_as_evidence: bool


ARTIFACT_AUTHORITY: dict[ArtifactType, ArtifactAuthority] = {
    ArtifactType.TRACE: ArtifactAuthority(
        runtime_affecting=False,
        hot_path_allowed=False,
        requires_signature=False,
        requires_activation=False,
        requires_review_or_proof=False,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
    ArtifactType.REPLAY_BUNDLE: ArtifactAuthority(
        runtime_affecting=False,
        hot_path_allowed=False,
        requires_signature=False,
        requires_activation=False,
        requires_review_or_proof=False,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
    ArtifactType.SEALED_EVAL_RESULT: ArtifactAuthority(
        runtime_affecting=False,
        hot_path_allowed=False,
        requires_signature=False,
        requires_activation=False,
        requires_review_or_proof=True,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
    ArtifactType.FLEET_OBSERVATION_BATCH: ArtifactAuthority(
        runtime_affecting=False,
        hot_path_allowed=False,
        requires_signature=False,
        requires_activation=False,
        requires_review_or_proof=True,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
    ArtifactType.CURRICULUM_BUNDLE: ArtifactAuthority(
        runtime_affecting=False,
        hot_path_allowed=False,
        requires_signature=True,
        requires_activation=False,
        requires_review_or_proof=True,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
    ArtifactType.PACK_RELEASE: ArtifactAuthority(
        runtime_affecting=True,
        hot_path_allowed=False,
        requires_signature=True,
        requires_activation=True,
        requires_review_or_proof=True,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
    ArtifactType.POLICY_RELEASE: ArtifactAuthority(
        runtime_affecting=True,
        hot_path_allowed=False,
        requires_signature=True,
        requires_activation=True,
        requires_review_or_proof=True,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
    ArtifactType.MODALITY_COMPILER_RELEASE: ArtifactAuthority(
        runtime_affecting=True,
        hot_path_allowed=False,
        requires_signature=True,
        requires_activation=True,
        requires_review_or_proof=True,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
    ArtifactType.COLD_VAULT_SNAPSHOT: ArtifactAuthority(
        runtime_affecting=True,
        hot_path_allowed=False,
        requires_signature=True,
        requires_activation=True,
        requires_review_or_proof=True,
        default_epistemic_status="speculative",
        admissible_as_evidence=False,
    ),
}


def authority_for(artifact_type: ArtifactType | str) -> ArtifactAuthority:
    """Return the authority profile for an artifact type.

    Raises:
        ValueError: if the artifact type is unknown.
    """

    try:
        normalized = artifact_type if isinstance(artifact_type, ArtifactType) else ArtifactType(artifact_type)
    except ValueError as exc:
        raise ValueError(f"unknown artifact type: {artifact_type!r}") from exc
    return ARTIFACT_AUTHORITY[normalized]
