"""EngineIdentity — L11 Phase 1.

EngineIdentity is the content-derived sha256 of the engine's ratified personality
substrate (identity / safety / ethics / register / anchor-lens pack files) plus
the code revision. Content-derived, NOT entropy: same substrate -> same identity
(two engines with the same ratified packs ARE the same engine functionally).
This is the "who am I" hash the L11 lineage chain and reboot verification build on.
"""

from __future__ import annotations

import pytest

from core.config import DEFAULT_IDENTITY_PACK, RuntimeConfig
from core.engine_identity import (
    RATIFIED_ROLES,
    EngineIdentityError,
    compute_engine_identity,
    engine_identity_for_config,
    ratified_substrate,
)

_DEFAULTS: dict[str, str] = {
    "identity": "default_general_v1",
    "safety": "core_safety_axes_v1",
    "ethics": "default_general_ethics_v1",
    "register": "default_neutral_v1",
    "anchor_lens": "default_unanchored_v1",
}


def test_engine_identity_is_deterministic_and_content_derived() -> None:
    a = compute_engine_identity(_DEFAULTS, git_revision="abc123")
    b = compute_engine_identity(dict(_DEFAULTS), git_revision="abc123")
    assert a == b  # same substrate -> same identity (cross-engine portable)
    assert len(a) == 64  # sha256 hex


def test_changing_identity_pack_changes_identity() -> None:
    base = compute_engine_identity(_DEFAULTS, git_revision="abc123")
    swapped = compute_engine_identity(
        {**_DEFAULTS, "identity": "precision_first_v1"}, git_revision="abc123"
    )
    assert base != swapped  # a different identity pack IS a different identity


def test_changing_code_revision_changes_identity() -> None:
    a = compute_engine_identity(_DEFAULTS, git_revision="rev-a")
    b = compute_engine_identity(_DEFAULTS, git_revision="rev-b")
    assert a != b


def test_substrate_exposes_per_role_pack_content_hashes() -> None:
    substrate = ratified_substrate(_DEFAULTS, git_revision="abc123")
    assert set(RATIFIED_ROLES).issubset(substrate.keys())
    assert substrate["code_revision"] == "abc123"
    # Each role records its pack id + a 64-hex content hash of the pack file.
    for role in RATIFIED_ROLES:
        assert substrate[role]["pack_id"] == _DEFAULTS[role]
        assert len(substrate[role]["sha256"]) == 64
    # Distinct packs have distinct content hashes.
    assert substrate["identity"]["sha256"] != substrate["safety"]["sha256"]


def test_missing_ratified_pack_raises() -> None:
    with pytest.raises(EngineIdentityError):
        compute_engine_identity(
            {**_DEFAULTS, "identity": "no_such_pack_xyz"}, git_revision="abc123"
        )


def test_engine_identity_for_config_resolves_defaults() -> None:
    # An empty config resolves every role to its DEFAULT pack.
    from_config = engine_identity_for_config(RuntimeConfig(), git_revision="abc123")
    explicit = compute_engine_identity(_DEFAULTS, git_revision="abc123")
    assert from_config == explicit


def test_engine_identity_for_config_honors_identity_override() -> None:
    base = engine_identity_for_config(RuntimeConfig(), git_revision="abc123")
    override = engine_identity_for_config(
        RuntimeConfig(identity_pack="precision_first_v1"), git_revision="abc123"
    )
    assert base != override
    assert DEFAULT_IDENTITY_PACK == "default_general_v1"  # sanity on the default
