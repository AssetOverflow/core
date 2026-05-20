"""Register-pack loader (ADR-0068, Plan Phase R1).

Reads a ratified register pack from disk and constructs a frozen
:class:`RegisterPack` for the runtime.  See
``docs/decisions/ADR-0068-register-pack-class.md`` for context.

Loader contract (trust boundary):

* Register packs are surface-side only.  They parameterise the realizer
  and never contribute to the runtime manifold, ``boundary_ids``,
  safety/ethics composition, or the trace hash.
* The loader never mutates a pack on disk.  Pack creation goes through
  ``scripts/ratify_register_packs.py``.
* Bounds checks (allowed ``depth_preference``, dict-shaped overrides,
  list-shaped marker buckets) are enforced before any field of the
  returned :class:`RegisterPack` is observable to runtime code.
* When ``require_ratified=True`` and the pack's
  ``mastery_report_sha256`` is empty, the loader refuses.  Development
  environments may set ``CORE_ALLOW_UNRATIFIED_REGISTER=1`` to bypass.
* :meth:`RegisterPack.unregistered` returns a frozen sentinel matching
  the in-memory shape of ``default_neutral_v1``.  R2 will widen the
  realizer to consume one or the other; until then, no runtime code
  imports this module (pinned by ``tests/test_register_pack_seam.py``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

from core._safe_display import safe_pack_id
from formation.hashing import verify_seal


class RegisterPackError(ValueError):
    """Raised when a register pack is missing, malformed, or out of bounds."""


_DEFAULT_SEARCH_PATHS: tuple[Path, ...] = (
    Path(__file__).resolve().parent,
)

_ALLOWED_DEPTH_PREFERENCES: frozenset[str] = frozenset(
    {"terse", "standard", "pedagogical"}
)
_MARKER_BUCKETS: tuple[str, ...] = ("openings", "transitions", "closings")
_SCHEMA_VERSION: str = "1.0.0"
_MAX_MARKER_LEN: int = 128
_MAX_MARKERS_PER_BUCKET: int = 32
_MAX_OVERRIDE_KEY_LEN: int = 64
_MAX_OVERRIDE_VALUE_LEN: int = 128
_OVERRIDE_INT_MIN: int = -1_000_000
_OVERRIDE_INT_MAX: int = 1_000_000

#: Nested key under ``realizer_overrides`` that carries per-intent
#: dispatch (ADR-0071, Phase R4).  The value is ``{intent_name: {flat_key:
#: flat_value, ...}}``.  Intent-name validation lives in the ratify
#: gate; the loader only enforces structural bounds.
_PER_INTENT_KEY: str = "per_intent"

#: Closed set of override keys whose value type is ``bool`` (ADR-0077, R6).
#: All other keys remain ``int | str`` per the original (ADR-0070) schema.
#: Keeping booleans behind a known-key allow-list preserves the trust
#: boundary against arbitrary operator-authored override values.
_BOOLEAN_OVERRIDE_KEYS: frozenset[str] = frozenset({
    "drop_provenance_tag",
    "compress_gloss",
    "drop_articles",
    "append_semantic_domain_clause",
})


@dataclass(frozen=True)
class DiscourseMarkers:
    """Bounded marker pack consumed by the seeded-variation path (R4)."""

    openings: tuple[str, ...] = ()
    transitions: tuple[str, ...] = ()
    closings: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        return not (self.openings or self.transitions or self.closings)


@dataclass(frozen=True)
class RegisterPack:
    """Frozen presentation-axis pack.

    Composes into the realizer at R2; at R1 nothing consumes it.
    """

    register_id: str
    version: str
    description: str
    display_name: str
    depth_preference: str
    realizer_overrides: Mapping[str, object] = field(default_factory=dict)
    discourse_markers: DiscourseMarkers = field(default_factory=DiscourseMarkers)
    mastery_report_sha256: str = ""

    def is_unregistered(self) -> bool:
        """True for the in-memory sentinel returned by :meth:`unregistered`."""
        return self.register_id == "__unregistered__"

    def is_null_register(self) -> bool:
        """True iff overrides + markers are empty (R1 ``default_neutral_v1``)."""
        return (
            not self.realizer_overrides and self.discourse_markers.is_empty()
        )

    @classmethod
    def unregistered(cls) -> "RegisterPack":
        """Return the in-memory sentinel used when no register pack is selected.

        Structurally identical to a null register (empty overrides, empty
        markers, ``standard`` depth).  R2 will require byte-identical
        realizer output between this sentinel and ``default_neutral_v1``.
        """
        return cls(
            register_id="__unregistered__",
            version="0.0.0",
            description="In-memory sentinel; never serialised to disk.",
            display_name="Unregistered",
            depth_preference="standard",
            realizer_overrides={},
            discourse_markers=DiscourseMarkers(),
            mastery_report_sha256="",
        )


def load_register_pack(
    register_id: str,
    *,
    search_paths: Iterable[Path | str] | None = None,
    require_ratified: bool | None = None,
) -> RegisterPack:
    """Load a register pack and construct its :class:`RegisterPack`.

    Args:
        register_id: Pack identifier (e.g. ``"default_neutral_v1"``).
            The loader looks for ``<register_id>.json`` in each search
            path.
        search_paths: Iterable of directories to search.  Default is the
            built-in ``packs/register/`` directory.  Earlier paths take
            precedence.
        require_ratified: When ``True``, refuse packs whose
            ``mastery_report_sha256`` is empty.  When ``None`` (default),
            require ratification unless the env var
            ``CORE_ALLOW_UNRATIFIED_REGISTER=1`` is set.  When ``False``,
            never require ratification (for tests).

    Raises:
        RegisterPackError: On any bounds violation, missing file,
            malformed JSON, or — in production mode — unverified seal.
    """
    paths = _resolve_search_paths(search_paths)
    pack_path = _find_pack(register_id, paths)
    raw = _read_json(pack_path)
    _validate_envelope(raw, register_id)
    _validate_ratification(raw, register_id, require_ratified, pack_path)
    depth = _validate_depth_preference(raw["depth_preference"], register_id)
    overrides = _validate_overrides(raw["realizer_overrides"], register_id)
    markers = _build_discourse_markers(raw["discourse_markers"], register_id)
    return RegisterPack(
        register_id=str(raw["register_id"]),
        version=str(raw["version"]),
        description=str(raw["description"]),
        display_name=str(raw["display_name"]),
        depth_preference=depth,
        realizer_overrides=overrides,
        discourse_markers=markers,
        mastery_report_sha256=str(raw.get("mastery_report_sha256", "")),
    )


def available_register_packs(
    search_paths: Iterable[Path | str] | None = None,
) -> list[dict[str, object]]:
    """Return a sorted list of metadata dicts for every discoverable pack."""
    paths = _resolve_search_paths(search_paths)
    seen: dict[str, dict[str, object]] = {}
    for d in paths:
        if not d.is_dir():
            continue
        for entry in sorted(d.glob("*.json")):
            if entry.name.endswith(".mastery_report.json"):
                continue
            try:
                raw = _read_json(entry)
            except RegisterPackError:
                continue
            if not isinstance(raw, dict):
                continue
            if "schema_version" not in raw or "register_id" not in raw:
                continue
            register_id = str(raw.get("register_id", entry.stem))
            if register_id in seen:
                continue
            seen[register_id] = {
                "register_id": register_id,
                "version": str(raw.get("version", "")),
                "description": str(raw.get("description", "")),
                "ratified": bool(raw.get("mastery_report_sha256")),
                "path": str(entry),
            }
    return sorted(seen.values(), key=lambda d: str(d["register_id"]))


def verify_register_pack_seal(
    register_id: str,
    *,
    search_paths: Iterable[Path | str] | None = None,
) -> bool:
    """Return True iff the pack's companion mastery report is self-sealed
    and the pack's declared SHA matches the report's SHA.

    Read-only.  Does not raise on mismatch — callers that want a hard
    failure should use :func:`load_register_pack` with
    ``require_ratified=True``.
    """
    paths = _resolve_search_paths(search_paths)
    try:
        pack_path = _find_pack(register_id, paths)
    except RegisterPackError:
        return False
    try:
        raw = _read_json(pack_path)
    except RegisterPackError:
        return False
    declared = str(raw.get("mastery_report_sha256", ""))
    if not declared:
        return False
    report_path = pack_path.parent / f"{register_id}.mastery_report.json"
    if not report_path.is_file():
        return False
    try:
        report = _read_json(report_path)
    except RegisterPackError:
        return False
    if report.get("report_sha256") != declared:
        return False
    return verify_seal(report, sha_field="report_sha256")


# ---------- internals ----------


def _resolve_search_paths(
    search_paths: Iterable[Path | str] | None,
) -> tuple[Path, ...]:
    if search_paths is None:
        return _DEFAULT_SEARCH_PATHS
    return tuple(Path(p) for p in search_paths)


def _find_pack(register_id: str, paths: tuple[Path, ...]) -> Path:
    if (
        not register_id
        or not isinstance(register_id, str)
        or "/" in register_id
        or "\\" in register_id
        or ".." in register_id
    ):
        raise RegisterPackError(
            f"invalid register_id: {safe_pack_id(register_id)!r}"
        )
    for d in paths:
        candidate = d / f"{register_id}.json"
        if candidate.is_file():
            return candidate
    raise RegisterPackError(
        f"register pack {safe_pack_id(register_id)!r} not found in "
        f"{[str(p) for p in paths]}"
    )


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise RegisterPackError(f"failed to read pack {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegisterPackError(f"pack {path} did not deserialize to a dict")
    return data


def _validate_envelope(raw: dict, register_id: str) -> None:
    required = (
        "register_id",
        "version",
        "description",
        "schema_version",
        "display_name",
        "depth_preference",
        "realizer_overrides",
        "discourse_markers",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r} missing required fields: "
            f"{missing}"
        )
    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: unsupported schema_version "
            f"{raw.get('schema_version')!r} (expected {_SCHEMA_VERSION!r})"
        )
    if raw.get("register_id") != register_id:
        raise RegisterPackError(
            f"pack file declares register_id="
            f"{safe_pack_id(raw.get('register_id'))!r} but was requested as "
            f"{safe_pack_id(register_id)!r}"
        )


def _validate_ratification(
    raw: dict,
    register_id: str,
    require_ratified: bool | None,
    pack_path: Path,
) -> None:
    if require_ratified is False:
        return
    if require_ratified is None:
        require_ratified = (
            os.environ.get("CORE_ALLOW_UNRATIFIED_REGISTER") != "1"
        )
    if not require_ratified:
        return
    declared_sha = raw.get("mastery_report_sha256", "")
    if not declared_sha:
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r} is not ratified "
            "(mastery_report_sha256 empty); set "
            "CORE_ALLOW_UNRATIFIED_REGISTER=1 for development, or ratify "
            "via scripts/ratify_register_packs.py."
        )
    report_path = pack_path.parent / f"{register_id}.mastery_report.json"
    if not report_path.is_file():
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r} declares "
            f"mastery_report_sha256={str(declared_sha)[:12]}... but companion "
            f"report file {report_path.name!r} is missing"
        )
    try:
        with report_path.open("r", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: failed to read companion "
            f"report: {exc}"
        ) from exc
    if not isinstance(report, dict):
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: companion report is not a "
            "JSON object"
        )
    if report.get("report_sha256") != declared_sha:
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: companion report SHA "
            f"{str(report.get('report_sha256'))[:12]}... does not match pack's "
            f"declared {str(declared_sha)[:12]}..."
        )
    if not verify_seal(report, sha_field="report_sha256"):
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: companion report failed "
            "self-seal verification"
        )
    if not report.get("ratified", False):
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: companion report has "
            "ratified=False"
        )


def _validate_depth_preference(value: object, register_id: str) -> str:
    if not isinstance(value, str) or value not in _ALLOWED_DEPTH_PREFERENCES:
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: depth_preference="
            f"{value!r} not in {sorted(_ALLOWED_DEPTH_PREFERENCES)}"
        )
    return value


def _validate_overrides(
    value: object, register_id: str,
):
    if not isinstance(value, dict):
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: realizer_overrides must be "
            f"a dict, got {type(value).__name__}"
        )
    cleaned: dict[str, object] = {}
    for k, v in value.items():
        if not isinstance(k, str) or not k or len(k) > _MAX_OVERRIDE_KEY_LEN:
            raise RegisterPackError(
                f"pack {safe_pack_id(register_id)!r}: realizer_overrides "
                f"key must be a non-empty string ≤ {_MAX_OVERRIDE_KEY_LEN} "
                f"chars, got {safe_pack_id(k)!r}"
            )
        if k == _PER_INTENT_KEY:
            cleaned[k] = _validate_per_intent_block(v, register_id)
            continue
        cleaned[k] = _validate_flat_override_value(v, k, register_id)
    return _frozen_mapping(cleaned)


def _validate_flat_override_value(
    v: object, key: str, register_id: str,
) -> int | str | bool:
    """Validate a flat ``realizer_overrides`` value.

    Allowed types: ``bool`` (only for the closed
    :data:`_BOOLEAN_OVERRIDE_KEYS` set, ADR-0077), ``int`` (bounded), or
    non-empty bounded ``str``.  Shared between top-level overrides and
    ``per_intent`` sub-dicts.
    """
    if isinstance(v, bool):
        if key not in _BOOLEAN_OVERRIDE_KEYS:
            raise RegisterPackError(
                f"pack {safe_pack_id(register_id)!r}: realizer_overrides"
                f"[{safe_pack_id(key)!r}] bool is not an allowed value type "
                f"for this key (boolean-keys allow-list: "
                f"{sorted(_BOOLEAN_OVERRIDE_KEYS)})"
            )
        return v
    if isinstance(v, int):
        if v < _OVERRIDE_INT_MIN or v > _OVERRIDE_INT_MAX:
            raise RegisterPackError(
                f"pack {safe_pack_id(register_id)!r}: realizer_overrides"
                f"[{safe_pack_id(key)!r}] int value out of range"
                f" [{_OVERRIDE_INT_MIN}, {_OVERRIDE_INT_MAX}]"
            )
        return v
    if (
        not isinstance(v, str)
        or not v
        or len(v) > _MAX_OVERRIDE_VALUE_LEN
    ):
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: realizer_overrides"
            f"[{safe_pack_id(key)!r}] must be a non-empty string ≤ "
            f"{_MAX_OVERRIDE_VALUE_LEN} chars or an int"
        )
    return v


def _validate_per_intent_block(
    value: object, register_id: str,
) -> Mapping[str, Mapping[str, int | str | bool]]:
    """Validate the ``per_intent`` nested dict structure.

    Intent-name semantic validation (must match ``IntentTag``) lives
    in the ratify gate.  The loader only enforces structural bounds.
    """
    if not isinstance(value, dict):
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: realizer_overrides"
            f".per_intent must be a dict, got {type(value).__name__}"
        )
    cleaned: dict[str, Mapping[str, int | str]] = {}
    for intent_name, sub in value.items():
        if (
            not isinstance(intent_name, str)
            or not intent_name
            or len(intent_name) > _MAX_OVERRIDE_KEY_LEN
        ):
            raise RegisterPackError(
                f"pack {safe_pack_id(register_id)!r}: realizer_overrides"
                f".per_intent key must be a non-empty string ≤ "
                f"{_MAX_OVERRIDE_KEY_LEN} chars, got "
                f"{safe_pack_id(intent_name)!r}"
            )
        if not isinstance(sub, dict):
            raise RegisterPackError(
                f"pack {safe_pack_id(register_id)!r}: realizer_overrides"
                f".per_intent[{safe_pack_id(intent_name)!r}] must be a dict"
            )
        sub_cleaned: dict[str, int | str] = {}
        for sub_k, sub_v in sub.items():
            if (
                not isinstance(sub_k, str)
                or not sub_k
                or len(sub_k) > _MAX_OVERRIDE_KEY_LEN
            ):
                raise RegisterPackError(
                    f"pack {safe_pack_id(register_id)!r}: realizer_overrides"
                    f".per_intent[{safe_pack_id(intent_name)!r}] key must be "
                    f"a non-empty string ≤ {_MAX_OVERRIDE_KEY_LEN} chars"
                )
            if sub_k == _PER_INTENT_KEY:
                raise RegisterPackError(
                    f"pack {safe_pack_id(register_id)!r}: realizer_overrides"
                    f".per_intent[{safe_pack_id(intent_name)!r}] cannot "
                    "nest a per_intent block (only one level of nesting "
                    "is allowed)"
                )
            sub_cleaned[sub_k] = _validate_flat_override_value(
                sub_v, sub_k, register_id,
            )
        cleaned[intent_name] = _frozen_mapping(sub_cleaned)  # type: ignore[assignment]
    return cleaned


def _build_discourse_markers(
    value: object, register_id: str,
) -> DiscourseMarkers:
    if not isinstance(value, dict):
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: discourse_markers must be "
            f"a dict, got {type(value).__name__}"
        )
    missing = [b for b in _MARKER_BUCKETS if b not in value]
    if missing:
        raise RegisterPackError(
            f"pack {safe_pack_id(register_id)!r}: discourse_markers missing "
            f"buckets: {missing}"
        )
    buckets: dict[str, tuple[str, ...]] = {}
    for bucket in _MARKER_BUCKETS:
        items = value[bucket]
        if not isinstance(items, list):
            raise RegisterPackError(
                f"pack {safe_pack_id(register_id)!r}: discourse_markers"
                f".{bucket} must be a list"
            )
        if len(items) > _MAX_MARKERS_PER_BUCKET:
            raise RegisterPackError(
                f"pack {safe_pack_id(register_id)!r}: discourse_markers"
                f".{bucket} has {len(items)} entries; max is "
                f"{_MAX_MARKERS_PER_BUCKET}"
            )
        cleaned: list[str] = []
        for i, item in enumerate(items):
            # Empty-string entries are legitimate: they let the seeded
            # selector pick "no marker this turn" within an otherwise
            # populated bucket (ADR-0071).  Bounds: must be a string
            # ≤ _MAX_MARKER_LEN chars.
            if not isinstance(item, str) or len(item) > _MAX_MARKER_LEN:
                raise RegisterPackError(
                    f"pack {safe_pack_id(register_id)!r}: discourse_markers"
                    f".{bucket}[{i}] must be a string ≤ "
                    f"{_MAX_MARKER_LEN} chars"
                )
            cleaned.append(item)
        buckets[bucket] = tuple(cleaned)
    return DiscourseMarkers(
        openings=buckets["openings"],
        transitions=buckets["transitions"],
        closings=buckets["closings"],
    )


class _FrozenMapping(Mapping[str, object]):
    """Read-only mapping returned by :func:`_frozen_mapping`."""

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"_FrozenMapping({self._data!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _FrozenMapping):
            return self._data == other._data
        if isinstance(other, Mapping):
            return dict(self._data) == dict(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(tuple(sorted(self._data.items())))


def _frozen_mapping(data):
    return _FrozenMapping(dict(data))


#: Module-level unregistered sentinel.  Importable by composers so they
#: can use it as a keyword-only default without re-evaluating
#: :meth:`RegisterPack.unregistered` on every call.  Frozen and shared.
UNREGISTERED: RegisterPack = RegisterPack.unregistered()


__all__ = (
    "DiscourseMarkers",
    "RegisterPack",
    "RegisterPackError",
    "UNREGISTERED",
    "available_register_packs",
    "load_register_pack",
    "verify_register_pack_seal",
)
