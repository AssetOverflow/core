"""ADR-0164 §Decision §1 — operational lexicon loader for en_core_math_v1.

Provides word → category lookups for the reader's apply_word step 2.
I/O happens only at load time; all lookups are O(1) dict hits.
"""

from __future__ import annotations

import hashlib
import json
import os
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# ---------------------------------------------------------------------------
# Typed error
# ---------------------------------------------------------------------------


class LexiconLoadError(ValueError):
    """Raised on any load-time failure (checksum mismatch, conflict, etc.)."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LexiconEntry:
    lemma: str
    category: str
    aliases: tuple[str, ...]
    provenance: str


@dataclass(frozen=True, slots=True)
class Lexicon:
    by_surface: Mapping[str, LexiconEntry]
    by_category: Mapping[str, tuple[LexiconEntry, ...]]
    pack_manifest_sha256: str
    source_pack_id: str

    def __hash__(self) -> int:
        # Content-derived hash: same pack bytes → same sha256 → same hash.
        return hash((self.pack_manifest_sha256, self.source_pack_id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Lexicon):
            return NotImplemented
        return (
            dict(self.by_surface) == dict(other.by_surface)
            and self.pack_manifest_sha256 == other.pack_manifest_sha256
            and self.source_pack_id == other.source_pack_id
        )


# ---------------------------------------------------------------------------
# Module-level cache — keyed on (resolved_path_str, mtime_ns, sha256)
# ---------------------------------------------------------------------------

_CACHE: dict[tuple[str, int, str], Lexicon] = {}

_DEFAULT_PACK_RELPATH = Path("language_packs") / "data" / "en_core_math_v1"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    # Walk up until we find a directory that has pyproject.toml or setup.cfg.
    candidate = here
    for _ in range(10):
        candidate = candidate.parent
        if (candidate / "pyproject.toml").exists() or (candidate / "setup.cfg").exists():
            return candidate
    # Fallback: three levels up from this file
    return here.parent.parent.parent


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_lexicon(pack_path: Path | None = None) -> Lexicon:
    """Load and cache the operational lexicon.

    Reads per-category source files from ``pack_path/lexicon/*.jsonl`` for
    full entry schema (including aliases). Verifies the manifest checksum
    against the compiled ``lexicon.jsonl`` for pack integrity.
    """
    resolved = (
        (pack_path if isinstance(pack_path, Path) else Path(pack_path)).resolve()
        if pack_path is not None
        else (_repo_root() / _DEFAULT_PACK_RELPATH).resolve()
    )

    compiled_path = resolved / "lexicon.jsonl"
    manifest_path = resolved / "manifest.json"

    # Stable cache key based on compiled file mtime + sha256.
    mtime_ns = os.stat(compiled_path).st_mtime_ns
    actual_sha256 = _sha256_file(compiled_path)
    cache_key = (str(resolved), mtime_ns, actual_sha256)

    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Verify manifest checksum against the compiled lexicon bytes.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared_sha256: str = manifest.get("checksum", "")
    if declared_sha256 != actual_sha256:
        raise LexiconLoadError(
            f"Manifest checksum mismatch for {resolved!r}: "
            f"declared={declared_sha256!r}, actual={actual_sha256!r}"
        )

    pack_id: str = manifest.get("pack_id", resolved.name)

    # Load from source per-category files (they carry aliases).
    source_dir = resolved / "lexicon"
    if not source_dir.is_dir():
        raise LexiconLoadError(
            f"Source lexicon directory not found: {source_dir}"
        )

    entries: list[LexiconEntry] = []
    for src_file in sorted(source_dir.glob("*.jsonl")):
        for line in src_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            entry = LexiconEntry(
                lemma=rec["lemma"],
                category=rec["category"],
                aliases=tuple(rec.get("aliases", [])),
                provenance=rec.get("provenance", ""),
            )
            entries.append(entry)

    # Build by_surface (case-folded). Check for mutual-exclusion violations.
    by_surface_mut: dict[str, LexiconEntry] = {}
    conflicts: list[str] = []

    for entry in entries:
        surfaces = [entry.lemma.lower()] + [a.lower() for a in entry.aliases]
        for surf in surfaces:
            if surf in by_surface_mut:
                existing = by_surface_mut[surf]
                if existing.category != entry.category:
                    conflicts.append(
                        f"Surface {surf!r} is in both "
                        f"{existing.category!r} (lemma={existing.lemma!r}) "
                        f"and {entry.category!r} (lemma={entry.lemma!r})"
                    )
            else:
                by_surface_mut[surf] = entry

    if conflicts:
        raise LexiconLoadError(
            "Mutual-exclusion violation in pack "
            f"{pack_id!r}: {'; '.join(conflicts)}"
        )

    # Build by_category sorted by lemma within each group.
    by_cat_mut: dict[str, list[LexiconEntry]] = {}
    for entry in entries:
        by_cat_mut.setdefault(entry.category, []).append(entry)
    by_category_frozen: dict[str, tuple[LexiconEntry, ...]] = {
        cat: tuple(sorted(lst, key=lambda e: e.lemma))
        for cat, lst in by_cat_mut.items()
    }

    lexicon = Lexicon(
        by_surface=types.MappingProxyType(by_surface_mut),
        by_category=types.MappingProxyType(by_category_frozen),
        pack_manifest_sha256=actual_sha256,
        source_pack_id=pack_id,
    )
    _CACHE[cache_key] = lexicon
    return lexicon


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def lookup(lexicon: Lexicon, surface: str) -> LexiconEntry | None:
    """Case-fold surface and return its entry, or None if unknown."""
    return lexicon.by_surface.get(surface.lower())
