"""chat/partial_surface.py — Phase 2.2: partial-grounding tier.

When a prompt contains both an OOV token AND a pack-resident token,
the runtime today has two choices:

  1. ``pack_grounded_*`` composers — require *both* tokens to resolve
     (ADR-0050 COMPARISON: identical-lemma → None; OOV-lemma → None).
  2. The OOV invitation (P2.1) — names one unknown token but ignores
     the known one entirely.

Both miss a real signal: the known token is actually grounded, the
relation is partially representable, and the operator deserves to
see *which* side is OOV instead of a flat "I don't know one of these".

This module composes a **partial-grounding** surface that:

  - Grounds the pack-resident token verbatim from its lexicon
    (same atoms a full pack-grounded surface would emit).
  - Names the OOV token explicitly under a "whatever ... is" hedge —
    no synthesis, no inferred meaning, no domain guess.
  - States the contract: the relation cannot be grounded until the
    OOV token is ratified into a pack.
  - Tags ``grounding_source="partial"`` so audit and downstream
    aggregation distinguish this from full pack-grounded
    surfaces or the universal disclosure.

Today's scope is the COMPARISON intent (two subject lemmas, one OOV +
one known).  CAUSE/VERIFICATION extract a single subject; if it's
OOV the OOV invitation surface (P2.1) is the right surface — there
is no second lemma to partially ground against.  Future ADRs can
extend partial-grounding to other intent shapes as the classifier
grows multi-lemma extraction.

Trust boundary:
- The partial surface composes only the known-side lexicon atoms,
  the (safely-displayed) OOV token, and a fixed template.
- No vocabulary is invented; no meaning is inferred for the OOV
  side.
- The trailing instruction points at the reviewed pack-mutation
  path — partial grounding never auto-mutates state.
"""

from __future__ import annotations

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from core._safe_display import safe_display


def partial_comparison_surface(
    lemma_a: str,
    lemma_b: str,
    *,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> tuple[str, str] | None:
    """Return ``(surface, known_side)`` where ``known_side`` is ``"a"``
    or ``"b"`` depending on which lemma resolved, or ``None``.

    The surface format is fixed:

        "Whatever '{oov}' is, I can ground '{known}'
         — pack-grounded ({pack_id}): {d1}; {d2}.
         I cannot ground the comparison without learning '{oov}' —
         teach me via a reviewed PackMutationProposal."

    The composer returns ``None`` when:

      - either lemma is empty / not a string,
      - both lemmas resolve (route through the full
        ``pack_grounded_comparison_surface`` instead),
      - neither lemma resolves (route through the OOV invitation;
        partial-grounding has nothing to anchor on),
      - the two lemmas are identical strings (same-lemma comparison
        carries no contrastive evidence at any tier).
    """
    if not lemma_a or not isinstance(lemma_a, str):
        return None
    if not lemma_b or not isinstance(lemma_b, str):
        return None
    key_a = lemma_a.strip().lower()
    key_b = lemma_b.strip().lower()
    if not key_a or not key_b or key_a == key_b:
        return None

    resolved_a = resolve_lemma(key_a, pack_ids)
    resolved_b = resolve_lemma(key_b, pack_ids)
    # Partial-grounding requires exactly one side to resolve.
    if resolved_a is None and resolved_b is None:
        return None
    if resolved_a is not None and resolved_b is not None:
        return None

    if resolved_a is not None:
        known_lemma = key_a
        known_pack_id, known_domains = resolved_a
        oov_lemma = key_b
        known_side = "a"
    else:
        assert resolved_b is not None
        known_lemma = key_b
        known_pack_id, known_domains = resolved_b
        oov_lemma = key_a
        known_side = "b"

    safe_oov = safe_display(oov_lemma)
    head = "; ".join(known_domains[:2])
    surface = (
        f"Whatever '{safe_oov}' is, I can ground '{known_lemma}' "
        f"— pack-grounded ({known_pack_id}): {head}. "
        f"I cannot ground the comparison without learning '{safe_oov}' "
        f"— teach me via a reviewed PackMutationProposal."
    )
    return (surface, known_side)


__all__ = ["partial_comparison_surface"]
