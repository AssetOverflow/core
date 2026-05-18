"""chat/pack_grounding.py — pack-grounded surface for cold-start DEFINITION
and RECALL intents (ADR-0048).

When the ``UnknownDomainGate`` fires with ``source="empty_vault"`` — i.e.
the runtime has no session evidence yet — the runtime would otherwise
emit the universal ``_UNKNOWN_DOMAIN_SURFACE`` disclosure on every turn,
including for terms that are explicitly compiled into the ratified
cognition pack.

This module supplies a narrow, auditable alternative: when the input's
intent is ``DEFINITION`` or ``RECALL`` AND the intent's subject lemma is
present in ``en_core_cognition_v1``, return a deterministic surface
composed from the pack lexicon's ``semantic_domains`` for that lemma,
explicitly tagged as pack-sourced.

Design constraints (matching the seven axioms):

- Geometry-first: the pack lookup is by lemma surface, but the
  ``semantic_domains`` were curated against the same versors the
  vocabulary carries; the surface refers only to the lemma and its
  curated descriptors — no synthesis, no LLM fallback.
- Reconstruction-over-storage: the surface is reconstructed from the
  pack at call time; the lexicon is loaded once and cached because
  ratified packs are immutable.
- Dual-correction: any lemma not in the pack returns ``None``;
  callers fall through to ``_UNKNOWN_DOMAIN_SURFACE`` unchanged.
- Compilation-last: no tensors, no kernels — JSONL read and string
  formatting only.
- Trust boundary: every surface produced here is explicitly tagged
  ``pack:en_core_cognition_v1`` so the audit contract distinguishes
  pack-grounded surfaces from vault-grounded surfaces and from the
  universal disclosure.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PACK_ID: str = "en_core_cognition_v1"

_PACK_LEXICON_PATH = (
    Path(__file__).resolve().parent.parent
    / "language_packs"
    / "data"
    / PACK_ID
    / "lexicon.jsonl"
)


@lru_cache(maxsize=1)
def _pack_index() -> dict[str, tuple[str, ...]]:
    """Load the cognition pack lexicon once and return ``{lemma: semantic_domains}``.

    Ratified packs are immutable; safe to cache for the process lifetime.
    Returns an empty dict if the pack is unavailable — callers must treat
    a missing pack as "no pack-grounded surface available."
    """
    if not _PACK_LEXICON_PATH.exists():
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for line in _PACK_LEXICON_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        lemma = entry.get("lemma") or entry.get("surface")
        if not lemma:
            continue
        domains = tuple(entry.get("semantic_domains", ()))
        if domains:
            out[lemma.lower()] = domains
    return out


def pack_grounded_surface(lemma: str) -> str | None:
    """Return a deterministic pack-grounded surface for *lemma*, or ``None``.

    The surface format is fixed:

        "{lemma} — pack-grounded ({pack_id}): {d1}; {d2}; {d3}. No session evidence yet."

    Only the lemma and up to three semantic_domains from the pack are
    emitted; both come directly from the ratified pack lexicon, with no
    rewording.  The trailing disclosure is the constant trust-boundary
    label that distinguishes pack-grounded surfaces from vault-grounded
    surfaces (which would carry session evidence) and from the universal
    "insufficient grounding" disclosure (which carries neither).

    Returns ``None`` when:
      - the lemma is empty or not a string,
      - the pack lexicon file is unavailable,
      - the lemma is not present in the pack,
      - the pack entry has no ``semantic_domains``.
    """
    if not lemma or not isinstance(lemma, str):
        return None
    key = lemma.strip().lower()
    if not key:
        return None
    index = _pack_index()
    domains = index.get(key)
    if not domains:
        return None
    head = "; ".join(domains[:3])
    return (
        f"{key} — pack-grounded ({PACK_ID}): {head}. "
        f"No session evidence yet."
    )


def is_pack_lemma(lemma: str) -> bool:
    """Return True iff *lemma* has an entry with ``semantic_domains`` in the pack."""
    if not lemma or not isinstance(lemma, str):
        return False
    return lemma.strip().lower() in _pack_index()


def pack_grounded_comparison_surface(
    lemma_a: str, lemma_b: str
) -> str | None:
    """ADR-0050 — deterministic pack-grounded surface for COMPARISON intent.

    Returns a surface that composes each lemma's pack semantic_domains
    side-by-side, with no rewording or inference:

        "{a} (d_a1; d_a2) contrasts with {b} (d_b1; d_b2) — pack-grounded
         ({pack_id}). No session evidence yet."

    Up to two semantic_domains per side are emitted to keep the surface
    compact.  All visible tokens are either the lemmas themselves or
    verbatim pack strings; the verb "contrasts with" is the fixed
    COMPARISON template constant (mirroring the relation predicate
    `contrasts_with` already humanised by ``humanize_predicate``).

    Returns ``None`` when:
      - either lemma is empty or not a string,
      - either lemma is not present in the pack,
      - the two lemmas are identical (a comparison between a term
        and itself carries no contrastive evidence — defer to the
        single-lemma ``pack_grounded_surface`` path or to the
        universal disclosure).
    """
    if not lemma_a or not isinstance(lemma_a, str):
        return None
    if not lemma_b or not isinstance(lemma_b, str):
        return None
    key_a = lemma_a.strip().lower()
    key_b = lemma_b.strip().lower()
    if not key_a or not key_b:
        return None
    if key_a == key_b:
        return None
    index = _pack_index()
    domains_a = index.get(key_a)
    domains_b = index.get(key_b)
    if not domains_a or not domains_b:
        return None
    head_a = "; ".join(domains_a[:2])
    head_b = "; ".join(domains_b[:2])
    return (
        f"{key_a} ({head_a}) contrasts with {key_b} ({head_b}) "
        f"— pack-grounded ({PACK_ID}). No session evidence yet."
    )
