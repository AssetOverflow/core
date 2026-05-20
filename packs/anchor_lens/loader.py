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
* Bounds checks (allowed ``primary_substrate`` / ``substrate``,
  list-shaped preferences or scalar ``atom``, ≤64-char atoms,
  ≤64-char label) are enforced before any field of the returned
  :class:`AnchorLens` is observable to runtime code.
* When ``require_ratified=True`` and the pack's
  ``mastery_report_sha256`` is empty, the loader refuses.  Development
  environments may set ``CORE_ALLOW_UNRATIFIED_ANCHOR_LENS=1`` to
  bypass.
* :meth:`AnchorLens.unanchored` returns a frozen sentinel matching
  the in-memory shape of ``default_unanchored_v1``.  At L1.2 no
  composer reads this module (pinned by
  ``tests/test_anchor_lens_pack_seam.py``).

Schema versions supported:
  v1-legacy  fields: display_name, primary_substrate,
             semantic_domain_preferences (list), cognitive_mode_label
  v2         fields: substrate, atom (scalar), cognitive_mode,
             source_entry_id, pair_lens_id, ratification_method
  Both are accepted.  New packs should use v2.  The dataclass always
  exposes the v2 field names; legacy fields are normalised on load.

Mirror of ``packs/register/loader.py`` — anchor lens is the
substantive-axis sibling of the presentation-axis register class.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from formation.hashing import verify_seal

_DEFAULT_SEARCH_PATHS: tuple[Path, ...] = (
    Path(__file__).resolve().parent,
)

_ALLOWED_SUBSTRATES: frozenset[str] = frozenset({"grc", "he", "en", "none"})
_SCHEMA_VERSION: str = "1.0.0"
_MAX_ATOM_LEN: int = 64
_MAX_PREFERENCES: int = 64
_MAX_LABEL_LEN: int = 64
_MAX_DESCRIPTION_LEN: int = 1024
_MAX_DISPLAY_NAME_LEN: int = 128


class AnchorLensError(Exception):
    """Raised when a pack file is invalid or cannot be loaded."""


def safe_pack_id(value: object) -> str:
    """Return a printable, length-capped version of a pack id."""
    s = str(value) if value is not None else ""
    return s[:64]


@dataclass(frozen=True)
class AnchorLens:
    """Frozen substantive-axis pack.

    Field names follow the v2 schema.  Packs that still use v1-legacy
    field names are normalised by the loader before construction.
    """

    lens_id: str
    version: str
    description: str
    # v2 fields (canonical)
    substrate: str = "none"
    atom: str = ""
    cognitive_mode: str = ""
    source_entry_id: str = ""
    pair_lens_id: str | None = None
    ratification_method: str = "anchor_lens_lifts_proposition"
    mastery_report_sha256: str = ""

    def is_unanchored(self) -> bool:
        """True for the in-memory sentinel returned by :meth:`unanchored`.

        Distinguishes the in-memory ``__unanchored__`` sentinel from the
        on-disk ``default_unanchored_v1`` pack — both are structurally
        null but only the in-memory one carries the sentinel lens_id.
        """
        return self.lens_id == "__unanchored__"

    def is_null_lens(self) -> bool:
        """True iff structurally null (no atom, ``substrate='none'``)."""
        return (
            self.substrate == "none"
            and self.atom == ""
            and self.cognitive_mode == ""
        )

    # v1-legacy attribute aliases (back-compat for consumers not yet
    # migrated to v2 field names).  Read-only views over canonical v2.
    @property
    def primary_substrate(self) -> str:
        return self.substrate

    @property
    def semantic_domain_preferences(self) -> tuple[str, ...]:
        return (self.atom,) if self.atom else ()

    @property
    def cognitive_mode_label(self) -> str:
        return self.cognitive_mode

    @classmethod
    def unanchored(cls) -> "AnchorLens":
        """Return a frozen in-memory sentinel lens.

        Structurally null and tagged with the reserved sentinel
        ``lens_id='__unanchored__'`` to distinguish from the disk-ratified
        ``default_unanchored_v1`` pack.
        """
        return cls(
            lens_id="__unanchored__",
            version="1.0.0",
            description="In-memory unanchored sentinel.",
            substrate="none",
            atom="",
            cognitive_mode="",
            source_entry_id="",
            pair_lens_id=None,
            ratification_method="anchor_lens_lifts_proposition",
            mastery_report_sha256="",
        )


def _normalise_raw(raw: dict, lens_id: str) -> dict:
    """Normalise v1-legacy field names to v2 in-place and return raw.

    Transforms:
      primary_substrate -> substrate
      semantic_domain_preferences[0] -> atom  (first entry used; must be
          exactly one entry for a clean migration)
      cognitive_mode_label -> cognitive_mode
      display_name is dropped (informational only)
    """
    # substrate
    if "substrate" not in raw and "primary_substrate" in raw:
        raw["substrate"] = raw["primary_substrate"]
    # atom (scalar) from list
    if "atom" not in raw and "semantic_domain_preferences" in raw:
        prefs = raw["semantic_domain_preferences"]
        if isinstance(prefs, list) and prefs:
            raw["atom"] = prefs[0]
        else:
            raw["atom"] = ""
    # cognitive_mode
    if "cognitive_mode" not in raw and "cognitive_mode_label" in raw:
        raw["cognitive_mode"] = raw["cognitive_mode_label"]
    return raw


def _validate_envelope(raw: dict, lens_id: str) -> None:
    """Validate required fields and value bounds.  Accepts v1 and v2."""
    # After normalisation every pack must have these:
    required_post_normalise = (
        "lens_id",
        "version",
        "description",
        "schema_version",
        "substrate",
        "atom",
    )
    missing = [k for k in required_post_normalise if k not in raw]
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
            f"<= {_MAX_DESCRIPTION_LEN} chars"
        )
    substrate = raw.get("substrate", "")
    if substrate not in _ALLOWED_SUBSTRATES:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: substrate {substrate!r} not in "
            f"{sorted(_ALLOWED_SUBSTRATES)}"
        )
    atom = raw.get("atom", "")
    if not isinstance(atom, str) or len(atom) > _MAX_ATOM_LEN:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: atom must be a string "
            f"<= {_MAX_ATOM_LEN} chars"
        )
    # Non-null lens packs (substrate != 'none') must declare a non-empty
    # atom — the engagement path can't fire without one.
    if substrate != "none" and not atom:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: atom must be non-empty when "
            f"substrate is {substrate!r}"
        )
    cognitive_mode = raw.get("cognitive_mode", "")
    if not isinstance(cognitive_mode, str) or len(cognitive_mode) > _MAX_LABEL_LEN:
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r}: cognitive_mode must be a string "
            f"<= {_MAX_LABEL_LEN} chars"
        )


def _validate_lens_id_for_fs(lens_id: object) -> None:
    """Reject path-traversal / slash / empty / non-string lens ids."""
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


def _find_pack_path(lens_id: str, search_paths: Iterable[Path]) -> Path:
    _validate_lens_id_for_fs(lens_id)
    for directory in search_paths:
        candidate = Path(directory) / f"{lens_id}.json"
        if candidate.exists():
            return candidate
    raise AnchorLensError(
        f"anchor-lens pack {safe_pack_id(lens_id)!r} not found in search paths"
    )


def load_anchor_lens(
    lens_id: str,
    *,
    search_paths: Iterable[Path | str] | None = None,
    require_ratified: bool | None = None,
) -> AnchorLens:
    """Load, validate, and return a frozen :class:`AnchorLens`.

    Parameters
    ----------
    lens_id:
        The pack identifier, e.g. ``"grc_logos_v1"``.
    search_paths:
        Directories to search for ``<lens_id>.json``.  Defaults to the
        directory containing this module.
    require_ratified:
        If ``True``, refuse packs with an empty ``mastery_report_sha256``.
        If ``None`` (default), falls back to the
        ``CORE_ALLOW_UNRATIFIED_ANCHOR_LENS`` environment variable
        (refuse unless the variable is set to ``"1"`` or ``"true"`` or
        ``"yes"`` case-insensitively).
    """
    resolved_paths: list[Path] = [
        Path(p) for p in (search_paths or _DEFAULT_SEARCH_PATHS)
    ]
    pack_path = _find_pack_path(lens_id, resolved_paths)
    raw: dict = json.loads(pack_path.read_text(encoding="utf-8"))

    # Normalise legacy v1 field names to v2 before validation
    raw = _normalise_raw(raw, lens_id)

    _validate_envelope(raw, lens_id)

    if require_ratified is None:
        env = os.environ.get("CORE_ALLOW_UNRATIFIED_ANCHOR_LENS", "").lower()
        require_ratified = env not in ("1", "true", "yes")

    if require_ratified and not raw.get("mastery_report_sha256", ""):
        raise AnchorLensError(
            f"pack {safe_pack_id(lens_id)!r} is not ratified "
            f"(mastery_report_sha256 is empty).  Run "
            f"scripts/ratify_anchor_lens_packs.py or set "
            f"CORE_ALLOW_UNRATIFIED_ANCHOR_LENS=1 for development."
        )

    # Companion-SHA agreement check: when ratification is required and a
    # SHA is declared, the declared SHA must match the on-disk mastery
    # report's report_sha256.  Tamper-evidence boundary per ADR-0073b.
    if require_ratified and raw.get("mastery_report_sha256", ""):
        declared = str(raw.get("mastery_report_sha256", ""))
        report_path = pack_path.parent / f"{lens_id}.mastery_report.json"
        if report_path.is_file():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                report_sha = str(report.get("report_sha256", ""))
                if report_sha != declared:
                    raise AnchorLensError(
                        f"pack {safe_pack_id(lens_id)!r}: declared "
                        f"mastery_report_sha256 does not match companion "
                        f"report's report_sha256"
                    )
            except (OSError, json.JSONDecodeError) as exc:
                raise AnchorLensError(
                    f"pack {safe_pack_id(lens_id)!r}: companion mastery "
                    f"report unreadable: {exc}"
                ) from exc

    return AnchorLens(
        lens_id=raw["lens_id"],
        version=raw["version"],
        description=raw["description"],
        substrate=raw.get("substrate", "none"),
        atom=raw.get("atom", ""),
        cognitive_mode=raw.get("cognitive_mode", ""),
        source_entry_id=raw.get("source_entry_id", ""),
        pair_lens_id=raw.get("pair_lens_id"),
        ratification_method=raw.get(
            "ratification_method", "anchor_lens_lifts_proposition"
        ),
        mastery_report_sha256=raw.get("mastery_report_sha256", ""),
    )


# Module-level singleton sentinel (v1 back-compat).  Consumers that
# imported ``UNANCHORED`` directly continue to work; new code should
# prefer ``AnchorLens.unanchored()``.
UNANCHORED: "AnchorLens" = AnchorLens.unanchored()


def verify_anchor_lens_seal(
    lens_id: str,
    *,
    search_paths: Iterable[Path | str] | None = None,
) -> bool:
    """Return True iff the pack's companion mastery report is self-sealed
    and the pack's declared SHA matches the report's SHA.

    Read-only; never raises on mismatch — callers that want a hard
    failure should use :func:`load_anchor_lens` with ``require_ratified=True``.
    """
    resolved_paths: list[Path] = [
        Path(p) for p in (search_paths or _DEFAULT_SEARCH_PATHS)
    ]
    try:
        pack_path = _find_pack_path(lens_id, resolved_paths)
    except AnchorLensError:
        return False
    try:
        raw = json.loads(pack_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    declared = str(raw.get("mastery_report_sha256", ""))
    if not declared:
        return False
    report_path = pack_path.parent / f"{lens_id}.mastery_report.json"
    if not report_path.is_file():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if report.get("report_sha256") != declared:
        return False
    return verify_seal(report, sha_field="report_sha256")


def available_anchor_lens_packs(
    search_paths: Iterable[Path | str] | None = None,
) -> list[dict]:
    """Return summary dicts for all ``.json`` packs in the search paths.

    Each dict carries the minimum fields callers need for listing UI:
    ``lens_id``, ``ratified`` (bool from non-empty ``mastery_report_sha256``),
    ``primary_substrate`` (v1 name back-compat for stable consumers),
    and ``substrate`` (v2 canonical).
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
                raw = _normalise_raw(raw, stem)
            except (OSError, json.JSONDecodeError):
                continue
            substrate = raw.get("substrate", "none")
            summaries.append({
                "lens_id": stem,
                "ratified": bool(raw.get("mastery_report_sha256", "")),
                "substrate": substrate,
                "primary_substrate": substrate,  # v1 back-compat
            })
    return summaries
