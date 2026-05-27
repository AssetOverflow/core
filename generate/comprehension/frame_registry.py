"""CW-1 — runtime frame registry loader.

Reads ``{pack}/frames.jsonl`` (compiled by :mod:`language_packs.compile_frames`)
and exposes a frozen lookup surface for the comprehension reader's
frame-opener decision path.

Mirrors :mod:`generate.comprehension.lexicon` structurally:

- per-process cache keyed on ``(resolved_path, mtime_ns, sha256)``
- manifest checksum verification when the manifest declares
  ``frame_checksum``; backward-compatible when the field is absent
- empty / missing compiled artifact yields an empty registry rather
  than raising — preserves the no-op invariant when ``frames/`` carries
  zero reviewed entries

Trust boundary: read-only over the reviewed math pack; no engine_state
writes, no corpus mutation, no fallback to unsigned paths.
"""

from __future__ import annotations

import hashlib
import json
import os
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping


class FrameRegistryLoadError(ValueError):
    """Raised on any load-time failure (checksum mismatch, malformed entry)."""


Polarity = Literal["affirms", "falsifies"]


@dataclass(frozen=True, slots=True)
class FrameRegistryEntry:
    surface_form: str
    frame_category: str
    polarity: Polarity
    provenance: str


@dataclass(frozen=True, slots=True)
class FrameRegistry:
    by_surface: Mapping[str, FrameRegistryEntry]
    by_category: Mapping[str, tuple[FrameRegistryEntry, ...]]
    pack_manifest_sha256: str
    source_pack_id: str

    def is_empty(self) -> bool:
        return not self.by_surface

    def __hash__(self) -> int:
        return hash((self.pack_manifest_sha256, self.source_pack_id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FrameRegistry):
            return NotImplemented
        return (
            dict(self.by_surface) == dict(other.by_surface)
            and self.pack_manifest_sha256 == other.pack_manifest_sha256
            and self.source_pack_id == other.source_pack_id
        )


_CACHE: dict[tuple[str, int, str], FrameRegistry] = {}

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


def _empty_registry(pack_id: str, manifest_sha256: str) -> FrameRegistry:
    return FrameRegistry(
        by_surface=types.MappingProxyType({}),
        by_category=types.MappingProxyType({}),
        pack_manifest_sha256=manifest_sha256,
        source_pack_id=pack_id,
    )


def load_frame_registry(pack_path: Path | None = None) -> FrameRegistry:
    """Load and cache the math pack's frame registry.

    When ``{pack}/frames.jsonl`` is absent or empty, returns an empty
    registry (no-op semantics). When the manifest declares a
    ``frame_checksum`` it MUST match the on-disk compiled bytes; a
    mismatch raises :class:`FrameRegistryLoadError`.

    Caches per (resolved_path, mtime_ns, sha256) — invalidated on any
    byte-level edit to the compiled artifact.
    """
    resolved = (
        (pack_path if isinstance(pack_path, Path) else Path(pack_path)).resolve()
        if pack_path is not None
        else (_repo_root() / _DEFAULT_PACK_RELPATH).resolve()
    )

    manifest_path = resolved / "manifest.json"
    compiled_path = resolved / "frames.jsonl"
    if not manifest_path.exists():
        raise FrameRegistryLoadError(f"Pack manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pack_id: str = manifest.get("pack_id", resolved.name)
    declared_sha256 = manifest.get("frame_checksum")

    if not compiled_path.exists():
        # Backward-compat: no compiled frames + no declared checksum is a
        # legitimate empty registry. A declared checksum with no compiled
        # file is a discipline violation.
        if declared_sha256:
            raise FrameRegistryLoadError(
                f"Manifest declares frame_checksum={declared_sha256!r} but "
                f"frames.jsonl is missing at {compiled_path}"
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
        raise FrameRegistryLoadError(
            f"Frame checksum mismatch for {resolved!r}: "
            f"declared={declared_sha256!r}, actual={actual_sha256!r}"
        )

    entries: list[FrameRegistryEntry] = []
    if compiled_bytes:
        for line in compiled_bytes.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            polarity = rec.get("polarity")
            if polarity not in _VALID_POLARITIES:
                raise FrameRegistryLoadError(
                    f"Frame entry has invalid polarity {polarity!r}; "
                    f"must be one of {sorted(_VALID_POLARITIES)!r}"
                )
            entries.append(
                FrameRegistryEntry(
                    surface_form=str(rec["surface_form"]),
                    frame_category=str(rec["frame_category"]),
                    polarity=polarity,
                    provenance=str(rec.get("provenance", "")),
                )
            )

    by_surface_mut: dict[str, FrameRegistryEntry] = {}
    by_cat_mut: dict[str, list[FrameRegistryEntry]] = {}
    for entry in entries:
        key = entry.surface_form.lower()
        # Conflict policy: the FIRST entry per (surface, category, polarity)
        # wins; later identical entries are deduped. Conflicting polarities
        # for the same surface form raise — the operator must resolve.
        existing = by_surface_mut.get(key)
        if existing is not None and (
            existing.frame_category != entry.frame_category
            or existing.polarity != entry.polarity
        ):
            raise FrameRegistryLoadError(
                f"Frame surface {key!r} carries conflicting entries: "
                f"({existing.frame_category!r}, {existing.polarity!r}) vs "
                f"({entry.frame_category!r}, {entry.polarity!r})"
            )
        by_surface_mut[key] = entry
        by_cat_mut.setdefault(entry.frame_category, []).append(entry)

    by_category_frozen: dict[str, tuple[FrameRegistryEntry, ...]] = {
        cat: tuple(sorted(lst, key=lambda e: e.surface_form))
        for cat, lst in by_cat_mut.items()
    }

    registry = FrameRegistry(
        by_surface=types.MappingProxyType(by_surface_mut),
        by_category=types.MappingProxyType(by_category_frozen),
        pack_manifest_sha256=actual_sha256,
        source_pack_id=pack_id,
    )
    _CACHE[cache_key] = registry
    return registry


def lookup(registry: FrameRegistry, surface: str) -> FrameRegistryEntry | None:
    """Case-fold surface and return its entry, or None if unknown."""
    return registry.by_surface.get(surface.lower())


def clear_cache() -> None:
    """Test hook — drop the per-process cache."""
    _CACHE.clear()


__all__ = [
    "FrameRegistry",
    "FrameRegistryEntry",
    "FrameRegistryLoadError",
    "Polarity",
    "load_frame_registry",
    "lookup",
    "clear_cache",
]
