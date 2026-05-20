"""Rhetorical-style pack loader (ADR-0087 substrate phase).

Reads a ratified rhetorical-style pack from disk and constructs a
frozen :class:`RhetoricalStylePack` for the runtime to mount.

Pattern is the same as :mod:`packs.anchor_lens.loader`:

* Self-sealed mastery report verified at load time
  (``require_ratified=True`` by default; bypassed by
  ``CORE_ALLOW_UNRATIFIED_RHETORICAL_STYLE=1`` for dev).
* Path-traversal-safe ``pack_id`` resolution.
* Allow-list schema validation — unknown keys rejected; ``permitted_frames``
  / ``required_moves_per_claim`` / ``forbidden_moves`` constrained
  to known-frame / known-move vocabularies.
* ``default_unstyled: true`` only valid when all three lists are
  empty (the null-lift pack).

The substrate is composer-side only.  At this phase no composer or
realizer yet consumes the pack — the loader exists so the consumer
ADR can mount real packs against a stable contract.

ADR
---
ADR-0087 — Rhetorical Style as Selection Axis (Pre-Work for Writing
Curriculum)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from formation.hashing import verify_seal


DEFAULT_RHETORICAL_STYLE_PACK: str = "default_unstyled_v1"

_DEFAULT_SEARCH_PATHS: tuple[Path, ...] = (
    Path(__file__).resolve().parent,
)

_SCHEMA_VERSION: str = "1.0.0"

# v0 allow-lists.  Deliberately small per ADR-0087 §Composer & realizer
# contract — additions require ADR amendment, not silent extension.
_ALLOWED_FRAMES: frozenset[str] = frozenset({
    "warrant",            # "Therefore X, because Y."
    "concession",         # "While X, Y."
    "hedge",              # "This suggests X, though Q."
    "definitional_move",  # "By X we mean {gloss}."
})
_ALLOWED_MOVES: frozenset[str] = frozenset({
    "claim",
    "evidence",
    "warrant",
    "concession",
    "hedge",
    "bare_assertion",
    "definitional",
})

_REQUIRED_KEYS: frozenset[str] = frozenset({
    "pack_id",
    "schema_version",
    "version",
    "issued_at",
    "default_unstyled",
    "permitted_frames",
    "required_moves_per_claim",
    "forbidden_moves",
    "provenance",
    "mastery_report_sha256",
})

_MAX_LIST_LEN: int = 32
_MAX_PROVENANCE_LEN: int = 256
_MAX_ISSUED_AT_LEN: int = 64


class RhetoricalStylePackError(RuntimeError):
    """Raised when a rhetorical-style pack is missing, malformed, or
    unverified.

    Inherits from :class:`RuntimeError` (not :class:`ValueError`) on the
    same principle as :class:`packs.safety.SafetyPackError`: a missing
    rhetorical-style pack for a deployment that opts in is a
    fail-closed runtime condition, not a recoverable input-validation
    error.
    """


def _safe_pack_id(value: object) -> str:
    """Return a printable, length-capped version of a pack id."""
    s = str(value) if value is not None else ""
    return s[:64]


@dataclass(frozen=True, slots=True)
class RhetoricalStylePack:
    """Frozen rhetorical-style pack.

    The substantive content of the pack is three lists:

    * ``permitted_frames`` — the realizer's frame allow-list (the only
      rhetorical-mode frames it may emit while this pack is mounted).
    * ``required_moves_per_claim`` — moves the composer MUST include for
      every claim it surfaces.
    * ``forbidden_moves`` — moves the composer MUST refuse to ratify.

    The null-lift pack (``default_unstyled_v1``) has all three lists
    empty and ``default_unstyled=True``.  Loading it changes nothing.
    """

    pack_id: str
    schema_version: str
    version: int
    issued_at: str
    default_unstyled: bool
    permitted_frames: tuple[str, ...]
    required_moves_per_claim: tuple[str, ...]
    forbidden_moves: tuple[str, ...]
    provenance: str
    mastery_report_sha256: str = ""

    def is_null_lift(self) -> bool:
        """True iff this pack imposes no constraints at all.

        The null-lift pack is the substrate equivalent of
        ``anchor_lens.AnchorLens.is_null_lens`` — structurally
        equivalent to no pack being mounted.
        """
        return (
            self.default_unstyled
            and not self.permitted_frames
            and not self.required_moves_per_claim
            and not self.forbidden_moves
        )


def _validate_pack_id_for_fs(pack_id: object) -> None:
    """Reject path-traversal / slash / empty / non-string pack ids."""
    if (
        not pack_id
        or not isinstance(pack_id, str)
        or "/" in pack_id
        or "\\" in pack_id
        or ".." in pack_id
        or pack_id.startswith(".")
    ):
        raise RhetoricalStylePackError(
            f"invalid rhetorical-style pack_id: {_safe_pack_id(pack_id)!r}"
        )
    for ch in pack_id:
        if not (ch.isascii() and (ch.isalnum() or ch in {"_", "-"})):
            raise RhetoricalStylePackError(
                f"rhetorical-style pack_id must be alphanumeric/_/-: "
                f"{_safe_pack_id(pack_id)!r}"
            )


def _find_pack_path(pack_id: str, search_paths: Iterable[Path]) -> Path:
    _validate_pack_id_for_fs(pack_id)
    for directory in search_paths:
        candidate = Path(directory) / f"{pack_id}.json"
        if candidate.exists():
            return candidate
    raise RhetoricalStylePackError(
        f"rhetorical-style pack {_safe_pack_id(pack_id)!r} not found in search paths"
    )


def _validate_string_list(
    raw: object,
    *,
    pack_id: str,
    field_name: str,
    allow_list: frozenset[str],
) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: {field_name!r} must be a list"
        )
    if len(raw) > _MAX_LIST_LEN:
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: {field_name!r} exceeds max len {_MAX_LIST_LEN}"
        )
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item:
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: {field_name!r} must contain non-empty strings"
            )
        if item not in allow_list:
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: {field_name!r} contains "
                f"unknown value {item!r} (allowed: {sorted(allow_list)})"
            )
        if item in seen:
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: {field_name!r} contains "
                f"duplicate value {item!r}"
            )
        seen.add(item)
        out.append(item)
    return tuple(out)


def _validate_envelope(raw: dict, pack_id: str) -> None:
    if not isinstance(raw, dict):
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: top-level payload must be a JSON object"
        )
    unknown = set(raw.keys()) - _REQUIRED_KEYS
    if unknown:
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: unrecognised key(s) {sorted(unknown)}; "
            f"strict schema gate per ADR-0087"
        )
    missing = _REQUIRED_KEYS - set(raw.keys())
    if missing:
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: missing required key(s) {sorted(missing)}"
        )
    if raw["pack_id"] != pack_id:
        raise RhetoricalStylePackError(
            f"pack file declares pack_id={_safe_pack_id(raw['pack_id'])!r} but "
            f"was requested as {_safe_pack_id(pack_id)!r}"
        )
    if raw["schema_version"] != _SCHEMA_VERSION:
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: unsupported schema_version "
            f"{raw['schema_version']!r} (expected {_SCHEMA_VERSION!r})"
        )
    if not isinstance(raw["version"], int) or isinstance(raw["version"], bool) or raw["version"] < 1:
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: version must be a positive int"
        )
    if not isinstance(raw["issued_at"], str) or not raw["issued_at"] or len(raw["issued_at"]) > _MAX_ISSUED_AT_LEN:
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: issued_at must be a non-empty string <= {_MAX_ISSUED_AT_LEN} chars"
        )
    if not isinstance(raw["default_unstyled"], bool):
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: default_unstyled must be a boolean"
        )
    if not isinstance(raw["provenance"], str) or not raw["provenance"] or len(raw["provenance"]) > _MAX_PROVENANCE_LEN:
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: provenance must be a non-empty string <= {_MAX_PROVENANCE_LEN} chars"
        )
    if not isinstance(raw["mastery_report_sha256"], str):
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: mastery_report_sha256 must be a string"
        )


def _validate_unstyled_invariant(
    pack_id: str,
    default_unstyled: bool,
    permitted_frames: tuple[str, ...],
    required_moves_per_claim: tuple[str, ...],
    forbidden_moves: tuple[str, ...],
) -> None:
    """Enforce ADR-0087 §Verification: ``default_unstyled: true`` only
    valid when all three constraint lists are empty.
    """
    if default_unstyled:
        if permitted_frames or required_moves_per_claim or forbidden_moves:
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: default_unstyled=true requires "
                f"empty permitted_frames / required_moves_per_claim / forbidden_moves"
            )
    else:
        # A non-default pack that declares zero constraints is also
        # rejected — it would be indistinguishable from null-lift but
        # would silently miss the default_unstyled invariant test.
        if not permitted_frames and not required_moves_per_claim and not forbidden_moves:
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: non-default pack must declare at "
                f"least one of permitted_frames / required_moves_per_claim / forbidden_moves"
            )


def load_rhetorical_style_pack(
    pack_id: str = DEFAULT_RHETORICAL_STYLE_PACK,
    *,
    search_paths: Iterable[Path | str] | None = None,
    require_ratified: bool | None = None,
) -> RhetoricalStylePack:
    """Load, validate, and return a frozen :class:`RhetoricalStylePack`.

    Parameters
    ----------
    pack_id:
        Pack identifier, e.g. ``"default_unstyled_v1"``.  Defaults to
        :data:`DEFAULT_RHETORICAL_STYLE_PACK`.
    search_paths:
        Directories to search for ``<pack_id>.json``.  Defaults to the
        directory containing this module.
    require_ratified:
        If ``True``, refuse packs with an empty
        ``mastery_report_sha256``.  If ``None`` (default), falls back
        to the ``CORE_ALLOW_UNRATIFIED_RHETORICAL_STYLE`` environment
        variable (refuse unless set to ``1`` / ``true`` / ``yes``).
    """
    resolved_paths: list[Path] = [
        Path(p) for p in (search_paths or _DEFAULT_SEARCH_PATHS)
    ]
    pack_path = _find_pack_path(pack_id, resolved_paths)
    try:
        raw: dict = json.loads(pack_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RhetoricalStylePackError(
            f"pack {_safe_pack_id(pack_id)!r}: malformed JSON ({exc})"
        ) from exc

    _validate_envelope(raw, pack_id)

    permitted_frames = _validate_string_list(
        raw["permitted_frames"], pack_id=pack_id,
        field_name="permitted_frames", allow_list=_ALLOWED_FRAMES,
    )
    required_moves_per_claim = _validate_string_list(
        raw["required_moves_per_claim"], pack_id=pack_id,
        field_name="required_moves_per_claim", allow_list=_ALLOWED_MOVES,
    )
    forbidden_moves = _validate_string_list(
        raw["forbidden_moves"], pack_id=pack_id,
        field_name="forbidden_moves", allow_list=_ALLOWED_MOVES,
    )

    _validate_unstyled_invariant(
        pack_id,
        bool(raw["default_unstyled"]),
        permitted_frames,
        required_moves_per_claim,
        forbidden_moves,
    )

    if require_ratified is None:
        env = os.environ.get("CORE_ALLOW_UNRATIFIED_RHETORICAL_STYLE", "").lower()
        require_ratified = env not in ("1", "true", "yes")

    declared_sha = raw["mastery_report_sha256"]
    if require_ratified:
        if not declared_sha:
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r} is not ratified "
                f"(mastery_report_sha256 is empty).  Run "
                f"scripts/ratify_rhetorical_style_packs.py or set "
                f"CORE_ALLOW_UNRATIFIED_RHETORICAL_STYLE=1 for development."
            )
        # Companion-SHA agreement check.
        report_path = pack_path.parent / f"{pack_id}.mastery_report.json"
        if not report_path.is_file():
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: companion mastery report missing "
                f"at {report_path}"
            )
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: companion mastery report "
                f"unreadable: {exc}"
            ) from exc
        report_sha = str(report.get("report_sha256", ""))
        if report_sha != declared_sha:
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: declared mastery_report_sha256 "
                f"does not match companion report's report_sha256"
            )
        if not verify_seal(report, sha_field="report_sha256"):
            raise RhetoricalStylePackError(
                f"pack {_safe_pack_id(pack_id)!r}: companion mastery report self-seal "
                f"verification failed"
            )

    return RhetoricalStylePack(
        pack_id=raw["pack_id"],
        schema_version=raw["schema_version"],
        version=raw["version"],
        issued_at=raw["issued_at"],
        default_unstyled=bool(raw["default_unstyled"]),
        permitted_frames=permitted_frames,
        required_moves_per_claim=required_moves_per_claim,
        forbidden_moves=forbidden_moves,
        provenance=raw["provenance"],
        mastery_report_sha256=declared_sha,
    )


def available_rhetorical_style_packs(
    search_paths: Iterable[Path | str] | None = None,
) -> list[dict]:
    """Return summary dicts for all ``.json`` packs in the search paths.

    Mirror of :func:`packs.anchor_lens.loader.available_anchor_lens_packs`.
    """
    resolved_paths: list[Path] = [
        Path(p) for p in (search_paths or _DEFAULT_SEARCH_PATHS)
    ]
    summaries: list[dict] = []
    for directory in resolved_paths:
        d = Path(directory)
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            stem = f.stem
            if stem.startswith("_") or ".mastery_report" in stem:
                continue
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            summaries.append({
                "pack_id": stem,
                "ratified": bool(raw.get("mastery_report_sha256", "")),
                "default_unstyled": bool(raw.get("default_unstyled", False)),
                "version": raw.get("version", 0),
            })
    return summaries
