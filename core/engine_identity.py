"""EngineIdentity — content-derived identity of the ratified substrate (L11).

``EngineIdentity`` is the sha256 of the canonical serialization of the engine's
ratified PERSONALITY substrate — the active identity / safety / ethics / register
/ anchor-lens pack files — plus the code revision. It is **content-derived, NOT
entropy-based**: two engines with the same ratified substrate compute the SAME
identity, because they ARE the same engine functionally (substrate is shareable).

This is the "who am I" hash. It is bumped only by a ratified change to the
identity substrate (a new identity pack, a safety-axis change), NOT by lived
learning (recall, teaching) — that is the engine's *experience*, carried across
reboot by the Shape B+ lived-state lineage, not its identity. The git-like
lineage chain (parent links on ratification) and the reboot identity verification
build on this primitive.

Honest scope (per the EngineIdentity candidate note): this is a *convention*
naming the existing per-pack content hashes, not a new pack format. The ratified
teaching corpus / recognizer-registry head can be folded into the tuple later
(additive — a new key changes the identity, which is the correct semantic for a
ratified-substrate change).
"""

from __future__ import annotations

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

    The ratified substrate changed while the engine was down, so it would resume
    the lived state under a DIFFERENT identity than the checkpoint was written
    under. Raised only under strict identity continuity; the default surfaces a
    warning and a queryable break flag (reboot is recovery, not control flow).
    """


def _pack_content_hash(role: str, pack_id: str) -> str:
    path = _PACKS_ROOT / _ROLE_DIRS[role] / f"{pack_id}.json"
    if not path.exists():
        raise EngineIdentityError(
            f"ratified {role} pack not found: {_ROLE_DIRS[role]}/{pack_id}.json"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ratified_substrate(pack_ids: dict[str, str], git_revision: str) -> dict[str, Any]:
    """The canonical, auditable identity tuple.

    ``{role: {"pack_id", "sha256"}}`` for every ratified role plus
    ``"code_revision"``. ``pack_ids`` must name a pack for every role in
    ``RATIFIED_ROLES``.
    """
    substrate: dict[str, Any] = {}
    for role in RATIFIED_ROLES:
        pack_id = pack_ids[role]
        substrate[role] = {
            "pack_id": pack_id,
            "sha256": _pack_content_hash(role, pack_id),
        }
    substrate["code_revision"] = git_revision
    return substrate


def compute_engine_identity(pack_ids: dict[str, str], git_revision: str) -> str:
    """The sha256 EngineIdentity over the ratified substrate tuple."""
    canonical = json.dumps(
        ratified_substrate(pack_ids, git_revision),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolve_pack_ids(config: RuntimeConfig) -> dict[str, str]:
    """Resolve each ratified role to its active pack id (config override or DEFAULT)."""
    return {
        "identity": config.identity_pack or DEFAULT_IDENTITY_PACK,
        "safety": DEFAULT_SAFETY_PACK,  # never-swappable
        "ethics": config.ethics_pack or DEFAULT_ETHICS_PACK,
        "register": config.register_pack_id or DEFAULT_REGISTER_PACK,
        "anchor_lens": config.anchor_lens_id or DEFAULT_ANCHOR_LENS,
    }


def engine_identity_for_config(config: RuntimeConfig, git_revision: str) -> str:
    """EngineIdentity for a runtime config (resolving every role to its active pack)."""
    return compute_engine_identity(_resolve_pack_ids(config), git_revision)


def ratified_substrate_for_config(
    config: RuntimeConfig, git_revision: str
) -> dict[str, Any]:
    """The auditable identity tuple for a runtime config."""
    return ratified_substrate(_resolve_pack_ids(config), git_revision)
