"""Identity-pack loader.

Reads a content-addressed identity pack from disk and constructs an
:class:`IdentityManifold` for the runtime.  See
``docs/decisions/ADR-0027-identity-packs.md`` for context.

Loader contract (read carefully — this is a trust boundary):

* The loader never mutates a pack on disk.  Pack creation goes through
  the formation pipeline (``formation.templates.identity_anchor`` ->
  compose -> ratify -> promote).
* Bounds checks (axis count, direction magnitude, weight, threshold
  range, axis-id uniqueness) are enforced before any field of the
  returned manifold is observable to runtime code.
* When ``require_ratified=True`` and the pack's ``mastery_report_sha256``
  is empty, the loader refuses.  Development environments may set
  ``CORE_ALLOW_UNRATIFIED_IDENTITY=1`` to bypass — this is a
  development-only escape hatch and is logged.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from core.physics.identity import IdentityManifold, SurfacePreferences, ValueAxis
from formation.hashing import verify_seal


class IdentityPackError(ValueError):
    """Raised when an identity pack is missing, malformed, or out of bounds."""


_DEFAULT_SEARCH_PATHS: tuple[Path, ...] = (
    Path(__file__).resolve().parent,
)
_MAX_WEIGHT: float = 10.0
_MIN_AXES: int = 1
_DIRECTION_LEN: int = 3
_DIRECTION_BOUND: float = 1.0
_THRESHOLD_LO: float = 0.0
_THRESHOLD_HI: float = 1.0


def load_identity_manifold(
    pack_id: str,
    *,
    search_paths: Iterable[Path | str] | None = None,
    require_ratified: bool | None = None,
) -> IdentityManifold:
    """Load an identity pack and construct its :class:`IdentityManifold`.

    Args:
        pack_id: Pack identifier (e.g. ``"default_general_v1"``).  The
            loader looks for ``<pack_id>.json`` in each search path.
        search_paths: Iterable of directories to search.  Default is the
            built-in ``packs/identity/`` directory.  Earlier paths take
            precedence — pass overlay directories first.
        require_ratified: When ``True``, refuse packs whose
            ``mastery_report_sha256`` is empty.  When ``None`` (default),
            require ratification unless the env var
            ``CORE_ALLOW_UNRATIFIED_IDENTITY=1`` is set.  When ``False``,
            never require ratification (for tests and development).

    Returns:
        A constructed :class:`IdentityManifold`.

    Raises:
        IdentityPackError: On any bounds violation, missing file, malformed
            JSON, or — in production mode — unverified self-seal.
    """
    paths = _resolve_search_paths(search_paths)
    pack_path = _find_pack(pack_id, paths)
    raw = _read_json(pack_path)
    _validate_envelope(raw, pack_id)
    _validate_ratification(raw, pack_id, require_ratified, pack_path)
    axes = _build_axes(raw["value_axes"], pack_id)
    threshold = _validate_threshold(raw["alignment_threshold"], pack_id)
    boundaries = frozenset(_validate_boundaries(raw["boundary_ids"], pack_id))
    surface_prefs = _build_surface_preferences(
        raw.get("surface_preferences"), pack_id,
    )
    return IdentityManifold(
        value_axes=axes,
        boundary_ids=boundaries,
        alignment_threshold=threshold,
        surface_preferences=surface_prefs,
    )


def available_packs(
    search_paths: Iterable[Path | str] | None = None,
) -> list[dict[str, object]]:
    """Return a list of ``{"pack_id", "version", "description", "ratified"}``
    dicts for every JSON pack discoverable on the search paths.  Sorted by
    ``pack_id``.
    """
    paths = _resolve_search_paths(search_paths)
    seen: dict[str, dict[str, object]] = {}
    for d in paths:
        if not d.is_dir():
            continue
        for entry in sorted(d.glob("*.json")):
            # Skip companion artifacts (mastery reports, etc.) — only
            # real identity packs declare ``schema_version`` and
            # ``value_axes``.
            if entry.name.endswith(".mastery_report.json"):
                continue
            try:
                raw = _read_json(entry)
            except IdentityPackError:
                continue
            if not isinstance(raw, dict):
                continue
            if "schema_version" not in raw or "value_axes" not in raw:
                continue
            pack_id = str(raw.get("pack_id", entry.stem))
            if pack_id in seen:
                continue
            seen[pack_id] = {
                "pack_id": pack_id,
                "version": str(raw.get("version", "")),
                "description": str(raw.get("description", "")),
                "ratified": bool(raw.get("mastery_report_sha256")),
                "path": str(entry),
            }
    return sorted(seen.values(), key=lambda d: str(d["pack_id"]))


# ---------- internals ----------


def _resolve_search_paths(
    search_paths: Iterable[Path | str] | None,
) -> tuple[Path, ...]:
    if search_paths is None:
        return _DEFAULT_SEARCH_PATHS
    return tuple(Path(p) for p in search_paths)


def _find_pack(pack_id: str, paths: tuple[Path, ...]) -> Path:
    if not pack_id or "/" in pack_id or ".." in pack_id:
        raise IdentityPackError(f"invalid pack_id: {pack_id!r}")
    for d in paths:
        candidate = d / f"{pack_id}.json"
        if candidate.is_file():
            return candidate
    raise IdentityPackError(
        f"identity pack {pack_id!r} not found in {[str(p) for p in paths]}"
    )


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityPackError(f"failed to read pack {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise IdentityPackError(f"pack {path} did not deserialize to a dict")
    return data


def _validate_envelope(raw: dict, pack_id: str) -> None:
    required = (
        "pack_id",
        "version",
        "description",
        "schema_version",
        "alignment_threshold",
        "boundary_ids",
        "value_axes",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise IdentityPackError(
            f"pack {pack_id!r} missing required fields: {missing}"
        )
    if raw.get("schema_version") != "1.0.0":
        raise IdentityPackError(
            f"pack {pack_id!r}: unsupported schema_version "
            f"{raw.get('schema_version')!r}"
        )
    if raw.get("pack_id") != pack_id:
        raise IdentityPackError(
            f"pack file declares pack_id={raw.get('pack_id')!r} but was "
            f"requested as {pack_id!r}"
        )


def _validate_ratification(
    raw: dict, pack_id: str, require_ratified: bool | None, pack_path: Path,
) -> None:
    if require_ratified is False:
        return
    if require_ratified is None:
        require_ratified = os.environ.get("CORE_ALLOW_UNRATIFIED_IDENTITY") != "1"
    if not require_ratified:
        return
    declared_sha = raw.get("mastery_report_sha256", "")
    if not declared_sha:
        raise IdentityPackError(
            f"pack {pack_id!r} is not ratified (mastery_report_sha256 empty); "
            "set CORE_ALLOW_UNRATIFIED_IDENTITY=1 for development, or "
            "ratify the pack through the formation pipeline "
            "(scripts/ratify_identity_packs.py)."
        )
    report_path = pack_path.parent / f"{pack_id}.mastery_report.json"
    if not report_path.is_file():
        raise IdentityPackError(
            f"pack {pack_id!r} declares mastery_report_sha256={declared_sha[:12]}"
            f"... but companion report file {report_path.name!r} is missing"
        )
    try:
        with report_path.open("r", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityPackError(
            f"pack {pack_id!r}: failed to read companion report: {exc}"
        ) from exc
    if not isinstance(report, dict):
        raise IdentityPackError(
            f"pack {pack_id!r}: companion report is not a JSON object"
        )
    if report.get("report_sha256") != declared_sha:
        raise IdentityPackError(
            f"pack {pack_id!r}: companion report SHA "
            f"{str(report.get('report_sha256'))[:12]}... does not match pack's "
            f"declared {declared_sha[:12]}..."
        )
    if not verify_seal(report, sha_field="report_sha256"):
        raise IdentityPackError(
            f"pack {pack_id!r}: companion report failed self-seal verification"
        )
    if not report.get("ratified", False):
        raise IdentityPackError(
            f"pack {pack_id!r}: companion report has ratified=False"
        )


def _build_axes(axes_raw: list, pack_id: str) -> tuple[ValueAxis, ...]:
    if not isinstance(axes_raw, list) or len(axes_raw) < _MIN_AXES:
        raise IdentityPackError(
            f"pack {pack_id!r}: value_axes must be a list with at least "
            f"{_MIN_AXES} axis"
        )
    seen_ids: set[str] = set()
    axes: list[ValueAxis] = []
    for i, axis_raw in enumerate(axes_raw):
        if not isinstance(axis_raw, dict):
            raise IdentityPackError(
                f"pack {pack_id!r}: axis[{i}] must be a dict, got "
                f"{type(axis_raw).__name__}"
            )
        for field in ("axis_id", "name", "direction", "weight"):
            if field not in axis_raw:
                raise IdentityPackError(
                    f"pack {pack_id!r}: axis[{i}] missing field {field!r}"
                )
        axis_id = str(axis_raw["axis_id"])
        if axis_id in seen_ids:
            raise IdentityPackError(
                f"pack {pack_id!r}: duplicate axis_id {axis_id!r}"
            )
        seen_ids.add(axis_id)
        direction = axis_raw["direction"]
        if not isinstance(direction, list) or len(direction) != _DIRECTION_LEN:
            raise IdentityPackError(
                f"pack {pack_id!r}: axis {axis_id!r} direction must be a "
                f"list of {_DIRECTION_LEN} floats"
            )
        for j, comp in enumerate(direction):
            if not isinstance(comp, (int, float)):
                raise IdentityPackError(
                    f"pack {pack_id!r}: axis {axis_id!r} direction[{j}] "
                    "must be numeric"
                )
            if not -_DIRECTION_BOUND <= float(comp) <= _DIRECTION_BOUND:
                raise IdentityPackError(
                    f"pack {pack_id!r}: axis {axis_id!r} direction[{j}]="
                    f"{comp} out of bounds [-{_DIRECTION_BOUND}, "
                    f"{_DIRECTION_BOUND}]"
                )
        weight = axis_raw["weight"]
        if not isinstance(weight, (int, float)):
            raise IdentityPackError(
                f"pack {pack_id!r}: axis {axis_id!r} weight must be numeric"
            )
        if not 0.0 <= float(weight) <= _MAX_WEIGHT:
            raise IdentityPackError(
                f"pack {pack_id!r}: axis {axis_id!r} weight={weight} "
                f"out of bounds [0, {_MAX_WEIGHT}]"
            )
        axes.append(
            ValueAxis(
                name=str(axis_raw["name"]),
                direction=tuple(float(x) for x in direction),
                axis_id=axis_id,
                weight=float(weight),
                theological_note=str(axis_raw.get("theological_note", "")),
            )
        )
    return tuple(axes)


def _validate_threshold(value: object, pack_id: str) -> float:
    if not isinstance(value, (int, float)):
        raise IdentityPackError(
            f"pack {pack_id!r}: alignment_threshold must be numeric"
        )
    fv = float(value)
    if not _THRESHOLD_LO <= fv <= _THRESHOLD_HI:
        raise IdentityPackError(
            f"pack {pack_id!r}: alignment_threshold={fv} out of bounds "
            f"[{_THRESHOLD_LO}, {_THRESHOLD_HI}]"
        )
    return fv


_ALLOWED_CLAIM_STRENGTHS: frozenset[str] = frozenset(
    {"balanced", "qualified", "affirmative"}
)
_MIN_HEDGE_LEN: int = 1
_MAX_HEDGE_LEN: int = 64


def _build_surface_preferences(
    value: object, pack_id: str,
) -> SurfacePreferences:
    """Parse and bounds-check the optional ``surface_preferences`` block.

    Absent block → defaults that reproduce pre-ADR-0028 behavior.
    """
    if value is None:
        return SurfacePreferences()
    if not isinstance(value, dict):
        raise IdentityPackError(
            f"pack {pack_id!r}: surface_preferences must be a dict, got "
            f"{type(value).__name__}"
        )
    defaults = SurfacePreferences()
    strong = _validate_threshold_field(
        value.get("hedge_threshold_strong", defaults.hedge_threshold_strong),
        pack_id, "hedge_threshold_strong",
    )
    soft = _validate_threshold_field(
        value.get("hedge_threshold_soft", defaults.hedge_threshold_soft),
        pack_id, "hedge_threshold_soft",
    )
    band_high = _validate_threshold_field(
        value.get("qualified_band_high", defaults.qualified_band_high),
        pack_id, "qualified_band_high",
    )
    if not (strong <= soft <= band_high):
        raise IdentityPackError(
            f"pack {pack_id!r}: surface_preferences thresholds must satisfy "
            f"hedge_threshold_strong ({strong}) <= "
            f"hedge_threshold_soft ({soft}) <= "
            f"qualified_band_high ({band_high})"
        )
    claim_strength = str(
        value.get("claim_strength", defaults.claim_strength)
    )
    if claim_strength not in _ALLOWED_CLAIM_STRENGTHS:
        raise IdentityPackError(
            f"pack {pack_id!r}: claim_strength={claim_strength!r} not in "
            f"{sorted(_ALLOWED_CLAIM_STRENGTHS)}"
        )
    return SurfacePreferences(
        hedge_threshold_strong=strong,
        hedge_threshold_soft=soft,
        preferred_hedge_strong=_validate_hedge_phrase(
            value.get("preferred_hedge_strong", defaults.preferred_hedge_strong),
            pack_id, "preferred_hedge_strong",
        ),
        preferred_hedge_soft=_validate_hedge_phrase(
            value.get("preferred_hedge_soft", defaults.preferred_hedge_soft),
            pack_id, "preferred_hedge_soft",
        ),
        claim_strength=claim_strength,
        qualified_band_high=band_high,
        preferred_qualifier=_validate_hedge_phrase(
            value.get("preferred_qualifier", defaults.preferred_qualifier),
            pack_id, "preferred_qualifier",
        ),
    )


def _validate_threshold_field(value: object, pack_id: str, field: str) -> float:
    if not isinstance(value, (int, float)):
        raise IdentityPackError(
            f"pack {pack_id!r}: surface_preferences.{field} must be numeric"
        )
    fv = float(value)
    if not _THRESHOLD_LO <= fv <= _THRESHOLD_HI:
        raise IdentityPackError(
            f"pack {pack_id!r}: surface_preferences.{field}={fv} out of "
            f"bounds [{_THRESHOLD_LO}, {_THRESHOLD_HI}]"
        )
    return fv


def _validate_hedge_phrase(value: object, pack_id: str, field: str) -> str:
    if not isinstance(value, str):
        raise IdentityPackError(
            f"pack {pack_id!r}: surface_preferences.{field} must be a string"
        )
    if not _MIN_HEDGE_LEN <= len(value) <= _MAX_HEDGE_LEN:
        raise IdentityPackError(
            f"pack {pack_id!r}: surface_preferences.{field} length "
            f"{len(value)} out of bounds [{_MIN_HEDGE_LEN}, {_MAX_HEDGE_LEN}]"
        )
    return value


def _validate_boundaries(value: object, pack_id: str) -> list[str]:
    if not isinstance(value, list):
        raise IdentityPackError(
            f"pack {pack_id!r}: boundary_ids must be a list"
        )
    out: list[str] = []
    for i, b in enumerate(value):
        if not isinstance(b, str) or not b:
            raise IdentityPackError(
                f"pack {pack_id!r}: boundary_ids[{i}] must be a non-empty "
                "string"
            )
        out.append(b)
    return out


__all__ = ["IdentityPackError", "available_packs", "load_identity_manifold"]
