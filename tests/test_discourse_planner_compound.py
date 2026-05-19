"""Tests for ``plan_compound_discourse``.

Pins:

* Sub-plans are concatenated in source order — never re-sorted.
* A ``TRANSITION`` bridge move (fact=None) is inserted between
  consecutive sub-plans; topic = next anchor's topic; given = prior
  topics forward.
* Single-part compounds are byte-equivalent to ``plan_discourse``.
* Empty bundles for one part cause that part to be skipped without
  breaking source order for the remaining parts.
* Plan equality and ``to_json`` are deterministic for compound plans.
"""

from __future__ import annotations

from generate.discourse_planner import (
    CompoundIntent,
    DiscourseMoveKind,
    DiscoursePlan,
    FactSource,
    GroundedFact,
    GroundingBundle,
    plan_compound_discourse,
    plan_discourse,
)
from generate.intent import (
    DialogueIntent,
    IntentTag,
    ResponseMode,
)


def _truth_def_intent() -> DialogueIntent:
    return DialogueIntent(tag=IntentTag.DEFINITION, subject="truth")


def _truth_cause_intent() -> DialogueIntent:
    return DialogueIntent(tag=IntentTag.CAUSE, subject="truth")


def _knowledge_def_intent() -> DialogueIntent:
    return DialogueIntent(tag=IntentTag.DEFINITION, subject="knowledge")


def _truth_bundle() -> GroundingBundle:
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
            GroundedFact(
                subject="truth", predicate="reveals", obj="knowledge",
                source=FactSource.TEACHING,
                source_id="cognition_chains_v1#cause_truth_reveals_knowledge",
            ),
        )
    )


def _knowledge_bundle() -> GroundingBundle:
    return GroundingBundle(
        facts=(
            GroundedFact(
                subject="knowledge", predicate="is_defined_as",
                obj="justified true belief", source=FactSource.PACK,
                source_id="en_core_cognition_v1:knowledge#gloss",
            ),
            GroundedFact(
                subject="knowledge", predicate="requires", obj="evidence",
                source=FactSource.TEACHING,
                source_id="cognition_chains_v1#cause_knowledge_requires_evidence",
            ),
        )
    )


# ---------------------------------------------------------------------------
# Single-part fall-through
# ---------------------------------------------------------------------------


class TestSinglePartFallthrough:
    def test_single_part_equals_plan_discourse(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(),), raw_text="What is truth?"
        )
        composed = plan_compound_discourse(
            compound, ResponseMode.EXPLAIN, (_truth_bundle(),)
        )
        direct = plan_discourse(
            _truth_def_intent(), ResponseMode.EXPLAIN, _truth_bundle()
        )
        assert composed == direct


# ---------------------------------------------------------------------------
# Multi-part composition
# ---------------------------------------------------------------------------


class TestMultiPartComposition:
    def test_two_part_compound_concatenates_in_source_order(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(), _knowledge_def_intent()),
            raw_text="What is truth, and what is knowledge?",
        )
        plan = plan_compound_discourse(
            compound, ResponseMode.EXPLAIN, (_truth_bundle(), _knowledge_bundle())
        )
        # First sub-plan starts with truth ANCHOR; somewhere between
        # the two sub-plans a TRANSITION bridge appears; second sub-plan
        # starts with knowledge ANCHOR.
        kinds = [m.kind for m in plan.moves]
        topics = [m.topic for m in plan.moves]
        # ANCHOR positions: first move and the move after the bridge.
        assert plan.moves[0].kind is DiscourseMoveKind.ANCHOR
        assert plan.moves[0].topic == "truth"
        # The bridge is TRANSITION with fact=None.
        bridge_idx = next(
            i for i, m in enumerate(plan.moves)
            if m.kind is DiscourseMoveKind.TRANSITION and m.fact is None
        )
        assert plan.moves[bridge_idx + 1].kind is DiscourseMoveKind.ANCHOR
        assert plan.moves[bridge_idx + 1].topic == "knowledge"
        # No cross-part re-sorting: knowledge ANCHOR never precedes truth ANCHOR.
        truth_anchor_idx = topics.index("truth")
        knowledge_anchor_idx = topics.index("knowledge")
        assert truth_anchor_idx < knowledge_anchor_idx
        _ = kinds

    def test_bridge_carries_prior_topics_in_given(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(), _knowledge_def_intent()),
            raw_text="What is truth, and what is knowledge?",
        )
        plan = plan_compound_discourse(
            compound, ResponseMode.EXPLAIN, (_truth_bundle(), _knowledge_bundle())
        )
        bridge = next(
            m for m in plan.moves
            if m.kind is DiscourseMoveKind.TRANSITION and m.fact is None
        )
        assert "truth" in bridge.given
        assert bridge.topic == "knowledge"

    def test_compound_plan_carries_primary_intent(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(), _truth_cause_intent()),
            raw_text="What is truth, and why does it matter?",
        )
        plan = plan_compound_discourse(
            compound, ResponseMode.EXPLAIN,
            (_truth_bundle(), _truth_bundle()),
        )
        # primary intent is the first part — DEFINITION(truth).
        assert plan.intent.tag is IntentTag.DEFINITION
        assert plan.intent.subject == "truth"


# ---------------------------------------------------------------------------
# Degenerate cases
# ---------------------------------------------------------------------------


class TestDegenerateCases:
    def test_part_with_empty_bundle_skipped_preserving_order(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(), _knowledge_def_intent()),
            raw_text="What is truth, and what is knowledge?",
        )
        plan = plan_compound_discourse(
            compound, ResponseMode.EXPLAIN,
            (_truth_bundle(), GroundingBundle()),
        )
        topics = [m.topic for m in plan.moves]
        # knowledge has no substrate ⇒ knowledge sub-plan is empty ⇒
        # bridge is not added ⇒ plan reduces to just the truth sub-plan.
        assert "knowledge" not in topics
        assert "truth" in topics

    def test_all_empty_bundles_produces_empty_compound_plan(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(), _knowledge_def_intent()),
            raw_text="What is truth, and what is knowledge?",
        )
        plan = plan_compound_discourse(
            compound, ResponseMode.EXPLAIN,
            (GroundingBundle(), GroundingBundle()),
        )
        assert plan.is_empty()

    def test_misaligned_parts_and_bundles_raises(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(),), raw_text="What is truth?"
        )
        try:
            plan_compound_discourse(
                compound, ResponseMode.EXPLAIN,
                (_truth_bundle(), _knowledge_bundle()),  # too many bundles
            )
        except ValueError as exc:
            assert "must align" in str(exc)
        else:
            raise AssertionError("Expected ValueError on misaligned input")


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestCompoundDeterminism:
    def test_compound_plan_is_byte_stable(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(), _knowledge_def_intent()),
            raw_text="What is truth, and what is knowledge?",
        )
        bundles = (_truth_bundle(), _knowledge_bundle())
        encoded = [
            plan_compound_discourse(compound, ResponseMode.EXPLAIN, bundles).to_json()
            for _ in range(8)
        ]
        assert len(set(encoded)) == 1

    def test_compound_plan_equality(self) -> None:
        compound = CompoundIntent(
            parts=(_truth_def_intent(), _truth_cause_intent()),
            raw_text="What is truth, and why does it matter?",
        )
        bundles = (_truth_bundle(), _truth_bundle())
        a = plan_compound_discourse(compound, ResponseMode.EXPLAIN, bundles)
        b = plan_compound_discourse(compound, ResponseMode.EXPLAIN, bundles)
        assert a == b
        assert isinstance(a, DiscoursePlan)
