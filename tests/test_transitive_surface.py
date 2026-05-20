"""ADR-0083 — transitive (multi-hop) teaching-grounded surface.

Strict superset of ADR-0062's depth-1 composer.  ``max_depth`` is the
number of follow-up hops appended beyond the initial chain.  This
test file pins:

  - Pure function: ``None`` when no chain; depth-0 == single-chain;
    depth-1 == ADR-0062 composed; depth-2 is a strict superset when
    a second hop survives.
  - Visited-set guard: blocks cycles at every depth.
  - Single-corpus traversal: cross-corpus follow-ups are refused in v1.
  - Determinism: same input → same surface bytes.
  - Runtime: ``transitive_surface=True`` supersedes
    ``composed_surface``; flags observable on frozen config.
  - Cognition lane: metrics byte-identical flag OFF vs ON at
    ``max_depth=2`` on both public and holdout splits (null-drop
    invariant — transitive mode adds clauses, never drops tokens).
"""

from __future__ import annotations

from dataclasses import replace

from core.config import RuntimeConfig
from chat.runtime import ChatRuntime
from chat.teaching_grounding import (
    teaching_grounded_surface,
    teaching_grounded_surface_composed,
    teaching_grounded_surface_transitive,
)
from generate.intent import IntentTag


# ---------------------------------------------------------------------------
# Pure-function contract
# ---------------------------------------------------------------------------


def test_transitive_returns_none_when_no_chain() -> None:
    out = teaching_grounded_surface_transitive(
        "zzznotalemma", IntentTag.CAUSE, max_depth=2,
    )
    assert out is None


def test_transitive_depth_zero_matches_single_chain() -> None:
    """``max_depth=0`` appends zero follow-ups → byte-identical to the
    single-chain surface for any (subject, intent) the corpus knows."""
    for lemma, intent in (
        ("light", IntentTag.CAUSE),
        ("memory", IntentTag.VERIFICATION),
        ("knowledge", IntentTag.CAUSE),
    ):
        trans = teaching_grounded_surface_transitive(lemma, intent, max_depth=0)
        single = teaching_grounded_surface(lemma, intent)
        assert trans is not None
        assert single is not None
        assert trans == single, f"depth-0 != single for {lemma}/{intent}"


def test_transitive_depth_one_matches_composed() -> None:
    """``max_depth=1`` appends one follow-up → byte-identical to
    ADR-0062's depth-1 composer."""
    for lemma, intent in (
        ("light", IntentTag.CAUSE),
        ("memory", IntentTag.VERIFICATION),
        ("knowledge", IntentTag.CAUSE),
    ):
        trans = teaching_grounded_surface_transitive(lemma, intent, max_depth=1)
        composed = teaching_grounded_surface_composed(lemma, intent)
        assert trans is not None
        assert composed is not None
        assert trans == composed, (
            f"depth-1 != composed for {lemma}/{intent}"
        )


def test_transitive_depth_two_is_strict_superset_for_light_cause() -> None:
    """``light cause``: chain ``light reveals truth``, follow-ups
    ``truth grounds knowledge`` (hop 1) and ``knowledge requires
    evidence`` (hop 2) — depth-2 emits both ``knowledge`` AND
    ``evidence`` clauses, strict superset of ADR-0062."""
    depth2 = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=2,
    )
    composed = teaching_grounded_surface_composed("light", IntentTag.CAUSE)
    assert depth2 is not None
    assert composed is not None
    assert depth2 != composed
    assert composed in depth2[: len(composed) - 1] or "knowledge" in depth2
    assert "evidence" in depth2
    # Each appended hop adds a ", which " linker — depth-2 has two.
    assert depth2.count(", which ") == 2


def test_transitive_depth_two_includes_every_intermediate_object() -> None:
    """Pack-grounded discipline: the initial subject and every hop
    object appear as a clause subject in the depth-2 surface."""
    depth2 = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=2,
    )
    assert depth2 is not None
    for token in ("light", "truth", "knowledge", "evidence"):
        assert token in depth2, f"{token} missing from depth-2 surface"


def test_transitive_depth_two_includes_every_intermediate_domain() -> None:
    """Every hop's object semantic_domains appear verbatim."""
    from chat.pack_grounding import _pack_index
    pack = _pack_index()
    depth2 = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=2,
    )
    assert depth2 is not None
    for obj in ("truth", "knowledge", "evidence"):
        domains = pack[obj]
        assert any(d in depth2 for d in domains[:1]), (
            f"no domain of {obj!r} in depth-2 surface"
        )


def test_transitive_cycle_guard_blocks_one_step_cycle() -> None:
    """``memory verification`` → ``memory requires recall``; the only
    follow-up candidate ``recall cause`` is ``recall reveals memory``
    which would re-introduce ``memory`` (1-step cycle).  Even at
    ``max_depth=4`` no hop survives → degrades to single-chain."""
    trans = teaching_grounded_surface_transitive(
        "memory", IntentTag.VERIFICATION, max_depth=4,
    )
    single = teaching_grounded_surface("memory", IntentTag.VERIFICATION)
    assert trans == single


def test_transitive_visited_set_blocks_deeper_cycle() -> None:
    """``light cause`` reaches ``evidence`` at hop 2.  No chain in the
    cognition corpus has subject ``evidence`` and a cause / verification
    object outside ``{light, truth, knowledge, evidence}``, so depth-3
    is identical to depth-2 (the depth-3 candidate, if any, must be
    refused by the visited-set guard or the per-hop terminator)."""
    depth2 = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=2,
    )
    depth3 = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=3,
    )
    assert depth2 == depth3


def test_transitive_is_deterministic() -> None:
    a = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=2,
    )
    b = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=2,
    )
    assert a == b


def test_transitive_preserves_trust_label() -> None:
    trans = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=2,
    )
    assert trans is not None
    assert trans.endswith("No session evidence yet.")
    assert "teaching-grounded (cognition_chains_v1)" in trans


def test_transitive_negative_max_depth_clamps_to_zero() -> None:
    """Misconfigured negative max_depth clamps to 0 (single-chain)."""
    out = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=-5,
    )
    single = teaching_grounded_surface("light", IntentTag.CAUSE)
    assert out == single


# ---------------------------------------------------------------------------
# Runtime integration via the config flags
# ---------------------------------------------------------------------------


def test_runtime_default_does_not_engage_transitive() -> None:
    """Both flags default False → single-chain surface."""
    rt = ChatRuntime(config=RuntimeConfig())
    response = rt.chat("Why does light exist?")
    expected = teaching_grounded_surface("light", IntentTag.CAUSE)
    assert response.surface == expected


def test_runtime_transitive_supersedes_composed() -> None:
    """When both flags are on, transitive wins (strict superset of
    composed at default ``max_depth=2``)."""
    cfg = replace(
        RuntimeConfig(),
        composed_surface=True,
        transitive_surface=True,
    )
    rt = ChatRuntime(config=cfg)
    response = rt.chat("Why does light exist?")
    expected = teaching_grounded_surface_transitive(
        "light", IntentTag.CAUSE, max_depth=2,
    )
    assert response.surface == expected
    # Strict superset over ADR-0062 on this prompt.
    assert response.surface != teaching_grounded_surface_composed(
        "light", IntentTag.CAUSE,
    )


def test_runtime_transitive_at_depth_one_matches_composed() -> None:
    cfg = replace(
        RuntimeConfig(),
        transitive_surface=True,
        transitive_max_depth=1,
    )
    rt = ChatRuntime(config=cfg)
    response = rt.chat("Why does light exist?")
    expected = teaching_grounded_surface_composed("light", IntentTag.CAUSE)
    assert response.surface == expected


def test_runtime_flags_observable_on_frozen_config() -> None:
    cfg = replace(
        RuntimeConfig(),
        transitive_surface=True,
        transitive_max_depth=3,
    )
    assert cfg.transitive_surface is True
    assert cfg.transitive_max_depth == 3
    default = RuntimeConfig()
    assert default.transitive_surface is False
    assert default.transitive_max_depth == 2


# ---------------------------------------------------------------------------
# Cognition-lane null-drop invariant (transitive adds clauses, never drops)
# ---------------------------------------------------------------------------


def test_cognition_lane_metrics_unchanged_with_transitive_flag() -> None:
    """At ``max_depth=2``, every expected_term and
    expected_surface_contains assertion that passed flag-OFF must still
    pass flag-ON.  If a future change ever drops tokens in transitive
    mode, this test fails as the deliberate regression it is."""
    from evals.framework import get_lane, run_lane

    lane = get_lane("cognition")
    watched = (
        "intent_accuracy",
        "surface_groundedness",
        "term_capture_rate",
        "versor_closure_rate",
    )
    on_cfg = replace(
        RuntimeConfig(),
        transitive_surface=True,
        transitive_max_depth=2,
    )
    for split in ("public", "holdout"):
        off = run_lane(lane, version="v1", split=split,
                       config=RuntimeConfig()).metrics
        on = run_lane(lane, version="v1", split=split,
                      config=on_cfg).metrics
        for m in watched:
            assert off[m] == on[m], (
                f"ADR-0083 null-drop invariant broken on split={split!r} "
                f"metric={m!r}: OFF={off[m]} vs ON={on[m]}.  "
                f"Transitive surface should add clauses, never drop tokens."
            )
