"""Typed surface candidate intermediate — selector-ready shape.

This module defines the dataclass that ``pack_grounded_surface`` and
related composers build BEFORE rendering to a final string.  It is the
"deliberately narrow" integration the 2026-05-19 design review asked
for: gloss-backed surface delivery today, drop-in compatible with the
future ``SurfaceSelector`` registry.

When the selector lands:

  - This candidate type becomes one variant in the selector's typed
    candidate union (alongside RefusalCandidate, TeachingCandidate,
    OOVCandidate, etc.).
  - ``pack_grounded_surface()`` becomes a *provider* that emits this
    candidate; the selector picks among providers' candidates by
    ranked grounding authority.
  - No data migration: the field layout below already matches the
    review's specification (surface + grounding_source + intent slots
    + provenance + is_user_facing_safe + is_fluent_sentence).

Until the selector lands, ``pack_grounded_surface()`` builds and then
renders the candidate inline.  The rendering step is the only thing
that needs relocation, not the candidate shape.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PackSurfaceCandidate:
    """A pack-grounded surface candidate carrying its provenance.

    Fields match the typed-candidate lattice the 2026-05-19 review
    described so the future ``SurfaceSelector`` consumes this directly.
    """

    # The final user-facing string (rendered).  This IS what would
    # appear in ChatResponse.surface when this candidate wins.
    surface: str

    # The ranked grounding-source tag — same enum the runtime emits.
    # Today: "pack" for both gloss-backed and dotted-disclosure paths
    # (the selector may later split "pack_gloss" / "pack_domains" if
    # the ranked authority lattice wants finer-grained ordering).
    grounding_source: str

    # The pack that ratified the lemma — provenance, not text.
    pack_id: str

    # The reviewed natural-language gloss when present; None when the
    # pack ships no gloss for this lemma and the candidate falls back
    # to dotted-domain disclosure.
    gloss: str | None

    # The semantic_domains list verbatim from the pack's lexicon.
    # Always present — this is the audit-trail content that survives
    # gloss revision.
    semantic_domains: tuple[str, ...]

    # The looked-up lemma (lowercase, stripped).
    lemma: str

    # POS tag from the lexicon (NOUN/VERB/ADJ/ADV/...).  Drives the
    # sentence frame in renderer code.
    pos: str

    # Honesty flags the selector consults.

    # True when the candidate emits a single sentence with terminal
    # punctuation and no placeholder markers.  Today this is True for
    # gloss-backed and dotted-domain surfaces alike.
    is_user_facing_safe: bool = True

    # True when the candidate carries a reviewed gloss (vs. dotted
    # domain disclosure).  The selector may prefer fluent candidates
    # over disclosure-style ones at the same grounding_source rank.
    is_fluent_sentence: bool = False


__all__ = ["PackSurfaceCandidate"]
