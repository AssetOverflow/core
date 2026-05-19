"""chat/anaphora.py — Phase 3.2: deterministic thread anaphora prefix.

When the current turn's subject lemma appeared in a recent *grounded*
turn (pack or teaching tier), the anaphora composer prepends a
deterministic backreference to the current surface.  Conversation
reads as a thread instead of a sequence of independent surfaces:

    Turn 0  > Why does light exist?
              [teaching] light — teaching-grounded (cognition_chains_v1):
              cognition.illumination; logos.core. light reveals truth ...
    Turn 1  > What is light?
              [pack] (Recalling turn 0: chain cause_light_reveals_truth.)
              light — pack-grounded (en_core_cognition_v1): cognition.illumination;
              logos.core; perception.clarity. No session evidence yet.

The prefix is **strictly deterministic**:

  - Same thread state + same current turn → byte-identical prefix.
  - No prose generation; the prefix references the prior turn by
    *turn index* and *chain id* (or grounding tier), nothing else.
  - The composer only fires when *both* the prior turn AND the
    current turn are pack/teaching tier; weaker tiers (vault /
    partial / oov / none) do not anchor.
  - Same-intent revisits (asking the same question twice) do not
    fire — the prior turn IS the current turn modulo session vault
    drift, prefixing it is redundant.
  - Opt-in via :attr:`core.config.RuntimeConfig.thread_anaphora`.
    Default ``False`` preserves every pre-P3.2 surface byte-identically.
"""

from __future__ import annotations

from chat.thread_context import ThreadContext


# Grounding tiers strong enough to anchor an anaphora reference.
_ANCHOR_TIERS: frozenset[str] = frozenset({"teaching", "pack"})


def thread_anaphora_prefix(
    thread_context: ThreadContext,
    current_subject: str,
    current_intent_tag_name: str,
    current_grounding_source: str,
) -> str | None:
    """Return a deterministic anaphora prefix, or ``None``.

    Engagement conditions (ALL must hold):

      1. ``current_subject`` is non-empty.
      2. ``current_grounding_source`` is in ``{"pack", "teaching"}``
         — weaker tiers cannot host a meaningful backreference.
      3. A prior turn on the same subject exists in
         ``thread_context`` AND was itself pack/teaching grounded.
      4. The prior turn's intent differs from the current turn's
         intent (a same-intent revisit is the same surface modulo
         vault drift; prefixing would be redundant).

    The prefix format references the prior turn by structured fields
    only — never by surface text, never by re-derived prose.  Two
    shapes exist:

      - Prior was teaching-grounded → ``"(Recalling turn N: chain
        <chain_id>.) "``
      - Prior was pack-grounded → ``"(Recalling turn N: <subject>
        grounded pack.) "``

    Returns ``None`` when any engagement condition fails.  Callers
    then emit the unprefixed surface byte-identically.
    """
    if not current_subject or not isinstance(current_subject, str):
        return None
    key = current_subject.strip().lower()
    if not key:
        return None
    if current_grounding_source not in _ANCHOR_TIERS:
        return None
    prior = thread_context.recent_for_subject(key)
    if prior is None:
        return None
    if prior.grounding_source not in _ANCHOR_TIERS:
        return None
    if prior.intent_tag_name and prior.intent_tag_name == current_intent_tag_name:
        return None

    if prior.grounding_source == "teaching" and prior.chain_id:
        return f"(Recalling turn {prior.turn_index}: chain {prior.chain_id}.) "
    return (
        f"(Recalling turn {prior.turn_index}: {key} grounded "
        f"{prior.grounding_source}.) "
    )


__all__ = ["thread_anaphora_prefix"]
