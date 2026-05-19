"""Tests for ``WALKTHROUGH`` v1 — sequential teaching-chain walk.

Pins:

* ≤ 4 moves total (1 anchor + ≤3 hops) — the hop cap is structural.
* Each hop follows ``(subject, *, object) → (object, *, *)`` along
  the teaching-chain graph; the final hop is a ``CLOSURE`` move.
* When no teaching chain is rooted on the anchor, the planner falls
  back to the expository (ANCHOR + SUPPORT) shape rather than
  fabricating walk steps.  The fallback plan retains
  ``mode=WALKTHROUGH`` so callers can tell the planner attempted a
  walkthrough but degraded honestly.
* Cycle-safe: a teaching cycle ``A→B→A`` walks A→B→A only if the
  facts are distinct; identical facts are never re-emitted.
"""

from __future__ import annotations

from generate.discourse_planner import (
    DiscourseMoveKind,
    FactSource,
    GroundedFact,
    GroundingBundle,
    plan_discourse,
)
from generate.intent import DialogueIntent, IntentTag, ResponseMode


def _intent(subject: str = "truth") -> DialogueIntent:
    return DialogueIntent(tag=IntentTag.DEFINITION, subject=subject)


def _chain_bundle() -> GroundingBundle:
    """4-link teaching chain: truth → knowledge → evidence → recall.

    Plus a pack anchor so ``_select_anchor`` has a definitional fact.
    """
    return GroundingBundle(
        facts=(
            GroundedFact(
                subject="truth", predicate="is_defined_as",
                obj="reality-correspondence", source=FactSource.PACK,
                source_id="en_core_cognition_v1:truth#gloss",
            ),
            GroundedFact(
                subject="truth", predicate="reveals", obj="knowledge",
                source=FactSource.TEACHING,
                source_id="cognition_chains_v1#cause_truth_reveals_knowledge",
            ),
            GroundedFact(
                subject="knowledge", predicate="requires", obj="evidence",
                source=FactSource.TEACHING,
                source_id="cognition_chains_v1#cause_knowledge_requires_evidence",
            ),
            GroundedFact(
                subject="evidence", predicate="supports", obj="recall",
                source=FactSource.TEACHING,
                source_id="cognition_chains_v1#cause_evidence_supports_recall",
            ),
        )
    )


def _pack_only_bundle() -> GroundingBundle:
    return GroundingBundle(
        facts=(
            GroundedFact(
                subject="truth", predicate="is_defined_as",
                obj="reality-correspondence", source=FactSource.PACK,
                source_id="en_core_cognition_v1:truth#gloss",
            ),
            GroundedFact(
                subject="truth", predicate="belongs_to",
                obj="epistemic_domain", source=FactSource.PACK,
                source_id="en_core_cognition_v1:truth#domain:0",
            ),
        )
    )


# ---------------------------------------------------------------------------
# Walk shape
# ---------------------------------------------------------------------------


class TestWalkthroughShape:
    def test_full_chain_emits_anchor_relation_relation_closure(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, _chain_bundle())
        kinds = [m.kind for m in plan.moves]
        # 1 anchor + 3 hops; last hop is CLOSURE.
        assert kinds == [
            DiscourseMoveKind.ANCHOR,
            DiscourseMoveKind.RELATION,
            DiscourseMoveKind.RELATION,
            DiscourseMoveKind.CLOSURE,
        ]

    def test_walk_follows_subject_to_object_to_subject(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, _chain_bundle())
        # Walk invariant applies *across hops* — consecutive teaching
        # facts on the chain.  The anchor is a pack ``is_defined_as``
        # whose obj is a gloss string, not a graph node, so it's
        # excluded.  First hop starts on the anchor's *subject*.
        teaching_moves = [m for m in plan.moves if m.fact is not None and m.fact.source is FactSource.TEACHING]
        for prev, curr in zip(teaching_moves, teaching_moves[1:]):
            assert curr.fact is not None and prev.fact is not None
            assert curr.fact.subject == prev.fact.obj
        # First teaching hop must start on the anchor's subject.
        anchor = plan.anchor()
        assert anchor is not None and anchor.fact is not None
        assert teaching_moves[0].fact is not None
        assert teaching_moves[0].fact.subject == anchor.fact.subject

    def test_hop_cap_at_four_moves(self) -> None:
        # Build a chain longer than the cap.
        long_facts = [
            GroundedFact(
                subject="truth", predicate="is_defined_as",
                obj="reality-correspondence", source=FactSource.PACK,
                source_id="en_core_cognition_v1:truth#gloss",
            ),
        ]
        # 6-link teaching chain.
        chain_subjects = ["truth", "a", "b", "c", "d", "e"]
        chain_objects = ["a", "b", "c", "d", "e", "f"]
        for s, o in zip(chain_subjects, chain_objects):
            long_facts.append(
                GroundedFact(
                    subject=s, predicate="leads_to", obj=o,
                    source=FactSource.TEACHING,
                    source_id=f"chain#{s}_to_{o}",
                )
            )
        bundle = GroundingBundle(facts=tuple(long_facts))
        plan = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, bundle)
        assert len(plan.moves) <= 4

    def test_topics_walk_through_chain(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, _chain_bundle())
        topics = plan.topics()
        # Anchor topic + 3 hop topics.
        assert topics == ("truth", "knowledge", "evidence")


# ---------------------------------------------------------------------------
# Fallback when no chain is rooted on the anchor
# ---------------------------------------------------------------------------


class TestWalkthroughFallback:
    def test_no_chain_falls_back_to_expository(self) -> None:
        plan = plan_discourse(
            _intent(), ResponseMode.WALKTHROUGH, _pack_only_bundle()
        )
        kinds = [m.kind for m in plan.moves]
        # ANCHOR + SUPPORT, no fabricated walk steps.
        assert kinds == [
            DiscourseMoveKind.ANCHOR,
            DiscourseMoveKind.SUPPORT,
        ]

    def test_fallback_plan_retains_walkthrough_mode(self) -> None:
        plan = plan_discourse(
            _intent(), ResponseMode.WALKTHROUGH, _pack_only_bundle()
        )
        # Even though the planner degraded, the mode tag remains
        # WALKTHROUGH so callers can detect "attempted walkthrough,
        # degraded honestly".
        assert plan.mode is ResponseMode.WALKTHROUGH

    def test_pack_only_no_support_returns_anchor_only(self) -> None:
        # Anchor fact only, no support, no teaching chain ⇒ ANCHOR-only
        # plan; mode still WALKTHROUGH.
        bundle = GroundingBundle(
            facts=(
                GroundedFact(
                    subject="truth", predicate="is_defined_as",
                    obj="reality-correspondence", source=FactSource.PACK,
                    source_id="en_core_cognition_v1:truth#gloss",
                ),
            )
        )
        plan = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, bundle)
        kinds = [m.kind for m in plan.moves]
        assert kinds == [DiscourseMoveKind.ANCHOR]
        assert plan.mode is ResponseMode.WALKTHROUGH


# ---------------------------------------------------------------------------
# Cycle safety
# ---------------------------------------------------------------------------


class TestWalkthroughCycleSafety:
    def test_cyclic_chain_does_not_re_emit_same_fact(self) -> None:
        # truth → A → truth (cycle).  Distinct facts, but if a third
        # hop tried to re-walk truth→A, it would re-emit the first
        # fact.  The planner must not.
        bundle = GroundingBundle(
            facts=(
                GroundedFact(
                    subject="truth", predicate="is_defined_as",
                    obj="reality-correspondence", source=FactSource.PACK,
                    source_id="en_core_cognition_v1:truth#gloss",
                ),
                GroundedFact(
                    subject="truth", predicate="produces", obj="echo",
                    source=FactSource.TEACHING,
                    source_id="chain#truth_produces_echo",
                ),
                GroundedFact(
                    subject="echo", predicate="returns_to", obj="truth",
                    source=FactSource.TEACHING,
                    source_id="chain#echo_returns_to_truth",
                ),
            )
        )
        plan = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, bundle)
        fact_keys = [m.fact.sort_key() for m in plan.moves if m.fact is not None]
        assert len(fact_keys) == len(set(fact_keys))


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestWalkthroughDeterminism:
    def test_walk_is_byte_stable(self) -> None:
        encoded = [
            plan_discourse(_intent(), ResponseMode.WALKTHROUGH, _chain_bundle()).to_json()
            for _ in range(8)
        ]
        assert len(set(encoded)) == 1

    def test_walk_equality(self) -> None:
        a = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, _chain_bundle())
        b = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, _chain_bundle())
        assert a == b
