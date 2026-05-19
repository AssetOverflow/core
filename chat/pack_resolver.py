"""chat/pack_resolver.py — ADR-0063 cross-pack surface resolver.

The cold-start grounding composers in :mod:`chat.pack_grounding` were
hardcoded to a single lexicon pack (``en_core_cognition_v1``).  That
asymmetry blocked ``en_core_relations_v1`` from being mounted on the
default runtime: mounting it would silently widen vault recall and
intent classification without a corresponding ratified surface
composer for kinship lemmas.

This module supplies the missing abstraction: a *deterministic*,
*first-match-wins* resolver that maps a lemma to ``(pack_id, semantic_domains)``
across an ordered tuple of mounted lexicon packs.  Surface composers
consult the resolver instead of a single pack; the surface trust-boundary
tag follows the *resolving* pack id.

Design constraints (CLAUDE.md / Reconstruction-over-storage):

- The resolver loads each pack lexicon at most once per process via
  :func:`functools.lru_cache`.  Ratified packs are immutable, so caching
  is sound.
- A pack that fails to load (missing file, unreadable JSON) contributes
  an empty index — callers cannot distinguish "pack absent" from "lemma
  absent in mounted packs".  Both produce ``None``.
- First-match-wins on collision.  The orthogonality test in
  ``tests/test_en_core_relations_v1_pack.py`` enforces zero overlap
  today; this rule documents the deterministic resolution if a future
  pack pair collides.
- No mutation of pack data is performed anywhere in this module.  All
  return types are tuples/frozensets/dicts of plain strings.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# Default mounted lexicon-pack ids that ADR-0063 surface composers
# consult.  Order matters: earlier packs win on lemma collision.  This
# tuple is intentionally narrow — it lists only ratified ``en_core_*``
# *content* packs.  Identity/safety/ethics packs are propositional
# overlays and never carry vocabulary; they are deliberately excluded.
DEFAULT_RESOLVABLE_PACK_IDS: tuple[str, ...] = (
    "en_core_cognition_v1",
    "en_core_meta_v1",
    "en_core_attitude_v1",
    "en_core_temporal_v1",
    "en_core_action_v1",
    "en_core_relations_v1",
    "en_core_relations_v2",
)

_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data"


@lru_cache(maxsize=16)
def _pack_lexicon_for(pack_id: str) -> dict[str, tuple[str, ...]]:
    """Return ``{lemma_lower: semantic_domains}`` for *pack_id*, cached.

    Returns an empty dict if the pack's lexicon file is missing,
    unreadable, or contains no entries with ``semantic_domains``.
    Ratified packs are immutable so the cache survives the process
    lifetime.
    """
    lexicon_path = _PACK_ROOT / pack_id / "lexicon.jsonl"
    if not lexicon_path.exists():
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for line in lexicon_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        lemma = entry.get("lemma") or entry.get("surface")
        if not lemma or not isinstance(lemma, str):
            continue
        domains = entry.get("semantic_domains", ())
        if not isinstance(domains, (list, tuple)) or not domains:
            continue
        out[lemma.lower()] = tuple(str(d) for d in domains)
    return out


def resolve_lemma(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> tuple[str, tuple[str, ...]] | None:
    """Return ``(pack_id, semantic_domains)`` for the first pack in
    *pack_ids* whose lexicon contains *lemma*, else ``None``.

    First-match-wins on collision.  ``pack_ids`` defaults to
    :data:`DEFAULT_RESOLVABLE_PACK_IDS`.
    """
    if not lemma or not isinstance(lemma, str):
        return None
    key = lemma.strip().lower()
    if not key:
        return None
    for pack_id in pack_ids:
        index = _pack_lexicon_for(pack_id)
        domains = index.get(key)
        if domains:
            return (pack_id, domains)
    return None


def is_resolvable(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> bool:
    """Return True iff *lemma* resolves in any of *pack_ids*."""
    return resolve_lemma(lemma, pack_ids) is not None


def mounted_lemmas(
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> frozenset[str]:
    """Return the frozen union of lemmas across *pack_ids*.

    Used by topic extractors that iterate over user-text tokens and
    need an O(1) "is this token any mounted lemma?" check.
    """
    out: set[str] = set()
    for pack_id in pack_ids:
        out.update(_pack_lexicon_for(pack_id).keys())
    return frozenset(out)


def clear_resolver_cache() -> None:
    """Drop the lru_cache for :func:`_pack_lexicon_for`.

    Test-only escape hatch: enables fixture-based pack mutation
    scenarios.  Production code never calls this — ratified packs are
    immutable.
    """
    _pack_lexicon_for.cache_clear()
