"""EngineIdentity — L11 Phase 1 (ADR-0220 split).

EngineIdentity is the content-derived sha256 of the engine's ratified personality
substrate (identity / safety / ethics / register / anchor-lens pack files) — the
RATIFIED PACKS ONLY. Content-derived, NOT entropy: same packs -> same identity
(two engines with the same ratified packs ARE the same engine functionally). The
build revision is NOT part of the identity (ADR-0220) — it is provenance. This is
the "who am I" hash the L11 lineage chain and reboot verification build on.
"""

from __future__ import annotations

import pytest

from core.config import DEFAULT_IDENTITY_PACK, RuntimeConfig
from core.engine_identity import (
    RATIFIED_ROLES,
    EngineIdentityError,
    compute_engine_identity,
    compute_legacy_engine_identity,
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
    a = compute_engine_identity(_DEFAULTS)
    b = compute_engine_identity(dict(_DEFAULTS))
    assert a == b  # same substrate -> same identity (cross-engine portable)
    assert len(a) == 64  # sha256 hex


def test_changing_identity_pack_changes_identity() -> None:
    base = compute_engine_identity(_DEFAULTS)
    swapped = compute_engine_identity({**_DEFAULTS, "identity": "precision_first_v1"})
    assert base != swapped  # a different identity pack IS a different identity


def test_code_revision_does_not_change_identity() -> None:
    # ADR-0220: the build revision is NOT an identity input, so a behavior-neutral
    # rebuild is the SAME identity. The packs-only hash takes no revision at all.
    packs_only = compute_engine_identity(_DEFAULTS)
    # The pre-split hash DID fold the revision and varied with it — that behavior
    # now lives ONLY in the legacy helper, retained for migration verification.
    legacy_a = compute_legacy_engine_identity(_DEFAULTS, "rev-a")
    legacy_b = compute_legacy_engine_identity(_DEFAULTS, "rev-b")
    assert legacy_a != legacy_b  # old (removed) behavior: identity flipped per commit
    # The new identity is independent of any revision and differs from both legacy
    # stamps (the scheme genuinely changed the hashed bytes).
    assert packs_only != legacy_a
    assert packs_only != legacy_b


def test_substrate_is_packs_only_no_code_revision() -> None:
    substrate = ratified_substrate(_DEFAULTS)
    # ADR-0220: the hashed tuple is EXACTLY the ratified roles — no code_revision.
    assert set(substrate.keys()) == set(RATIFIED_ROLES)
    assert "code_revision" not in substrate
    # Each role records its pack id + a 64-hex content hash of the pack file.
    for role in RATIFIED_ROLES:
        assert substrate[role]["pack_id"] == _DEFAULTS[role]
        assert len(substrate[role]["sha256"]) == 64
    # Distinct packs have distinct content hashes.
    assert substrate["identity"]["sha256"] != substrate["safety"]["sha256"]


def test_legacy_hash_reproduces_pre_split_value_and_folds_revision() -> None:
    # The legacy helper must byte-exactly reproduce the pre-split formula
    # (packs + code_revision) so a legacy stamp can be reconstructed & verified.
    substrate = ratified_substrate(_DEFAULTS)
    substrate["code_revision"] = "abc123"
    import hashlib
    import json

    expected = hashlib.sha256(
        json.dumps(
            substrate, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    assert compute_legacy_engine_identity(_DEFAULTS, "abc123") == expected


def test_missing_ratified_pack_raises() -> None:
    with pytest.raises(EngineIdentityError):
        compute_engine_identity({**_DEFAULTS, "identity": "no_such_pack_xyz"})


def test_engine_identity_for_config_resolves_defaults() -> None:
    # An empty config resolves every role to its DEFAULT pack.
    from_config = engine_identity_for_config(RuntimeConfig())
    explicit = compute_engine_identity(_DEFAULTS)
    assert from_config == explicit


def test_engine_identity_for_config_honors_identity_override() -> None:
    base = engine_identity_for_config(RuntimeConfig())
    override = engine_identity_for_config(RuntimeConfig(identity_pack="precision_first_v1"))
    assert base != override
    assert DEFAULT_IDENTITY_PACK == "default_general_v1"  # sanity on the default
