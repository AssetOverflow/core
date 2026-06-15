"""EngineIdentity — content-derived identity of the ratified substrate (L11).

``EngineIdentity`` is the sha256 of the canonical serialization of the engine's
ratified PERSONALITY substrate — the active identity / safety / ethics / register
/ anchor-lens pack files. It is **content-derived, NOT entropy-based**: two
engines with the same ratified packs compute the SAME identity, because they ARE
the same engine functionally (substrate is shareable).

This is the "who am I" hash. It is bumped only by a ratified change to the
identity substrate (a new identity pack, a safety-axis change), NOT by lived
learning (recall, teaching) and **NOT by the build revision** — that is the
engine's *experience* / *provenance*, carried separately (the manifest's
``written_at_revision``), not its identity. (ADR-0220: ``code_revision`` was
removed from the hashed tuple — a behavior-neutral rebuild is the SAME identity.)
The git-like lineage chain (parent links on ratification) and the reboot identity
verification build on this primitive.

Migration (ADR-0220): pre-split checkpoints stamped the identity WITH
``code_revision`` folded in (``identity_scheme`` 1 / absent). They are recognised
via the manifest's ``identity_scheme`` marker and migrated by a *verifying
re-stamp* — see ``reconcile_loaded_identity``: the legacy hash is reconstructed
from the persisted ``written_at_revision`` and the CURRENT packs; a match proves
the packs are unchanged (build-provenance-only divergence → resume + re-stamp),
a mismatch means the ratified packs genuinely changed (→ refuse). This avoids a
flag-day break while preserving "distinct ratified packs ⇒ refuse".

Honest scope: this is a *convention* naming the existing per-pack content hashes,
not a new pack format. The ratified teaching corpus / recognizer-registry head can
be folded into the tuple later (additive — a new key changes the identity, which
is the correct semantic for a ratified-substrate change).
"""

from __future__ import annotations

import enum
import hashlib
import json
from pathlib import Path
from typing import Any

from core.config import (
    DEFAULT_ANCHOR_LENS,
    DEFAULT_ETHICS_PACK,
    DEFAULT_IDENTITY_PACK,
    DEFAULT_REGISTER_PACK,
    RuntimeConfig,
)

# The never-swappable safety pack default (packs/safety/loader.py).
DEFAULT_SAFETY_PACK: str = "core_safety_axes_v1"

#: The current engine-identity stamp scheme (ADR-0220): ``2`` = packs-only hash.
#: A manifest with ``identity_scheme`` absent or ``< 2`` was stamped by the
#: pre-split build that folded ``code_revision`` into the hash (legacy scheme 1).
ENGINE_IDENTITY_SCHEME: int = 2

_PACKS_ROOT = Path(__file__).resolve().parents[1] / "packs"

#: role -> packs/ subdirectory holding ``<pack_id>.json``.
_ROLE_DIRS: dict[str, str] = {
    "identity": "identity",
    "safety": "safety",
    "ethics": "ethics",
    "register": "register",
    "anchor_lens": "anchor_lens",
}

#: The ratified roles that constitute the engine's identity, in canonical order.
RATIFIED_ROLES: tuple[str, ...] = (
    "identity",
    "safety",
    "ethics",
    "register",
    "anchor_lens",
)


class EngineIdentityError(RuntimeError):
    """A ratified pack named by the identity tuple could not be resolved."""


class IdentityContinuityError(RuntimeError):
    """A reboot found the stamped checkpoint identity != the recomputed identity.

    The ratified *pack* substrate changed while the engine was down, so it would
    resume the lived state under a DIFFERENT identity than the checkpoint was
    written under. A build-revision-only change is NOT this (ADR-0220) — it
    resumes. Raised only under strict identity continuity; the default surfaces a
    warning and a queryable break flag (reboot is recovery, not control flow).
    """


class IdentityReconciliation(enum.Enum):
    """The outcome of reconciling a stamped checkpoint identity against the build.

    - ``MATCH``: the stamp is the current (packs-only) scheme and equals the
      recomputed identity — a clean same-identity resume.
    - ``MIGRATED``: the stamp is the legacy (code_revision-folded) scheme, and a
      verifying recompute proves the ratified packs are unchanged — the same
      identity under an old stamp scheme; resume and re-stamp.
    - ``DIVERGED``: the ratified packs genuinely differ (a true different
      identity) — refuse under strict, warn + break otherwise.
    """

    MATCH = "match"
    MIGRATED = "migrated"
    DIVERGED = "diverged"


def _pack_content_hash(role: str, pack_id: str) -> str:
    path = _PACKS_ROOT / _ROLE_DIRS[role] / f"{pack_id}.json"
    if not path.exists():
        raise EngineIdentityError(
            f"ratified {role} pack not found: {_ROLE_DIRS[role]}/{pack_id}.json"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ratified_substrate(pack_ids: dict[str, str]) -> dict[str, Any]:
    """The canonical, auditable identity tuple — the ratified packs ONLY.

    ``{role: {"pack_id", "sha256"}}`` for every role in ``RATIFIED_ROLES``.
    ``pack_ids`` must name a pack for every such role. The build revision is
    deliberately NOT here (ADR-0220) — it is build provenance, recorded in the
    manifest's ``written_at_revision``, not part of the identity.
    """
    substrate: dict[str, Any] = {}
    for role in RATIFIED_ROLES:
        pack_id = pack_ids[role]
        substrate[role] = {
            "pack_id": pack_id,
            "sha256": _pack_content_hash(role, pack_id),
        }
    return substrate


def _hash_substrate(substrate: dict[str, Any]) -> str:
    canonical = json.dumps(
        substrate,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_engine_identity(pack_ids: dict[str, str]) -> str:
    """The sha256 EngineIdentity over the ratified-packs-only substrate tuple."""
    return _hash_substrate(ratified_substrate(pack_ids))


def compute_legacy_engine_identity(pack_ids: dict[str, str], git_revision: str) -> str:
    """Reproduce the PRE-split (scheme 1) identity: packs **plus** ``code_revision``.

    Byte-for-byte equivalent to the old ``compute_engine_identity`` so a legacy
    stamp can be reconstructed for the migration check (``reconcile_loaded_identity``).
    Do NOT use this to stamp new checkpoints — it exists only to recognise and
    verify legacy ones.
    """
    substrate = ratified_substrate(pack_ids)
    substrate["code_revision"] = git_revision
    return _hash_substrate(substrate)


def _resolve_pack_ids(config: RuntimeConfig) -> dict[str, str]:
    """Resolve each ratified role to its active pack id (config override or DEFAULT)."""
    return {
        "identity": config.identity_pack or DEFAULT_IDENTITY_PACK,
        "safety": DEFAULT_SAFETY_PACK,  # never-swappable
        "ethics": config.ethics_pack or DEFAULT_ETHICS_PACK,
        "register": config.register_pack_id or DEFAULT_REGISTER_PACK,
        "anchor_lens": config.anchor_lens_id or DEFAULT_ANCHOR_LENS,
    }


def engine_identity_for_config(config: RuntimeConfig) -> str:
    """EngineIdentity for a runtime config (resolving every role to its active pack)."""
    return compute_engine_identity(_resolve_pack_ids(config))


def ratified_substrate_for_config(config: RuntimeConfig) -> dict[str, Any]:
    """The auditable identity tuple (packs only) for a runtime config."""
    return ratified_substrate(_resolve_pack_ids(config))


def reconcile_loaded_identity(
    config: RuntimeConfig,
    current_identity: str,
    *,
    stored_identity: str,
    stored_scheme: int,
    stored_revision: str,
) -> IdentityReconciliation:
    """Reconcile a stamped checkpoint identity against the current build (ADR-0220).

    ``current_identity`` is the packs-only identity the current build computes for
    ``config`` (passed in to avoid recomputation). ``stored_*`` come from the
    loaded manifest (``engine_identity`` / ``identity_scheme`` / ``written_at_revision``).

    The single source of truth for the runtime load guard AND the workbench
    continuity reader, so both treat a legacy checkpoint identically:

    - Current scheme (``stored_scheme >= ENGINE_IDENTITY_SCHEME``): direct
      packs-only compare — ``MATCH`` or ``DIVERGED``.
    - Legacy scheme: the stored hash folded ``code_revision`` and is NOT directly
      comparable. Reconstruct the legacy hash from the CURRENT packs and the
      persisted ``stored_revision``; a match proves the packs are unchanged
      (``MIGRATED`` — same identity, build-provenance-only divergence). A mismatch
      means the ratified packs genuinely changed (``DIVERGED``). If the revision
      is missing we cannot verify, so we conservatively report ``DIVERGED`` rather
      than blindly migrating (which would swallow a real pack swap).
    """
    if stored_scheme >= ENGINE_IDENTITY_SCHEME:
        return (
            IdentityReconciliation.MATCH
            if stored_identity == current_identity
            else IdentityReconciliation.DIVERGED
        )
    if not stored_revision:
        return IdentityReconciliation.DIVERGED
    legacy = compute_legacy_engine_identity(_resolve_pack_ids(config), stored_revision)
    return (
        IdentityReconciliation.MIGRATED
        if legacy == stored_identity
        else IdentityReconciliation.DIVERGED
    )
