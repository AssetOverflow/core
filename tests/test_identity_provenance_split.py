"""ADR-0220 — identity/provenance split: the new invariants and the migration.

Proves the four behavioural claims the split introduces (the in-process reboot
tests in test_identity_continuity_verification.py CANNOT, because they reboot at a
constant git revision):

1. A behaviour-neutral rebuild (same ratified packs, different build revision) is
   the SAME identity — ``code_revision`` is no longer hashed.
2. A pre-split (legacy, code_revision-folded) checkpoint whose packs verify
   identical MIGRATES (warn + re-stamp), it does NOT flag-day strict-break.
3. A genuine ratified-pack divergence STILL refuses under strict — the migration
   tolerance is *verifying*, not blind (the wrong=identity proof obligation:
   this test fails loudly if the migration ever swallowed a real pack swap).
4. The reconcile decision is the single source of truth (unit-tested directly).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from core.engine_identity import (
    ENGINE_IDENTITY_SCHEME,
    IdentityContinuityError,
    IdentityReconciliation,
    _resolve_pack_ids,
    compute_engine_identity,
    compute_legacy_engine_identity,
    engine_identity_for_config,
    reconcile_loaded_identity,
)
from engine_state import EngineStateStore

_DEFAULT_CFG = RuntimeConfig()
_DEFAULT_PACKS = _resolve_pack_ids(_DEFAULT_CFG)
_CURRENT_ID = compute_engine_identity(_DEFAULT_PACKS)  # packs-only default identity


# --- reconcile_loaded_identity: the single source of truth (fast unit proofs) ---


def test_reconcile_match_on_current_scheme() -> None:
    r = reconcile_loaded_identity(
        _DEFAULT_CFG,
        _CURRENT_ID,
        stored_identity=_CURRENT_ID,
        stored_scheme=ENGINE_IDENTITY_SCHEME,
        stored_revision="any-rev",
    )
    assert r is IdentityReconciliation.MATCH


def test_reconcile_diverged_on_current_scheme_mismatch() -> None:
    r = reconcile_loaded_identity(
        _DEFAULT_CFG,
        _CURRENT_ID,
        stored_identity="deadbeef" * 8,
        stored_scheme=ENGINE_IDENTITY_SCHEME,
        stored_revision="any-rev",
    )
    assert r is IdentityReconciliation.DIVERGED


def test_reconcile_migrates_legacy_stamp_with_same_packs() -> None:
    # A legacy (scheme 1 / absent) stamp of the CURRENT packs at some old rev.
    legacy = compute_legacy_engine_identity(_DEFAULT_PACKS, "old-rev")
    r = reconcile_loaded_identity(
        _DEFAULT_CFG,
        _CURRENT_ID,
        stored_identity=legacy,
        stored_scheme=1,
        stored_revision="old-rev",
    )
    assert r is IdentityReconciliation.MIGRATED


def test_reconcile_refuses_legacy_stamp_with_different_packs() -> None:
    # THE wrong=identity defense: a legacy stamp of a DIFFERENT identity pack must
    # NOT be silently migrated — the packs genuinely diverged.
    other_packs = _resolve_pack_ids(RuntimeConfig(identity_pack="precision_first_v1"))
    legacy_other = compute_legacy_engine_identity(other_packs, "old-rev")
    r = reconcile_loaded_identity(
        _DEFAULT_CFG,
        _CURRENT_ID,
        stored_identity=legacy_other,
        stored_scheme=1,
        stored_revision="old-rev",
    )
    assert r is IdentityReconciliation.DIVERGED


def test_reconcile_legacy_without_revision_is_conservative() -> None:
    # Without the persisted revision the legacy hash can't be reconstructed, so we
    # cannot prove the packs are unchanged -> refuse rather than blindly migrate.
    legacy = compute_legacy_engine_identity(_DEFAULT_PACKS, "old-rev")
    r = reconcile_loaded_identity(
        _DEFAULT_CFG,
        _CURRENT_ID,
        stored_identity=legacy,
        stored_scheme=1,
        stored_revision="",
    )
    assert r is IdentityReconciliation.DIVERGED


# --- runtime integration: migration of a real pre-split checkpoint ---


def _write_legacy_manifest(
    state_dir: Path, *, pack_config: RuntimeConfig, revision: str = "old-rev-001"
) -> None:
    """Write a flat (pre-ADR-0219) manifest stamped under the LEGACY scheme — i.e.
    ``engine_identity`` folded ``code_revision`` and there is no ``identity_scheme``
    marker, exactly as a pre-split build would have left it."""
    state_dir.mkdir(parents=True, exist_ok=True)
    legacy_id = compute_legacy_engine_identity(_resolve_pack_ids(pack_config), revision)
    (state_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "turn_count": 4,
                "written_at_revision": revision,
                "engine_identity": legacy_id,
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_legacy_checkpoint_migrates_under_strict_then_restamps(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    _write_legacy_manifest(state_dir, pack_config=RuntimeConfig())  # same (default) packs

    # Strict mode must NOT flag-day-break a same-packs legacy checkpoint — it
    # migrates with a distinct (non-"break") warning and resumes.
    with pytest.warns(RuntimeWarning, match="migrating engine-identity stamp scheme"):
        runtime = ChatRuntime(
            config=RuntimeConfig(strict_identity_continuity=True),
            engine_state_path=state_dir,
        )
    assert runtime.identity_continuity_break is False

    # The next checkpoint re-stamps under the packs-only scheme.
    pipe = CognitiveTurnPipeline(runtime=runtime)
    pipe.run("What causes light?")
    manifest = EngineStateStore(state_dir).load_manifest() or {}
    assert manifest["identity_scheme"] == ENGINE_IDENTITY_SCHEME
    assert manifest["engine_identity"] == engine_identity_for_config(RuntimeConfig())


def test_legacy_checkpoint_with_different_packs_refuses_under_strict(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "es"
    # Legacy stamp of a DIFFERENT identity pack — a genuine substrate divergence.
    _write_legacy_manifest(
        state_dir, pack_config=RuntimeConfig(identity_pack="precision_first_v1")
    )
    with pytest.raises(IdentityContinuityError):
        ChatRuntime(
            config=RuntimeConfig(strict_identity_continuity=True),
            engine_state_path=state_dir,
        )


def test_legacy_checkpoint_with_different_packs_breaks_without_strict(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "es"
    _write_legacy_manifest(
        state_dir, pack_config=RuntimeConfig(identity_pack="precision_first_v1")
    )
    with pytest.warns(RuntimeWarning, match="identity continuity break"):
        runtime = ChatRuntime(config=RuntimeConfig(), engine_state_path=state_dir)
    assert runtime.identity_continuity_break is True


# --- malformed / missing manifest fields must not crash the guard or reader ---


def test_malformed_identity_scheme_does_not_crash_the_load_guard(tmp_path: Path) -> None:
    # A non-int identity_scheme must fall back to the legacy scheme (verifying
    # migration), not raise on int() while loading the checkpoint.
    state_dir = tmp_path / "es"
    state_dir.mkdir(parents=True)
    legacy_id = compute_legacy_engine_identity(_DEFAULT_PACKS, "old-rev")
    (state_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "turn_count": 4,
                "written_at_revision": "old-rev",
                "engine_identity": legacy_id,
                "identity_scheme": "not-an-int",  # malformed
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    with pytest.warns(RuntimeWarning, match="migrating engine-identity stamp scheme"):
        runtime = ChatRuntime(
            config=RuntimeConfig(strict_identity_continuity=True),
            engine_state_path=state_dir,
        )
    assert runtime.identity_continuity_break is False


def test_reader_malformed_identity_scheme_falls_back_to_legacy() -> None:
    from workbench.readers import _identity_continuity_from_manifest

    # A legacy stamp of the CURRENT default packs, but identity_scheme is garbage:
    # the reader must fall back to legacy and verify-migrate -> "verified", not crash.
    legacy = compute_legacy_engine_identity(_DEFAULT_PACKS, "r1")
    result = _identity_continuity_from_manifest(
        {
            "schema_version": 2,
            "turn_count": 1,
            "written_at_revision": "r1",
            "engine_identity": legacy,
            "identity_scheme": "not-an-int",
        }
    )
    assert result is not None
    assert result.status == "verified"


def test_reader_missing_revision_is_a_conservative_break() -> None:
    from workbench.readers import _identity_continuity_from_manifest

    # A legacy stamp with NO written_at_revision can't be verified -> DIVERGED ->
    # "break" (never blindly "verified"); and it must not crash on a None revision.
    legacy = compute_legacy_engine_identity(_DEFAULT_PACKS, "r1")
    result = _identity_continuity_from_manifest(
        {
            "schema_version": 2,
            "turn_count": 1,
            "engine_identity": legacy,
            # no written_at_revision, no identity_scheme
        }
    )
    assert result is not None
    assert result.status == "break"
