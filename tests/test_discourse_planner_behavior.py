"""Behavior tests for ``plan_discourse`` (step 4).

These tests pin move-selection rules per ``ResponseMode``:

* BRIEF     → exactly one ANCHOR.
* EXPLAIN   → ANCHOR + (SUPPORT) + (RELATION).
* PARAGRAPH → ANCHOR + (SUPPORT) + (RELATION) + (TRANSITION) + (CLOSURE).
* EXAMPLE   → ANCHOR + (RELATION) + (CLOSURE).
* WALKTHROUGH → falls back to BRIEF (deferred).

Determinism is verified end-to-end: ``(intent, mode, bundle)`` ⇒ same
plan ⇒ same canonical JSON.  This is the precondition for the future
ADR that folds ``DiscoursePlan`` into ``compute_trace_hash``.

Bundles are constructed by hand so the planner's selection rules are
tested in isolation from the live pack/teaching corpora.  Integration
with ``grounding_bundle_for`` is verified in step 5 once the runtime
flag is wired up.
"""

from __future__ import annotations

import pytest

from generate.discourse_planner import (
    DialogueIntent,
    DiscourseMoveKind,
    FactSource,
    GroundedFact,
    GroundingBundle,
    IntentTag,
    ResponseMode,
    plan_discourse,
)


def _intent(tag: IntentTag = IntentTag.DEFINITION, subject: str = "truth") -> DialogueIntent:
    return DialogueIntent(tag=tag, subject=subject)


def _full_bundle() -> GroundingBundle:
    """Bundle with anchor + support + relation + transition pieces.

    Topic: ``truth``
        ANCHOR     : truth is_defined_as ...
        SUPPORT    : truth belongs_to epistemic_domain
        RELATION   : truth reveals knowledge   (teaching)
        TRANSITION : knowledge requires evidence (teaching, new topic)
    """

    return GroundingBundle(
        facts=(
            GroundedFact(
                subject="truth",
                predicate="is_defined_as",
                obj="that which corresponds to reality",
                source=FactSource.PACK,
                source_id="en_core_cognition_v1:truth#gloss",
            ),
            GroundedFact(
                subject="truth",
                predicate="belongs_to",
                obj="epistemic_domain",
                source=FactSource.PACK,
                source_id="en_core_cognition_v1:truth#domain:0",
            ),
            GroundedFact(
                subject="truth",
                predicate="reveals",
                obj="knowledge",
                source=FactSource.TEACHING,
                source_id="cognition_chains_v1#cause_truth_reveals_knowledge",
            ),
            GroundedFact(
                subject="knowledge",
                predicate="requires",
                obj="evidence",
                source=FactSource.TEACHING,
                source_id="cognition_chains_v1#cause_knowledge_requires_evidence",
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
# BRIEF
# ---------------------------------------------------------------------------


class TestBriefMode:
    def test_brief_emits_anchor_only(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.BRIEF, _full_bundle())
        kinds = [m.kind for m in plan.moves]
        assert kinds == [DiscourseMoveKind.ANCHOR]

    def test_brief_anchor_prefers_is_defined_as(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.BRIEF, _full_bundle())
        anchor = plan.anchor()
        assert anchor is not None
        assert anchor.fact is not None
        assert anchor.fact.predicate == "is_defined_as"


# ---------------------------------------------------------------------------
# EXPLAIN
# ---------------------------------------------------------------------------


class TestExplainMode:
    def test_explain_emits_anchor_support_relation(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.EXPLAIN, _full_bundle())
        kinds = [m.kind for m in plan.moves]
        assert kinds == [
            DiscourseMoveKind.ANCHOR,
            DiscourseMoveKind.SUPPORT,
            DiscourseMoveKind.RELATION,
        ]

    def test_explain_support_is_pack_belongs_to(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.EXPLAIN, _full_bundle())
        support = next(
            m for m in plan.moves if m.kind is DiscourseMoveKind.SUPPORT
        )
        assert support.fact is not None
        assert support.fact.predicate == "belongs_to"
        assert support.fact.source is FactSource.PACK

    def test_explain_relation_is_teaching_chain(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.EXPLAIN, _full_bundle())
        relation = next(
            m for m in plan.moves if m.kind is DiscourseMoveKind.RELATION
        )
        assert relation.fact is not None
        assert relation.fact.source is FactSource.TEACHING

    def test_explain_collapses_when_only_pack_facts(self) -> None:
        plan = plan_discourse(
            _intent(), ResponseMode.EXPLAIN, _pack_only_bundle()
        )
        kinds = [m.kind for m in plan.moves]
        assert kinds == [DiscourseMoveKind.ANCHOR, DiscourseMoveKind.SUPPORT]


# ---------------------------------------------------------------------------
# PARAGRAPH
# ---------------------------------------------------------------------------


class TestParagraphMode:
    def test_paragraph_emits_full_five_moves(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.PARAGRAPH, _full_bundle())
        kinds = [m.kind for m in plan.moves]
        assert kinds == [
            DiscourseMoveKind.ANCHOR,
            DiscourseMoveKind.SUPPORT,
            DiscourseMoveKind.RELATION,
            DiscourseMoveKind.TRANSITION,
            DiscourseMoveKind.CLOSURE,
        ]

    def test_paragraph_transition_changes_topic(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.PARAGRAPH, _full_bundle())
        transition = next(
            m for m in plan.moves if m.kind is DiscourseMoveKind.TRANSITION
        )
        # The transition's topic must differ from the anchor's topic.
        assert transition.topic != "truth"
        assert transition.topic == "knowledge"

    def test_paragraph_closure_has_no_new_content(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.PARAGRAPH, _full_bundle())
        closure = next(
            m for m in plan.moves if m.kind is DiscourseMoveKind.CLOSURE
        )
        assert closure.fact is None
        assert closure.new == ()
        # Closure carries the chain of given lemmas forward.
        assert len(closure.given) > 0

    def test_paragraph_topics_cover_full_chain(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.PARAGRAPH, _full_bundle())
        assert plan.topics() == ("truth", "knowledge")

    def test_paragraph_facts_are_unique(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.PARAGRAPH, _full_bundle())
        used = [m.fact for m in plan.moves if m.fact is not None]
        keys = [f.sort_key() for f in used]
        assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# EXAMPLE
# ---------------------------------------------------------------------------


class TestExampleMode:
    def test_example_emits_anchor_relation_closure(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.EXAMPLE, _full_bundle())
        kinds = [m.kind for m in plan.moves]
        assert kinds == [
            DiscourseMoveKind.ANCHOR,
            DiscourseMoveKind.RELATION,
            DiscourseMoveKind.CLOSURE,
        ]

    def test_example_skips_support(self) -> None:
        plan = plan_discourse(_intent(), ResponseMode.EXAMPLE, _full_bundle())
        kinds = {m.kind for m in plan.moves}
        assert DiscourseMoveKind.SUPPORT not in kinds


# ---------------------------------------------------------------------------
# WALKTHROUGH (deferred)
# ---------------------------------------------------------------------------


class TestWalkthroughMode:
    def test_walkthrough_emits_chain_walk(self) -> None:
        # WALKTHROUGH v1 — sequential teaching-chain walk.  The
        # _full_bundle has a 2-hop chain (truth→knowledge→evidence)
        # plus pack anchor, so the walk emits ANCHOR + RELATION +
        # CLOSURE.  See test_discourse_planner_walkthrough.py for
        # the dedicated suite.
        plan = plan_discourse(_intent(), ResponseMode.WALKTHROUGH, _full_bundle())
        kinds = [m.kind for m in plan.moves]
        assert kinds[0] is DiscourseMoveKind.ANCHOR
        assert DiscourseMoveKind.CLOSURE in kinds or DiscourseMoveKind.RELATION in kinds


# ---------------------------------------------------------------------------
# Empty / degenerate inputs
# ---------------------------------------------------------------------------


class TestDegenerateInputs:
    @pytest.mark.parametrize("mode", list(ResponseMode))
    def test_empty_bundle_returns_empty_plan(self, mode: ResponseMode) -> None:
        plan = plan_discourse(_intent(), mode, GroundingBundle())
        assert plan.is_empty()
        assert plan.intent.subject == "truth"
        assert plan.mode is mode

    def test_anchor_falls_back_to_first_canonical_fact_when_no_pack_subject_match(
        self,
    ) -> None:
        # Bundle only has teaching facts whose subject differs from the
        # intent subject — anchor falls back to the first canonical fact.
        bundle = GroundingBundle(
            facts=(
                GroundedFact(
                    subject="memory", predicate="requires", obj="recall",
                    source=FactSource.TEACHING,
                    source_id="cognition_chains_v1#cause_memory_requires_recall",
                ),
            )
        )
        plan = plan_discourse(
            _intent(subject="nonexistent"),
            ResponseMode.BRIEF,
            bundle,
        )
        assert not plan.is_empty()
        anchor = plan.anchor()
        assert anchor is not None
        assert anchor.fact is not None
        assert anchor.fact.subject == "memory"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestPlannerDeterminism:
    @pytest.mark.parametrize("mode", list(ResponseMode))
    def test_plan_is_byte_stable_across_calls(self, mode: ResponseMode) -> None:
        bundle = _full_bundle()
        intent = _intent()
        encoded = [
            plan_discourse(intent, mode, bundle).to_json() for _ in range(8)
        ]
        assert len(set(encoded)) == 1

    def test_plan_is_pure_function(self) -> None:
        # Same inputs ⇒ equal plans (including positional move order).
        a = plan_discourse(_intent(), ResponseMode.PARAGRAPH, _full_bundle())
        b = plan_discourse(_intent(), ResponseMode.PARAGRAPH, _full_bundle())
        assert a == b
