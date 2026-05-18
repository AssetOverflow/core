"""ADR-0052 — teaching-grounded CAUSE / VERIFICATION surface tests.

Contract pinned here:

  - ``teaching_grounded_surface(lemma, intent_tag)`` returns a
    deterministic surface composed of the subject lemma + its pack
    ``semantic_domains``, a fixed connective predicate, the object
    lemma, and its pack ``semantic_domains``.  No synthesis.
  - Returns ``None`` when:
      * the lemma is empty or absent from the corpus,
      * the intent is not ``CAUSE`` or ``VERIFICATION``,
      * the chain references lemmas missing from the ratified pack.
  - The runtime wiring engages only when:
      * the gate fires with ``source="empty_vault"``,
      * ``output_language == "en"``,
      * intent is ``CAUSE`` or ``VERIFICATION``,
      * the subject lemma has a reviewed chain.
  - ``ChatResponse.grounding_source`` and ``TurnEvent.grounding_source``
    both carry ``"teaching"`` on this branch.
  - Refusal still takes priority — teaching-grounded surfaces never
    bypass safety / ethics verdict refusal.
"""

from __future__ import annotations

import pytest

from chat.pack_grounding import PACK_ID, _pack_index
from chat.runtime import ChatRuntime, _UNKNOWN_DOMAIN_SURFACE
from chat.teaching_grounding import (
    TEACHING_CORPUS_ID,
    has_teaching_chain,
    teaching_grounded_surface,
)
from generate.intent import IntentTag


# ---------------------------------------------------------------------------
# teaching_grounded_surface — pure-function contracts
# ---------------------------------------------------------------------------


def test_cause_light_chain_produces_surface() -> None:
    surface = teaching_grounded_surface("light", IntentTag.CAUSE)
    assert surface is not None
    assert "light" in surface
    assert "truth" in surface
    assert "reveals" in surface
    assert TEACHING_CORPUS_ID in surface
    assert "teaching-grounded" in surface
    assert "No session evidence yet." in surface


def test_cause_knowledge_chain_produces_surface() -> None:
    surface = teaching_grounded_surface("knowledge", IntentTag.CAUSE)
    assert surface is not None
    assert "knowledge" in surface
    assert "evidence" in surface
    assert "requires" in surface


def test_verification_memory_chain_produces_surface() -> None:
    surface = teaching_grounded_surface("memory", IntentTag.VERIFICATION)
    assert surface is not None
    assert "memory" in surface
    assert "recall" in surface
    assert "requires" in surface


def test_lemma_absent_from_corpus_returns_none() -> None:
    assert teaching_grounded_surface("dragon", IntentTag.CAUSE) is None


def test_subject_in_corpus_wrong_intent_returns_none() -> None:
    """``memory`` has a VERIFICATION chain but not a CAUSE chain."""
    assert teaching_grounded_surface("memory", IntentTag.CAUSE) is None


def test_definition_intent_returns_none() -> None:
    """Teaching grounding is scoped to CAUSE / VERIFICATION only."""
    assert teaching_grounded_surface("light", IntentTag.DEFINITION) is None
    assert teaching_grounded_surface("light", IntentTag.RECALL) is None
    assert teaching_grounded_surface("light", IntentTag.COMPARISON) is None
    assert teaching_grounded_surface("light", IntentTag.UNKNOWN) is None


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_or_invalid_lemma_returns_none(bad) -> None:
    assert teaching_grounded_surface(bad, IntentTag.CAUSE) is None  # type: ignore[arg-type]


def test_surface_is_deterministic() -> None:
    """Same input must produce byte-identical surface on repeat."""
    a = teaching_grounded_surface("memory", IntentTag.VERIFICATION)
    b = teaching_grounded_surface("memory", IntentTag.VERIFICATION)
    assert a == b
    assert a is not None


def test_case_insensitive_lookup() -> None:
    a = teaching_grounded_surface("LIGHT", IntentTag.CAUSE)
    b = teaching_grounded_surface("light", IntentTag.CAUSE)
    assert a == b
    assert a is not None


def test_has_teaching_chain_helper() -> None:
    assert has_teaching_chain("light", IntentTag.CAUSE) is True
    assert has_teaching_chain("knowledge", IntentTag.CAUSE) is True
    assert has_teaching_chain("memory", IntentTag.VERIFICATION) is True
    assert has_teaching_chain("memory", IntentTag.CAUSE) is False
    assert has_teaching_chain("dragon", IntentTag.CAUSE) is False
    assert has_teaching_chain("light", IntentTag.DEFINITION) is False
    assert has_teaching_chain("", IntentTag.CAUSE) is False


# ---------------------------------------------------------------------------
# Doctrine — every atom verbatim from pack or fixed template
# ---------------------------------------------------------------------------


def test_surface_atoms_are_verbatim_from_pack() -> None:
    """Every visible non-template descriptor must be a verbatim
    ``semantic_domains`` string from the ratified pack — no rewording."""
    surface = teaching_grounded_surface("knowledge", IntentTag.CAUSE)
    assert surface is not None
    index = _pack_index()
    # Subject domains (first 2 by corpus config)
    for domain in index["knowledge"][:2]:
        assert domain in surface
    # Object domain (first 1)
    for domain in index["evidence"][:1]:
        assert domain in surface
    # Fixed-template tokens
    assert "teaching-grounded" in surface
    assert "No session evidence yet." in surface


def test_surface_does_not_invent_packless_descriptors() -> None:
    """Sanity: no fabricated cognition.* domain that isn't in the pack."""
    surface = teaching_grounded_surface("memory", IntentTag.VERIFICATION)
    assert surface is not None
    index = _pack_index()
    all_pack_domains: set[str] = set()
    for domains in index.values():
        all_pack_domains.update(domains)
    # Every "<word>.<word>" looking descriptor in the surface must be a
    # real pack domain.  Crude but effective at catching fabrication.
    import re
    for match in re.findall(r"\b[a-z]+\.[a-z]+\b", surface):
        assert match in all_pack_domains, f"non-pack descriptor: {match}"


# ---------------------------------------------------------------------------
# ChatRuntime integration — cold-start CAUSE / VERIFICATION path
# ---------------------------------------------------------------------------


def test_cold_start_cause_light_returns_teaching_surface() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Why does light exist?")
    assert resp.grounding_source == "teaching"
    assert "light" in resp.surface
    assert "truth" in resp.surface
    assert "teaching-grounded" in resp.surface


def test_cold_start_cause_knowledge_returns_teaching_surface() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Why does knowledge require evidence?")
    assert resp.grounding_source == "teaching"
    assert "knowledge" in resp.surface
    assert "evidence" in resp.surface


def test_cold_start_verification_memory_returns_teaching_surface() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Does memory require recall?")
    assert resp.grounding_source == "teaching"
    assert "memory" in resp.surface
    assert "recall" in resp.surface


def test_cold_start_cause_unknown_subject_routes_to_oov_invitation() -> None:
    """ADR-0065 / P2.1 — CAUSE on an OOV subject routes through the
    OOV invitation surface (subject is OOV → no chain → fall-through
    to OOV).  Pre-P2.1 this returned the universal disclosure."""
    rt = ChatRuntime()
    resp = rt.chat("Why does dragon exist?")
    assert resp.grounding_source == "oov"
    assert "dragon" in resp.surface


def test_turn_event_carries_grounding_source_teaching() -> None:
    rt = ChatRuntime()
    rt.chat("Why does light exist?")
    last_event = rt.turn_log[-1]
    assert getattr(last_event, "grounding_source", None) == "teaching"


def test_teaching_grounded_passes_verdict_audit() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Why does light exist?")
    assert resp.safety_verdict is not None
    assert resp.ethics_verdict is not None


def test_definition_path_still_returns_pack_source() -> None:
    """Regression: DEFINITION still routes to pack, not teaching."""
    rt = ChatRuntime()
    resp = rt.chat("What is light?")
    assert resp.grounding_source == "pack"
    assert PACK_ID in resp.surface


def test_comparison_path_still_returns_pack_source() -> None:
    """Regression: COMPARISON still routes to pack, not teaching."""
    rt = ChatRuntime()
    resp = rt.chat("Compare memory and recall")
    assert resp.grounding_source == "pack"
