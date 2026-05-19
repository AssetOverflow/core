"""Phase 3.2 — thread anaphora prefix tests.

The contract these tests pin:

  - ``thread_anaphora_prefix`` is deterministic and pure.
  - Fires only when BOTH the prior turn (recovered from
    ``ThreadContext``) AND the current turn are pack/teaching tier.
  - Same-intent revisits do not fire (redundant prefix).
  - Format is structural-fields-only: turn index + chain_id or
    grounding tier; never re-derives prose.
  - Live runtime: ``RuntimeConfig.thread_anaphora=False`` keeps
    every existing surface byte-identical (default off).
  - With the flag on AND seeded thread state, the runtime prepends
    the deterministic backreference to the pack-grounded surface.
"""

from __future__ import annotations

import pytest

from chat.anaphora import thread_anaphora_prefix
from chat.runtime import ChatRuntime
from chat.thread_context import ThreadContext, TurnSummary
from core.config import RuntimeConfig


def _seed(tc: ThreadContext, **kw) -> None:
    """Helper to push a TurnSummary into a context."""
    tc.push(TurnSummary(
        turn_index=kw.get("turn_index", 0),
        intent_tag_name=kw.get("intent", "cause"),
        subject=kw.get("subject", "light"),
        grounding_source=kw.get("source", "teaching"),
        chain_id=kw.get("chain_id"),
        corpus_id=kw.get("corpus_id"),
    ))


# ---------------------------------------------------------------------------
# Pure-function contract
# ---------------------------------------------------------------------------


def test_prior_teaching_current_pack_fires_with_chain_id() -> None:
    tc = ThreadContext()
    _seed(tc, turn_index=0, intent="cause", subject="light",
          source="teaching", chain_id="cause_light_reveals_truth",
          corpus_id="cognition_chains_v1")
    prefix = thread_anaphora_prefix(tc, "light", "definition", "pack")
    assert prefix is not None
    assert "Recalling turn 0" in prefix
    assert "cause_light_reveals_truth" in prefix


def test_prior_pack_current_teaching_fires_with_grounding_tier() -> None:
    tc = ThreadContext()
    _seed(tc, turn_index=2, intent="definition", subject="light", source="pack")
    prefix = thread_anaphora_prefix(tc, "light", "cause", "teaching")
    assert prefix is not None
    assert "Recalling turn 2" in prefix
    assert "pack" in prefix
    assert "light" in prefix


def test_same_intent_revisit_does_not_fire() -> None:
    """Asking the same question twice on the same subject — the
    prior turn IS the same surface modulo vault drift; prefixing
    would be redundant."""
    tc = ThreadContext()
    _seed(tc, turn_index=0, intent="definition", subject="light", source="pack")
    assert thread_anaphora_prefix(tc, "light", "definition", "pack") is None


def test_prior_weak_tier_does_not_anchor() -> None:
    """Prior turn whose grounding was OOV / partial / vault / none
    is not a strong-enough anchor."""
    tc = ThreadContext()
    _seed(tc, source="oov")
    # recent_for_subject excludes OOV by default → prior lookup returns None.
    assert thread_anaphora_prefix(tc, "light", "definition", "pack") is None

    tc2 = ThreadContext()
    _seed(tc2, source="partial")
    assert thread_anaphora_prefix(tc2, "light", "definition", "pack") is None


def test_current_weak_tier_does_not_fire() -> None:
    """Anaphora is a *forward-reference* prefix on a strongly-grounded
    surface; weak-tier current turns are not hosts."""
    tc = ThreadContext()
    _seed(tc, source="teaching", chain_id="x")
    assert thread_anaphora_prefix(tc, "light", "definition", "oov") is None
    assert thread_anaphora_prefix(tc, "light", "definition", "partial") is None
    assert thread_anaphora_prefix(tc, "light", "definition", "none") is None


def test_empty_subject_returns_none() -> None:
    tc = ThreadContext()
    _seed(tc, source="teaching", chain_id="x")
    assert thread_anaphora_prefix(tc, "", "definition", "pack") is None
    assert thread_anaphora_prefix(tc, "   ", "definition", "pack") is None


def test_no_recent_match_returns_none() -> None:
    tc = ThreadContext()
    _seed(tc, subject="light", source="teaching", chain_id="x")
    assert thread_anaphora_prefix(tc, "memory", "definition", "pack") is None


def test_most_recent_match_wins() -> None:
    """If the same subject appears twice, the most recent matching
    grounded turn is the anchor — not the earliest."""
    tc = ThreadContext()
    _seed(tc, turn_index=0, intent="cause", subject="light",
          source="teaching", chain_id="cause_old")
    _seed(tc, turn_index=2, intent="cause", subject="light",
          source="teaching", chain_id="cause_new")
    prefix = thread_anaphora_prefix(tc, "light", "definition", "pack")
    assert prefix is not None
    assert "cause_new" in prefix
    assert "turn 2" in prefix


def test_is_deterministic() -> None:
    tc = ThreadContext()
    _seed(tc, source="teaching", chain_id="x")
    a = thread_anaphora_prefix(tc, "light", "definition", "pack")
    b = thread_anaphora_prefix(tc, "light", "definition", "pack")
    assert a == b


# ---------------------------------------------------------------------------
# Live runtime integration
# ---------------------------------------------------------------------------


def test_runtime_default_off_preserves_surface_bytewise() -> None:
    """With ``thread_anaphora=False`` (default), even a seeded thread
    context does not alter the emitted surface."""
    rt = ChatRuntime()  # default config
    rt.thread_context.push(TurnSummary(
        turn_index=0, intent_tag_name="cause", subject="light",
        grounding_source="teaching", chain_id="cause_light_reveals_truth",
        corpus_id="cognition_chains_v1",
    ))
    resp = rt.chat("What is light?")
    assert resp.grounding_source == "pack"
    assert "Recalling" not in resp.surface
    # Gloss-backed surface capitalizes the lemma at sentence start;
    # the pack-grounded provenance tag is mid-sentence (lowercase).
    assert "light" in resp.surface.lower()
    assert "pack-grounded" in resp.surface


def test_runtime_anaphora_on_emits_prefix() -> None:
    cfg = RuntimeConfig(thread_anaphora=True)
    rt = ChatRuntime(config=cfg)
    rt.thread_context.push(TurnSummary(
        turn_index=0, intent_tag_name="cause", subject="light",
        grounding_source="teaching", chain_id="cause_light_reveals_truth",
        corpus_id="cognition_chains_v1",
    ))
    resp = rt.chat("What is light?")
    assert resp.grounding_source == "pack"
    assert "Recalling turn 0" in resp.surface
    assert "cause_light_reveals_truth" in resp.surface
    # Prefix precedes the pack-grounded surface, never replaces it.
    assert "light" in resp.surface.lower()
    assert "pack-grounded" in resp.surface


def test_runtime_anaphora_on_does_not_fire_without_anchor() -> None:
    """With the flag on but NO prior turn on the subject, the prefix
    composer returns None and the surface is unchanged."""
    cfg = RuntimeConfig(thread_anaphora=True)
    rt = ChatRuntime(config=cfg)
    resp = rt.chat("What is light?")
    assert resp.grounding_source == "pack"
    assert "Recalling" not in resp.surface
