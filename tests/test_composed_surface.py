"""ADR-0062 — composed teaching-grounded surface (chain-of-chains).

When a chain ``(A, intent_A, conn_A, B)`` is grounded and a follow-up
chain ``(B, ?, conn_B, C)`` exists in the corpus, the composed
composer extends the single-chain surface with a second clause:

    "{A} — teaching-grounded ({corpus_id}): {dA}. {A} {conn_A} {B}
     ({dB}), which {conn_B} {C} ({dC}). No session evidence yet."

This test file pins:

  - Default config keeps the flag off → byte-identical single-chain
    surface.
  - Flag-on with a follow-up available → composed two-clause surface.
  - Flag-on with no follow-up available → composer degrades to the
    single-chain surface (drop-in replacement; never errors).
  - Cycle guard: 1-step cycles (A→B, B→A) are not followed.
  - Determinism: same input → same surface bytes.
  - Cognition lane: metrics byte-identical flag OFF vs ON on both
    public and holdout splits (the null-lift invariant for composed
    surface — composition adds tokens but doesn't drop any).
"""

from __future__ import annotations

from dataclasses import replace

from core.config import RuntimeConfig
from chat.runtime import ChatRuntime
from chat.teaching_grounding import (
    teaching_grounded_surface,
    teaching_grounded_surface_composed,
)
from generate.intent import IntentTag


# ---------------------------------------------------------------------------
# Pure-function contract
# ---------------------------------------------------------------------------


def test_composed_returns_none_when_no_chain() -> None:
    """No chain for (subject, intent) → None, matching the
    single-chain composer's behaviour."""
    out = teaching_grounded_surface_composed("zzznotalemma", IntentTag.CAUSE)
    assert out is None


def test_composed_degrades_to_single_chain_when_no_follow_up() -> None:
    """``memory verification`` has no follow-up chain whose subject
    is its object (``recall``) that doesn't cycle back to ``memory``
    — composer degrades to the single-chain surface byte-identically."""
    composed = teaching_grounded_surface_composed("memory", IntentTag.VERIFICATION)
    single = teaching_grounded_surface("memory", IntentTag.VERIFICATION)
    assert composed is not None
    assert single is not None
    assert composed == single


def test_composed_produces_two_clause_when_follow_up_exists() -> None:
    """``light cause`` has ``light reveals truth`` AND there exists a
    follow-up ``truth cause`` (``truth grounds knowledge``).  The
    composed surface must contain both ``light`` and ``knowledge``."""
    composed = teaching_grounded_surface_composed("light", IntentTag.CAUSE)
    single = teaching_grounded_surface("light", IntentTag.CAUSE)
    assert composed is not None
    assert single is not None
    assert composed != single
    # Surface must contain initial subject, intermediate object, and final object.
    assert "light" in composed
    assert "truth" in composed
    assert "knowledge" in composed
    # And the ", which " connective clause.
    assert ", which " in composed


def test_composed_includes_intermediate_and_final_domains() -> None:
    """Pack-grounded discipline: both the intermediate object's
    semantic_domains AND the final object's semantic_domains appear
    verbatim in the composed surface."""
    from chat.pack_grounding import _pack_index
    pack = _pack_index()
    truth_d = pack["truth"]
    knowledge_d = pack["knowledge"]

    composed = teaching_grounded_surface_composed("light", IntentTag.CAUSE)
    assert composed is not None
    assert any(d in composed for d in truth_d[:1])
    assert any(d in composed for d in knowledge_d[:1])


def test_composed_is_deterministic() -> None:
    a = teaching_grounded_surface_composed("light", IntentTag.CAUSE)
    b = teaching_grounded_surface_composed("light", IntentTag.CAUSE)
    assert a == b


def test_composed_cycle_guard_blocks_one_step_cycle() -> None:
    """``memory verification`` → ``memory requires recall``; the only
    follow-up candidate ``recall cause`` is ``recall reveals memory``
    which would re-introduce ``memory`` (1-step cycle).  Composer
    must not follow.  Surface == single-chain surface."""
    composed = teaching_grounded_surface_composed("memory", IntentTag.VERIFICATION)
    single = teaching_grounded_surface("memory", IntentTag.VERIFICATION)
    assert composed == single


def test_composed_preserves_trust_label() -> None:
    """The trailing ``No session evidence yet.`` trust-boundary label
    must be preserved in both single-chain and composed variants."""
    composed = teaching_grounded_surface_composed("light", IntentTag.CAUSE)
    assert composed is not None
    assert "No session evidence yet." in composed


# ---------------------------------------------------------------------------
# Runtime integration via the config flag
# ---------------------------------------------------------------------------


def test_runtime_default_uses_single_chain() -> None:
    """Default ``RuntimeConfig`` keeps ``composed_surface=False`` →
    runtime emits the single-chain surface for ``Why does light exist?``."""
    rt = ChatRuntime(config=RuntimeConfig())
    response = rt.chat("Why does light exist?")
    expected = teaching_grounded_surface("light", IntentTag.CAUSE)
    assert response.surface == expected


def test_runtime_with_flag_on_uses_composed() -> None:
    rt = ChatRuntime(config=replace(RuntimeConfig(), composed_surface=True))
    response = rt.chat("Why does light exist?")
    expected = teaching_grounded_surface_composed("light", IntentTag.CAUSE)
    assert response.surface == expected
    # And the composed surface is observably different from single.
    assert response.surface != teaching_grounded_surface("light", IntentTag.CAUSE)


def test_runtime_flag_is_observable_on_frozen_config() -> None:
    cfg = replace(RuntimeConfig(), composed_surface=True)
    assert cfg.composed_surface is True
    assert RuntimeConfig().composed_surface is False


# ---------------------------------------------------------------------------
# Cognition-lane null-lift invariant (composed mode adds tokens, never drops)
# ---------------------------------------------------------------------------


def test_cognition_lane_metrics_unchanged_with_composed_flag() -> None:
    """Composed mode emits a strictly longer surface with one
    additional follow-up clause; every expected_term that passed
    flag-OFF must still pass flag-ON.  Public + holdout splits.
    If a future change drops tokens in composed mode (e.g. omitting
    the intermediate object), this test fails as a regression."""
    from evals.framework import get_lane, run_lane

    lane = get_lane("cognition")
    watched = ("intent_accuracy", "surface_groundedness",
               "term_capture_rate", "versor_closure_rate")
    for split in ("public", "holdout"):
        off = run_lane(lane, version="v1", split=split,
                       config=RuntimeConfig()).metrics
        on = run_lane(lane, version="v1", split=split,
                      config=replace(RuntimeConfig(), composed_surface=True)).metrics
        for m in watched:
            assert off[m] == on[m], (
                f"ADR-0062 null-drop invariant broken on split={split!r} "
                f"metric={m!r}: OFF={off[m]} vs ON={on[m]}.  "
                f"Composed surface should add tokens, never drop them."
            )
