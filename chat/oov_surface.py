"""chat/oov_surface.py — Phase 2.1: OOV "teach me" surface.

When the intent classifier extracts a clean subject lemma but that
lemma is not resident in any mounted lexicon pack, the runtime today
falls through to the universal disclosure
(``_UNKNOWN_DOMAIN_SURFACE``).  That surface is *honest* (it does
not pretend to know) but it is also *flat* — it conveys no signal
that a specific vocabulary gap was hit, and it offers the operator
no concrete next step.

This module replaces that cliff with a gradient.  Cold-start prompts
whose subject is OOV emit a deterministic learning-invitation
surface that:

  1. Names the unknown token explicitly so the operator sees which
     word the system could not ground.
  2. Lists the currently-mounted lexicon packs so the operator knows
     where the token could be added.
  3. Points at the existing reviewed-pack-mutation path
     (:mod:`teaching.proposals`) as the way to teach the system the
     new lemma — never "auto-learn", never invent meaning.

The surface is tagged ``grounding_source="oov"`` so downstream audit,
discovery aggregation, and operator tooling can distinguish
"I haven't learned this yet" from "I refuse" / "I'm unsure" /
"insufficient evidence".

Design constraints (matching ADR-0048..0064 doctrine):

- **Deterministic.**  Same OOV token + same mounted-pack list →
  byte-identical surface.
- **No synthesis.**  The surface composes only:
    * the OOV token (verbatim user input — safely escaped at the
      :func:`chat._safe_display.safe_display` boundary),
    * the mounted-pack ids (declared statically in
      :data:`chat.pack_resolver.DEFAULT_RESOLVABLE_PACK_IDS`),
    * a fixed-template instruction.
  No new vocabulary is invented; no domain inference is performed.
- **Trust boundary preserved.**  The surface invites a *reviewed*
  pack mutation; it never silently mutates any pack or corpus.  The
  ADR-0027 proposal-only invariant is intact.
"""

from __future__ import annotations

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, is_resolvable
from core._safe_display import safe_display
from generate.intent import IntentTag


# Intent shapes for which the runtime emits a grounded cold-start
# surface today (ADR-0048 / 0050 / 0052 / 0053 / 0061).  OOV
# invitation fires only when the prompt's intent is one of these —
# UNKNOWN-intent prompts get the universal disclosure unchanged
# because the classifier itself could not extract a confident
# subject.
_OOV_INTENT_TAGS: frozenset[IntentTag] = frozenset({
    IntentTag.DEFINITION,
    IntentTag.RECALL,
    IntentTag.CAUSE,
    IntentTag.VERIFICATION,
    IntentTag.COMPARISON,
    IntentTag.PROCEDURE,
    IntentTag.CORRECTION,
    IntentTag.NARRATIVE,  # P3.3
    IntentTag.EXAMPLE,    # P3.4
})


def oov_learning_invitation_surface(
    token: str,
    intent_tag: IntentTag,
    *,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> str | None:
    """Return a deterministic OOV learning-invitation surface, or ``None``.

    The surface format is fixed:

        "I haven't learned '{token}' yet (intent: {intent}).
         Mounted lexicon packs: {pack_list}.
         Teach me via a reviewed PackMutationProposal."

    The trailing instruction is the constant trust-boundary label.
    It points at the existing reviewed-pack-mutation path; the
    surface never invents meaning for the unknown token.

    Returns ``None`` (caller falls through to the universal disclosure)
    when:
      - ``token`` is empty or not a string,
      - ``token`` IS resolvable in *pack_ids* (caller routed here by
        mistake — keep the explicit fall-through rather than emit a
        misleading surface),
      - the mounted-pack list is empty (no learnable destination —
        emitting an invitation with no targets would be unhelpful).
    """
    if not token or not isinstance(token, str):
        return None
    cleaned = token.strip()
    if not cleaned:
        return None
    if intent_tag not in _OOV_INTENT_TAGS:
        return None
    if is_resolvable(cleaned, pack_ids):
        return None
    if not pack_ids:
        return None
    safe_token = safe_display(cleaned)
    pack_list = ", ".join(pack_ids)
    intent_name = intent_tag.name.lower()
    return (
        f"I haven't learned '{safe_token}' yet (intent: {intent_name}). "
        f"Mounted lexicon packs: {pack_list}. "
        f"Teach me via a reviewed PackMutationProposal."
    )


def is_oov_for_packs(
    token: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> bool:
    """Return True iff *token* is non-empty and not resolvable in
    any of *pack_ids*.  Convenience predicate for the runtime
    dispatcher (avoids duplicating the ``is_resolvable`` inversion
    in caller code)."""
    if not token or not isinstance(token, str):
        return False
    cleaned = token.strip()
    if not cleaned:
        return False
    return not is_resolvable(cleaned, pack_ids)


__all__ = [
    "oov_learning_invitation_surface",
    "is_oov_for_packs",
]
