"""Safety-pack loader implementation.

Companion to ``packs/identity/loader.py``.  Identity packs carry the
character of CORE (which can be swapped per deployment); safety packs
carry the boundaries CORE will *never* cross (which cannot be swapped at
all).  Architecturally they are sister concerns but structurally they
are separate: different directory, different schema, different loader.

See ``docs/decisions/ADR-0029-safety-packs.md``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Iterable

from formation.hashing import verify_seal


class SafetyPackError(RuntimeError):
    """Raised when the safety pack is missing, malformed, or unverified.

    Inherits from ``RuntimeError`` (not ``ValueError`` like
    ``IdentityPackError``) because a missing safety pack is a fail-closed
    runtime condition, not a recoverable input-validation error.
    """


DEFAULT_SAFETY_PACK: str = "core_safety_axes_v1"
_DEFAULT_SEARCH_PATHS: tuple[Path, ...] = (
    Path(__file__).resolve().parent,
)


@dataclass(frozen=True, slots=True)
class SafetyPack:
    """Loaded safety pack.

    ``boundary_ids`` is the set of constraints to be unioned into the
    runtime ``IdentityManifold.boundary_ids``.  Identity packs may add
    boundaries on top, but the loader composition step (see
    ``chat/runtime.py``) ensures these are always present.
    """

    pack_id: str
    version: str
    description: str
    boundary_ids: FrozenSet[str]
    boundary_descriptions: dict[str, str]
    mastery_report_sha256: str
    ratified: bool


def load_safety_pack(
    pack_id: str = DEFAULT_SAFETY_PACK,
    *,
    search_paths: Iterable[Path | str] | None = None,
    require_ratified: bool | None = None,
) -> SafetyPack:
    """Load the safety pack.  Fails closed on any error.

    Args:
        pack_id: Safety pack identifier.  Defaults to
            ``DEFAULT_SAFETY_PACK``.  Callers should not pass anything
            else in production; the argument exists for testing.
        search_paths: Directories to search.  Defaults to
            ``packs/safety/``.
        require_ratified: When ``True``, require the companion
            ``<pack_id>.mastery_report.json`` and verify its self-seal.
            ``None`` (default) → production mode unless
            ``CORE_ALLOW_UNRATIFIED_SAFETY=1`` is set.  ``False`` →
            never require ratification (tests only).

    Raises:
        SafetyPackError: On any failure.  Callers must not catch and
            continue — a CORE installation without an operative safety
            pack must refuse to start.
    """
    paths = _resolve_search_paths(search_paths)
    pack_path = _find_pack(pack_id, paths)
    raw = _read_json(pack_path)
    _validate_envelope(raw, pack_id)
    _validate_ratification(raw, pack_id, require_ratified, pack_path)
    boundaries = _validate_boundaries(raw["boundary_ids"], pack_id)
    descriptions = _validate_descriptions(
        raw.get("boundary_descriptions", {}), pack_id, boundaries,
    )
    return SafetyPack(
        pack_id=str(raw["pack_id"]),
        version=str(raw["version"]),
        description=str(raw["description"]),
        boundary_ids=frozenset(boundaries),
        boundary_descriptions=descriptions,
        mastery_report_sha256=str(raw.get("mastery_report_sha256", "")),
        ratified=bool(raw.get("mastery_report_sha256")),
    )


# ---------- internals ----------


def _resolve_search_paths(
    search_paths: Iterable[Path | str] | None,
) -> tuple[Path, ...]:
    if search_paths is None:
        return _DEFAULT_SEARCH_PATHS
    return tuple(Path(p) for p in search_paths)


def _find_pack(pack_id: str, paths: tuple[Path, ...]) -> Path:
    if not pack_id or "/" in pack_id or ".." in pack_id:
        raise SafetyPackError(f"invalid safety pack_id: {pack_id!r}")
    for d in paths:
        candidate = d / f"{pack_id}.json"
        if candidate.is_file():
            return candidate
    raise SafetyPackError(
        f"safety pack {pack_id!r} not found in "
        f"{[str(p) for p in paths]} — refusing to start without an "
        "operative safety pack"
    )


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyPackError(
            f"failed to read safety pack {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise SafetyPackError(
            f"safety pack {path} did not deserialize to a dict"
        )
    return data


def _validate_envelope(raw: dict, pack_id: str) -> None:
    required = ("pack_id", "version", "description", "schema_version", "boundary_ids")
    missing = [k for k in required if k not in raw]
    if missing:
        raise SafetyPackError(
            f"safety pack {pack_id!r} missing required fields: {missing}"
        )
    if raw.get("schema_version") != "1.0.0":
        raise SafetyPackError(
            f"safety pack {pack_id!r}: unsupported schema_version "
            f"{raw.get('schema_version')!r}"
        )
    if raw.get("pack_id") != pack_id:
        raise SafetyPackError(
            f"safety pack file declares pack_id={raw.get('pack_id')!r} "
            f"but was requested as {pack_id!r}"
        )


def _validate_ratification(
    raw: dict, pack_id: str, require_ratified: bool | None, pack_path: Path,
) -> None:
    if require_ratified is False:
        return
    if require_ratified is None:
        require_ratified = (
            os.environ.get("CORE_ALLOW_UNRATIFIED_SAFETY") != "1"
        )
    if not require_ratified:
        return
    declared_sha = raw.get("mastery_report_sha256", "")
    if not declared_sha:
        raise SafetyPackError(
            f"safety pack {pack_id!r} is not ratified "
            "(mastery_report_sha256 empty); production refuses unratified "
            "safety packs.  Run scripts/ratify_safety_pack.py."
        )
    report_path = pack_path.parent / f"{pack_id}.mastery_report.json"
    if not report_path.is_file():
        raise SafetyPackError(
            f"safety pack {pack_id!r}: companion report "
            f"{report_path.name!r} is missing"
        )
    try:
        with report_path.open("r", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyPackError(
            f"safety pack {pack_id!r}: failed to read companion report: {exc}"
        ) from exc
    if not isinstance(report, dict):
        raise SafetyPackError(
            f"safety pack {pack_id!r}: companion report is not a JSON object"
        )
    if report.get("report_sha256") != declared_sha:
        raise SafetyPackError(
            f"safety pack {pack_id!r}: companion report SHA "
            f"{str(report.get('report_sha256'))[:12]}... does not match "
            f"pack's declared {declared_sha[:12]}..."
        )
    if not verify_seal(report, sha_field="report_sha256"):
        raise SafetyPackError(
            f"safety pack {pack_id!r}: companion report failed self-seal "
            "verification"
        )
    if not report.get("ratified", False):
        raise SafetyPackError(
            f"safety pack {pack_id!r}: companion report has ratified=False"
        )


def _validate_boundaries(value: object, pack_id: str) -> list[str]:
    if not isinstance(value, list) or len(value) < 1:
        raise SafetyPackError(
            f"safety pack {pack_id!r}: boundary_ids must be a non-empty list"
        )
    seen: set[str] = set()
    out: list[str] = []
    for i, b in enumerate(value):
        if not isinstance(b, str) or not b:
            raise SafetyPackError(
                f"safety pack {pack_id!r}: boundary_ids[{i}] must be a "
                "non-empty string"
            )
        if b in seen:
            raise SafetyPackError(
                f"safety pack {pack_id!r}: duplicate boundary_id {b!r}"
            )
        seen.add(b)
        out.append(b)
    return out


def _validate_descriptions(
    value: object, pack_id: str, boundaries: list[str],
) -> dict[str, str]:
    if not isinstance(value, dict):
        raise SafetyPackError(
            f"safety pack {pack_id!r}: boundary_descriptions must be a dict"
        )
    out: dict[str, str] = {}
    for b in boundaries:
        desc = value.get(b, "")
        if not isinstance(desc, str):
            raise SafetyPackError(
                f"safety pack {pack_id!r}: boundary_descriptions[{b!r}] "
                "must be a string"
            )
        out[b] = desc
    return out


__all__ = [
    "DEFAULT_SAFETY_PACK",
    "SafetyPack",
    "SafetyPackError",
    "load_safety_pack",
]
