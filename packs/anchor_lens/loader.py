"""Anchor-lens pack loader (ADR-0073b, Plan Phase L1.2).

Reads a ratified anchor-lens pack from disk and constructs a frozen
:class:`AnchorLens` for the runtime.  See
``docs/decisions/ADR-0073-anchor-lens-substrate.md`` (umbrella) and
``docs/decisions/ADR-0073b-anchor-lens-class-loader.md`` (this phase)
for context.

Loader contract (trust boundary):

* Anchor-lens packs are composer-side only.  They parameterise the
  proposition-construction step at L1.3 and never contribute to the
  runtime manifold, ``boundary_ids``, safety/ethics composition, or
  the trace hash directly (the *output* trace hash deliberately moves
  when the lens changes because the proposition changes — but the
  hash function does not depend on the lens object).
* The loader never mutates a pack on disk.  Pack creation goes through
  ``scripts/ratify_anchor_lens_packs.py``.
* Bounds checks (allowed ``primary_substrate``, list-shaped
  preferences, ≤64-char atoms, ≤64-char label) are enforced before
  any field of the returned :class:`AnchorLens` is observable to
  runtime code.
* When ``require_ratified=True`` and the pack's
  ``mastery_report_sha256`` is empty, the loader refuses.  Development
  environments may set ``CORE_ALLOW_UNRATIFIED_ANCHOR_LENS=1`` to
  bypass.
* :meth:`AnchorLens.unanchored` returns a frozen sentinel matching
  the in-memory shape of ``default_unanchored_v1``.  At L1.2 no
  composer reads this module (pinned by
  ``tests/test_anchor_lens_pack_seam.py``).

Mirror of ``packs/register/loader.py`` — anchor lens is the
substantive-axis sibling of the presentation-axis register class.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core._safe_display import safe_pack_id
from formation.hashing import verify_seal


class AnchorLensError(ValueError):
    """Raised when an anchor-lens pack is missing, malformed, or out of bounds."""


_DEFAULT_SEARCH_PATHS: tuple[Path, ...] = (
    Path(__file__).resolve().parent,
)

_ALLOWED_SUBSTRATES: frozenset[str] = frozenset(
    {"grc", "he", "en", "none"}
)
_SCHEMA_VERSION: str = "1.0.0"
_MAX_ATOM_LEN: int = 64
_MAX_PREFERENCES: int = 64
_MAX_LABEL_LEN: int = 64
_MAX_DESCRIPTION_LEN: int = 512
_MAX_DISPLAY_NAME_LEN: int = 128


@dataclass(frozen=True)
class AnchorLens:
    """Frozen substantive-axis pack.

    Composes into the proposition-construction step at L1.3; at L1.2
    nothing consumes it.  The lens directs which lemma's
    ``semantic_domains`` the composer prefers at proposition-build
    time, in English compound phrasing
    (e.g. ``"knowing-as-experience"``) — never raw non-English
    glyphs at the user surface.
    """

    lens_id: str
    version: str
    description: str
    display_name: str
    primary_substrate: str
    semantic_domain_preferences: tuple[str, ...] = ()
    cognitive_mode_label: str = ""
    mastery_report_sha256: str = ""

    def is_unanchored(self) -> bool:
        """True for the in-memory sentinel returned by :meth:`unanchored`."""
        return self.lens_id == "__unanchored__"

    def is_null_lens(self) -> bool:
        """True iff no atoms, ``primary_substrate='none'``, empty label."""
        return (
            self.primary_substrate == "none"
            and not self.semantic_domain_preferences
            and not self.cognitive_mode_label
        )

    @classmethod
    def unanchored(cls) -> "AnchorLens":
        """Return the in-memory sentinel used when no anchor lens is selected.

        Structurally identical to ``default_unanchored_v1`` (null
        preferences, ``"none"`` substrate, empty mode label).  L1.2
        requires byte-identical lane output between this sentinel and
        ``default_unanchored_v1`` — the ``anchor_lens_byte_identity_
        null_lift`` invariant.
        """
        return cls(
            lens_id="__unanchored__",
            version="0.0.0",
            description="In-memory sentinel; never serialised to disk.",
            display_name="Unanchored",
            primary_substrate="none",
            semantic_domain_preferences=(),
            cognitive_mode_label="",
            mastery_report_sha256="",
        )


def load_anchor_lens(
    lens_id: str,
    *,
    search_paths: Iterable[Path | str] | None = None,
    require_ratified: bool | None = None,
) -> AnchorLens:
    """Load an anchor-lens pack and construct its :class:`AnchorLens`.

    Args:
        lens_id: Pack identifier (e.g. ``"default_unanchored_v1"``).
            The loader looks for ``<lens_id>.json`` in each search
            path.
        search_paths: Iterable of directories to search.  Default is the
            built-in ``packs/anchor_lens/`` directory.  Earlier paths
            take precedence.
        require_ratified: When ``True``, refuse packs whose
            ``mastery_report_sha256`` is empty.  When ``None`` (default),
            require ratification unless the env var
            ``CORE_ALLOW_UNRATIFIED_ANCHOR_LENS=1`` is set.  When
            ``False``, never require ratification (for tests).

    Raises:
        AnchorLensError: On any bounds violation, missing file,
            malformed JSON, or — in production mode — unverified seal.
    """
    paths = _resolve_search_paths(search_paths)
    pack_path = _find_pack(lens_id, paths)
    raw = _read_json(pack_path)
    _validate_envelope(raw, lens_id)
    _validate_ratification(raw, lens_id, require_ratified, pack_path)
    substrate = _validate_substrate(raw["primary_substrate"], lens_id)
    preferences = _validate_preferences(
        raw["semantic_domain_preferences"], lens_id,
    )
    label = _validate_label(raw["cognitive_mode_label"], lens_id)
    return AnchorLens(
        lens_id=str(raw["lens_id"]),
        version=str(raw["version"]),
        description=str(raw["description"]),
        display_name=str(raw["display_name"]),
        primary_substrate=substrate,
        semantic_domain_preferences=preferences,
        cognitive_mode_label=label,
        mastery_report_sha256=str(raw.get("mastery_report_sha256", "")),
    )


def available_anchor_lens_packs(
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
            except AnchorLensError:
                continue
            if not isinstance(raw, dict):
                continue
            if "schema_version" not in raw or "lens_id" not in raw:
                continue
            lens_id = str(raw.get("lens_id", entry.stem))
            if lens_id in seen:
                continue
            seen[lens_id] = {
                "lens_id": lens_id,
                "version": str(raw.get("version", "")),
                "description": str(raw.get("description", "")),
                "primary_substrate": str(raw.get("primary_substrate", "")),
                "ratified": bool(raw.get("mastery_report_sha256")),
                "path": str(entry),
            }
    return sorted(seen.values(), key=lambda d: str(d["lens_id"]))


def verify_anchor_lens_seal(
    lens_id: str,
    *,
    search_paths: Iterable[Path | str] | None = None,
) -> bool:
    """Return True iff the pack's companion mastery report is self-sealed
    and the pack's declared SHA matches the report's SHA.

    Read-only.  Does not raise on mismatch — callers that want a hard
    failure should use :func:`load_anchor_lens` with
    ``require_ratified=True``.
    """
    paths = _resolve_search_paths(search_paths)
    try:
        pack_path = _find_pack(lens_id, paths)
    except AnchorLensError:
        return False
    try:
        raw = _read_json(pack_path)
    except AnchorLensError:
        return False
    declared = str(raw.get("mastery_report_sha256", ""))
    if not declared:
        return False
    report_path = pack_path.parent / f"{lens_id}.mastery_report.json"
    if not report_path.is_file():
        return False
    try:
        report = _read_json(report_path)
    except AnchorLensError:
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


def _find_pack(lens_id: str, paths: tuple[Path, ...]) -> Path:
    if (
        not lens_id
        or not isinstance(lens_id, str)
        or "/" in lens_id
        or "\\" in lens_id
        or ".." in lens_id
    ):
        raise AnchorLensError(
            f"invalid lens_id: {safe_pack_id(lens_id)!r}"
        )
    for d in paths:
        candidate = d / f"{lens_id}.json"
        if candidate.is_file():
            return candidate
    raise AnchorLensError(
        f"anchor-lens pack {safe_pack_id(lens_id)!r} not found in "
        f"{[str(p) for p in paths]}"
    )


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise AnchorLensError(f"failed to read pack {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AnchorLensError(f"pack {path} did not deserialize to a dict")
    return data


def _validate_envelope(raw: dict, lens_id: str) -> None:
    required = (
        "lens_id",
        "version",
        "description",
        "schema_version",
        "display_name",
        "primary_substrate",
        "semantic_domain_preferences",
        "cognitive_mode_label",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r} missing required fields: "
            f"{missing}"
        )
    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: unsupported schema_version "
            f"{raw.get('schema_version')!r} (expected {_SCHEMA_VERSION!r})"
        )
    if raw.get("lens_id") != lens_id:
        raise AnchorLensError(
            f"pack file declares lens_id="
            f"{safe_pack_id(raw.get('lens_id'))!r} but was requested as "
            f"{safe_pack_id(lens_id)!r}"
        )
    desc = raw.get("description", "")
    if not isinstance(desc, str) or len(desc) > _MAX_DESCRIPTION_LEN:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: description must be a string "
            f"≤ {_MAX_DESCRIPTION_LEN} chars"
        )
    display_name = raw.get("display_name", "")
    if (
        not isinstance(display_name, str)
        or not display_name
        or len(display_name) > _MAX_DISPLAY_NAME_LEN
    ):
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: display_name must be a non-empty "
            f"string ≤ {_MAX_DISPLAY_NAME_LEN} chars"
        )


def _validate_ratification(
    raw: dict,
    lens_id: str,
    require_ratified: bool | None,
    pack_path: Path,
) -> None:
    if require_ratified is False:
        return
    if require_ratified is None:
        require_ratified = (
            os.environ.get("CORE_ALLOW_UNRATIFIED_ANCHOR_LENS") != "1"
        )
    if not require_ratified:
        return
    declared_sha = raw.get("mastery_report_sha256", "")
    if not declared_sha:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r} is not ratified "
            "(mastery_report_sha256 empty); set "
            "CORE_ALLOW_UNRATIFIED_ANCHOR_LENS=1 for development, or "
            "ratify via scripts/ratify_anchor_lens_packs.py."
        )
    report_path = pack_path.parent / f"{lens_id}.mastery_report.json"
    if not report_path.is_file():
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r} declares "
            f"mastery_report_sha256={str(declared_sha)[:12]}... but companion "
            f"report file {report_path.name!r} is missing"
        )
    try:
        with report_path.open("r", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: failed to read companion "
            f"report: {exc}"
        ) from exc
    if not isinstance(report, dict):
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: companion report is not a "
            "JSON object"
        )
    if report.get("report_sha256") != declared_sha:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: companion report SHA "
            f"{str(report.get('report_sha256'))[:12]}... does not match pack's "
            f"declared {str(declared_sha)[:12]}..."
        )
    if not verify_seal(report, sha_field="report_sha256"):
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: companion report failed "
            "self-seal verification"
        )
    if not report.get("ratified", False):
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: companion report has "
            "ratified=False"
        )


def _validate_substrate(value: object, lens_id: str) -> str:
    if not isinstance(value, str) or value not in _ALLOWED_SUBSTRATES:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: primary_substrate="
            f"{value!r} not in {sorted(_ALLOWED_SUBSTRATES)}"
        )
    return value


def _validate_preferences(
    value: object, lens_id: str,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: semantic_domain_preferences "
            f"must be a list, got {type(value).__name__}"
        )
    if len(value) > _MAX_PREFERENCES:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: semantic_domain_preferences "
            f"has {len(value)} entries; max is {_MAX_PREFERENCES}"
        )
    cleaned: list[str] = []
    seen: set[str] = set()
    for i, atom in enumerate(value):
        if (
            not isinstance(atom, str)
            or not atom
            or len(atom) > _MAX_ATOM_LEN
        ):
            raise AnchorLensError(
                f"pack {safe_pack_id(lens_id)!r}: "
                f"semantic_domain_preferences[{i}] must be a non-empty "
                f"string ≤ {_MAX_ATOM_LEN} chars"
            )
        if atom in seen:
            raise AnchorLensError(
                f"pack {safe_pack_id(lens_id)!r}: "
                f"semantic_domain_preferences contains duplicate atom "
                f"{safe_pack_id(atom)!r}"
            )
        seen.add(atom)
        cleaned.append(atom)
    return tuple(cleaned)


def _validate_label(value: object, lens_id: str) -> str:
    if not isinstance(value, str) or len(value) > _MAX_LABEL_LEN:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: cognitive_mode_label must be "
            f"a string ≤ {_MAX_LABEL_LEN} chars"
        )
    return value


#: Module-level unanchored sentinel.  Importable by composers (at L1.3)
#: so they can use it as a keyword-only default without re-evaluating
#: :meth:`AnchorLens.unanchored` on every call.  Frozen and shared.
UNANCHORED: AnchorLens = AnchorLens.unanchored()


__all__ = (
    "AnchorLens",
    "AnchorLensError",
    "UNANCHORED",
    "available_anchor_lens_packs",
    "load_anchor_lens",
    "verify_anchor_lens_seal",
)
