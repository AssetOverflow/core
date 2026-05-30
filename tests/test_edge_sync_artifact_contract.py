from __future__ import annotations

import pytest

from core.sync.artifacts import ARTIFACT_AUTHORITY, ArtifactAuthority, ArtifactType, authority_for


def test_artifact_authority_profiles_are_closed() -> None:
    assert set(ARTIFACT_AUTHORITY) == set(ArtifactType)
    assert all(isinstance(profile, ArtifactAuthority) for profile in ARTIFACT_AUTHORITY.values())


def test_no_edge_sync_artifact_is_hot_path_allowed() -> None:
    assert all(not profile.hot_path_allowed for profile in ARTIFACT_AUTHORITY.values())


def test_runtime_affecting_artifacts_require_signature_and_activation() -> None:
    runtime_affecting = {
        ArtifactType.PACK_RELEASE,
        ArtifactType.POLICY_RELEASE,
        ArtifactType.MODALITY_COMPILER_RELEASE,
        ArtifactType.COLD_VAULT_SNAPSHOT,
    }
    for artifact_type in runtime_affecting:
        profile = authority_for(artifact_type)
        assert profile.runtime_affecting
        assert profile.requires_signature
        assert profile.requires_activation
        assert profile.requires_review_or_proof


def test_non_runtime_artifacts_do_not_gain_evidence_authority() -> None:
    non_runtime = {
        ArtifactType.TRACE,
        ArtifactType.REPLAY_BUNDLE,
        ArtifactType.SEALED_EVAL_RESULT,
        ArtifactType.FLEET_OBSERVATION_BATCH,
    }
    for artifact_type in non_runtime:
        profile = authority_for(artifact_type)
        assert not profile.runtime_affecting
        assert not profile.admissible_as_evidence
        assert profile.default_epistemic_status == "speculative"


def test_signed_does_not_imply_evidence() -> None:
    signed_artifact_types = [
        artifact_type
        for artifact_type, profile in ARTIFACT_AUTHORITY.items()
        if profile.requires_signature
    ]
    assert signed_artifact_types
    for artifact_type in signed_artifact_types:
        profile = authority_for(artifact_type)
        assert not profile.admissible_as_evidence


def test_fleet_observations_default_speculative_and_require_review() -> None:
    profile = authority_for("fleet_observation_batch")
    assert profile.default_epistemic_status == "speculative"
    assert profile.requires_review_or_proof
    assert not profile.admissible_as_evidence
    assert not profile.runtime_affecting


def test_unknown_artifact_type_rejects() -> None:
    with pytest.raises(ValueError, match="unknown artifact type"):
        authority_for("cloud_says_this_is_true")
