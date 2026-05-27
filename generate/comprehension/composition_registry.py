"""CW-2 — runtime composition registry loader.

Reads ``{pack}/compositions.jsonl`` (compiled by
:mod:`language_packs.compile_compositions`) and exposes a frozen lookup
surface for the recognizer/injector path.

Structural twin of :mod:`generate.comprehension.frame_registry` plus
two extra guards required by ADR-0169 / ADR-0169.1:

1. **Allowlist enforced at load** — any entry whose
   ``composition_category`` falls outside
   :data:`teaching.math_composition_proposal.SAFE_COMPOSITION_CATEGORIES`
   raises :class:`WrongCompositionCategory`. Defense in depth: protects
   against pack edits that bypass the handler's own enforcement.

2. **Polarity respected** — ``polarity: "falsifies"`` entries are
   loaded and exposed; consumers MUST suppress an injection that would
   have fired without the entry. Silently treating ``falsifies`` as
   ``affirms`` is a discipline violation.

Trust boundary identical to FrameRegistry: read-only over reviewed pack;
no fallback to unsigned paths.
"""

from __future__ import annotations

import hashlib
import json
import os
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from teaching.math_composition_ratification import SAFE_COMPOSITION_CATEGORIES


class CompositionRegistryLoadError(ValueError):
    """Raised on any load-time failure (checksum mismatch, malformed entry)."""


class WrongCompositionCategory(CompositionRegistryLoadError):
    """Raised when a compiled entry carries a category outside the allowlist."""


Polarity = Literal["affirms", "falsifies"]


@dataclass(frozen=True, slots=True)
class CompositionRegistryEntry:
    surface_pattern: str
    composition_category: str
    polarity: Polarity
    provenance: str


@dataclass(frozen=True, slots=True)
class CompositionRegistry:
    by_pattern: Mapping[str, CompositionRegistryEntry]
    by_category: Mapping[str, tuple[CompositionRegistryEntry, ...]]
    pack_manifest_sha256: str
    source_pack_id: str

    def is_empty(self) -> bool:
        return not self.by_pattern

    def __hash__(self) -> int:
        return hash((self.pack_manifest_sha256, self.source_pack_id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CompositionRegistry):
            return NotImplemented
        return (
            dict(self.by_pattern) == dict(other.by_pattern)
            and self.pack_manifest_sha256 == other.pack_manifest_sha256
            and self.source_pack_id == other.source_pack_id
        )


_CACHE: dict[tuple[str, int, str], CompositionRegistry] = {}

_DEFAULT_PACK_RELPATH = Path("language_packs") / "data" / "en_core_math_v1"

_VALID_POLARITIES: frozenset[str] = frozenset({"affirms", "falsifies"})


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    candidate = here
    for _ in range(10):
        candidate = candidate.parent
        if (candidate / "pyproject.toml").exists() or (candidate / "setup.cfg").exists():
            return candidate
    return here.parent.parent.parent


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _empty_registry(pack_id: str, manifest_sha256: str) -> CompositionRegistry:
    return CompositionRegistry(
        by_pattern=types.MappingProxyType({}),
        by_category=types.MappingProxyType({}),
        pack_manifest_sha256=manifest_sha256,
        source_pack_id=pack_id,
    )


def load_composition_registry(pack_path: Path | None = None) -> CompositionRegistry:
    """Load and cache the math pack's composition registry.

    When ``{pack}/compositions.jsonl`` is absent or empty, returns an
    empty registry (no-op semantics).

    When the manifest declares ``composition_checksum`` it MUST match
    the on-disk compiled bytes; mismatch raises
    :class:`CompositionRegistryLoadError`.

    Any entry whose ``composition_category`` is outside
    :data:`SAFE_COMPOSITION_CATEGORIES` raises
    :class:`WrongCompositionCategory` (defense in depth).

    Any entry whose ``polarity`` is not in
    ``{"affirms", "falsifies"}`` raises
    :class:`CompositionRegistryLoadError`.

    Caches per (resolved_path, mtime_ns, sha256).
    """
    resolved = (
        (pack_path if isinstance(pack_path, Path) else Path(pack_path)).resolve()
        if pack_path is not None
        else (_repo_root() / _DEFAULT_PACK_RELPATH).resolve()
    )

    manifest_path = resolved / "manifest.json"
    compiled_path = resolved / "compositions.jsonl"
    if not manifest_path.exists():
        raise CompositionRegistryLoadError(f"Pack manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pack_id: str = manifest.get("pack_id", resolved.name)
    declared_sha256 = manifest.get("composition_checksum")

    if not compiled_path.exists():
        if declared_sha256:
            raise CompositionRegistryLoadError(
                f"Manifest declares composition_checksum={declared_sha256!r} but "
                f"compositions.jsonl is missing at {compiled_path}"
            )
        return _empty_registry(pack_id, manifest.get("checksum", ""))

    compiled_bytes = compiled_path.read_bytes()
    actual_sha256 = _sha256_bytes(compiled_bytes)
    mtime_ns = os.stat(compiled_path).st_mtime_ns
    cache_key = (str(resolved), mtime_ns, actual_sha256)

    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    if declared_sha256 and declared_sha256 != actual_sha256:
        raise CompositionRegistryLoadError(
            f"Composition checksum mismatch for {resolved!r}: "
            f"declared={declared_sha256!r}, actual={actual_sha256!r}"
        )

    entries: list[CompositionRegistryEntry] = []
    if compiled_bytes:
        for line in compiled_bytes.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)

            category = rec.get("composition_category")
            if category not in SAFE_COMPOSITION_CATEGORIES:
                raise WrongCompositionCategory(
                    f"Composition entry has category {category!r} outside "
                    f"SAFE_COMPOSITION_CATEGORIES="
                    f"{sorted(SAFE_COMPOSITION_CATEGORIES)!r}; "
                    "load-time allowlist enforced per ADR-0169 defense in depth"
                )

            polarity = rec.get("polarity")
            if polarity not in _VALID_POLARITIES:
                raise CompositionRegistryLoadError(
                    f"Composition entry has invalid polarity {polarity!r}; "
                    f"must be one of {sorted(_VALID_POLARITIES)!r}"
                )

            entries.append(
                CompositionRegistryEntry(
                    surface_pattern=str(rec["surface_pattern"]),
                    composition_category=str(category),
                    polarity=polarity,
                    provenance=str(rec.get("provenance", "")),
                )
            )

    by_pattern_mut: dict[str, CompositionRegistryEntry] = {}
    by_cat_mut: dict[str, list[CompositionRegistryEntry]] = {}
    for entry in entries:
        # Pattern identity is the case-sensitive surface pattern — these
        # are structural shape strings, not natural-language surfaces.
        key = entry.surface_pattern
        existing = by_pattern_mut.get(key)
        if existing is not None and (
            existing.composition_category != entry.composition_category
            or existing.polarity != entry.polarity
        ):
            raise CompositionRegistryLoadError(
                f"Composition pattern {key!r} carries conflicting entries: "
                f"({existing.composition_category!r}, {existing.polarity!r}) vs "
                f"({entry.composition_category!r}, {entry.polarity!r})"
            )
        by_pattern_mut[key] = entry
        by_cat_mut.setdefault(entry.composition_category, []).append(entry)

    by_category_frozen: dict[str, tuple[CompositionRegistryEntry, ...]] = {
        cat: tuple(sorted(lst, key=lambda e: e.surface_pattern))
        for cat, lst in by_cat_mut.items()
    }

    registry = CompositionRegistry(
        by_pattern=types.MappingProxyType(by_pattern_mut),
        by_category=types.MappingProxyType(by_category_frozen),
        pack_manifest_sha256=actual_sha256,
        source_pack_id=pack_id,
    )
    _CACHE[cache_key] = registry
    return registry


def lookup(
    registry: CompositionRegistry, surface_pattern: str
) -> CompositionRegistryEntry | None:
    """Exact-match lookup by surface pattern (case-sensitive, structural)."""
    return registry.by_pattern.get(surface_pattern)


def is_affirmed(registry: CompositionRegistry, surface_pattern: str) -> bool:
    """Return True only when an entry exists AND its polarity is ``affirms``.

    Convenience for consumer code: a falsifying entry returns False (the
    consumer must suppress injection that would have fired anyway).
    Absence also returns False (no opinion).
    """
    entry = registry.by_pattern.get(surface_pattern)
    return entry is not None and entry.polarity == "affirms"


def is_falsified(registry: CompositionRegistry, surface_pattern: str) -> bool:
    """Return True only when an entry exists AND its polarity is ``falsifies``."""
    entry = registry.by_pattern.get(surface_pattern)
    return entry is not None and entry.polarity == "falsifies"


def clear_cache() -> None:
    """Test hook — drop the per-process cache."""
    _CACHE.clear()


__all__ = [
    "CompositionRegistry",
    "CompositionRegistryEntry",
    "CompositionRegistryLoadError",
    "WrongCompositionCategory",
    "Polarity",
    "load_composition_registry",
    "lookup",
    "is_affirmed",
    "is_falsified",
    "clear_cache",
]
