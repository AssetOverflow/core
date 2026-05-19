"""Contract tests for ``generate/discourse_planner.py``.

These tests pin the **serialization determinism** invariant that a
later ADR will rely on when folding ``DiscoursePlan`` into
``compute_trace_hash``.  Adding the determinism gate *before* the
hash dependency is the explicit sequencing requirement: replay
regressions must surface as clean test failures, not as flaky
paragraph turns downstream.

What this file is **not**:

* Not a runtime/wiring test — nothing here imports ``chat.*`` or
  exercises a live ``ChatRuntime``.  At this stage the planner has
  no runtime path; cognition-eval byte-identity is asserted by the
  existing eval lane, not here.
* Not a planner-behavior test — ``plan_discourse`` is contract-only
  in this landing and raises ``NotImplementedError``.  Move-selection
  rules will be tested in the follow-up ADR.
"""

from __future__ import annotations

import inspect
import json

import pytest

from generate.discourse_planner import (
    DialogueIntent,
    DiscourseMove,
    DiscourseMoveKind,
    DiscoursePlan,
    FactSource,
    GroundedFact,
    GroundingBundle,
    IntentTag,
    Relation,
    ResponseMode,
    plan_discourse,
)


def _make_intent() -> DialogueIntent:
    return DialogueIntent(tag=IntentTag.DEFINITION, subject="truth")


def _make_facts() -> tuple[GroundedFact, ...]:
    return (
        GroundedFact(
            subject="truth",
            predicate="reveals",
            obj="knowledge",
            source=FactSource.TEACHING,
            source_id="cognition_chains_v1#cause_truth_reveals_knowledge",
        ),
        GroundedFact(
            subject="truth",
            predicate="is_defined_as",
            obj="that which corresponds to reality",
            source=FactSource.PACK,
            source_id="en_core_cognition_v1:truth",
        ),
        GroundedFact(
            subject="truth",
            predicate="belongs_to",
            obj="epistemic_domain",
            source=FactSource.PACK,
            source_id="en_core_cognition_v1:truth#domain",
        ),
    )


def _make_plan() -> DiscoursePlan:
    facts = _make_facts()
    # pack fact[1] is the anchor (is_defined_as), pack fact[2] supports
    # (belongs_to), teaching fact[0] is the relation.
    moves = (
        DiscourseMove(
            kind=DiscourseMoveKind.ANCHOR,
            topic="truth",
            given=(),
            new=("truth",),
            relation_to_previous=None,
            fact=facts[1],
        ),
        DiscourseMove(
            kind=DiscourseMoveKind.SUPPORT,
            topic="truth",
            given=("truth",),
            new=("epistemic_domain",),
            relation_to_previous=Relation.ELABORATION,
            fact=facts[2],
        ),
        DiscourseMove(
            kind=DiscourseMoveKind.RELATION,
            topic="truth",
            given=("truth", "epistemic_domain"),
            new=("knowledge",),
            relation_to_previous=Relation.CAUSE,
            fact=facts[0],
        ),
    )
    return DiscoursePlan(
        intent=_make_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=moves,
    )


# ---------------------------------------------------------------------------
# Immutability / frozen-dataclass invariants
# ---------------------------------------------------------------------------


class TestFrozenInvariants:
    def test_grounded_fact_is_frozen(self) -> None:
        fact = _make_facts()[0]
        with pytest.raises((AttributeError, TypeError)):
            fact.subject = "different"  # type: ignore[misc]

    def test_grounding_bundle_is_frozen(self) -> None:
        bundle = GroundingBundle(facts=_make_facts())
        with pytest.raises((AttributeError, TypeError)):
            bundle.facts = ()  # type: ignore[misc]

    def test_discourse_move_is_frozen(self) -> None:
        plan = _make_plan()
        with pytest.raises((AttributeError, TypeError)):
            plan.moves[0].topic = "lie"  # type: ignore[misc]

    def test_discourse_plan_is_frozen(self) -> None:
        plan = _make_plan()
        with pytest.raises((AttributeError, TypeError)):
            plan.mode = ResponseMode.BRIEF  # type: ignore[misc]

    def test_value_equality(self) -> None:
        assert _make_plan() == _make_plan()
        assert hash(_make_facts()[0]) == hash(_make_facts()[0])


# ---------------------------------------------------------------------------
# Canonical ordering invariants
# ---------------------------------------------------------------------------


class TestCanonicalOrdering:
    def test_fact_source_priority_is_pack_first(self) -> None:
        bundle = GroundingBundle(
            facts=(
                GroundedFact("a", "p", "b", FactSource.OPERATOR, "op:1"),
                GroundedFact("a", "p", "b", FactSource.VAULT, "vault:1"),
                GroundedFact("a", "p", "b", FactSource.TEACHING, "teach:1"),
                GroundedFact("a", "p", "b", FactSource.PACK, "pack:1"),
            )
        )
        sources = tuple(f.source for f in bundle.sorted_facts())
        assert sources == (
            FactSource.PACK,
            FactSource.TEACHING,
            FactSource.VAULT,
            FactSource.OPERATOR,
        )

    def test_sort_is_total_within_same_source(self) -> None:
        bundle = GroundingBundle(
            facts=(
                GroundedFact("zeta", "p", "o", FactSource.PACK, "id:2"),
                GroundedFact("alpha", "p", "o", FactSource.PACK, "id:1"),
                GroundedFact("alpha", "p", "o", FactSource.PACK, "id:0"),
            )
        )
        ordered = bundle.sorted_facts()
        assert ordered[0].subject == "alpha"
        assert ordered[0].source_id == "id:0"
        assert ordered[1].subject == "alpha"
        assert ordered[1].source_id == "id:1"
        assert ordered[2].subject == "zeta"

    def test_bundle_sort_is_idempotent(self) -> None:
        bundle = GroundingBundle(facts=_make_facts())
        once = bundle.sorted_facts()
        twice = GroundingBundle(facts=once).sorted_facts()
        assert once == twice

    def test_facts_by_source_filters_and_orders(self) -> None:
        bundle = GroundingBundle(facts=_make_facts())
        pack_only = bundle.facts_by_source(FactSource.PACK)
        assert all(f.source is FactSource.PACK for f in pack_only)
        assert pack_only == tuple(
            sorted(pack_only, key=GroundedFact.sort_key)
        )


# ---------------------------------------------------------------------------
# Serialization determinism (the gate before trace_hash adoption)
# ---------------------------------------------------------------------------


class TestSerializationDeterminism:
    def test_to_json_is_byte_stable_across_calls(self) -> None:
        plan = _make_plan()
        encoded = [plan.to_json() for _ in range(8)]
        assert len(set(encoded)) == 1

    def test_to_json_is_byte_stable_across_equal_plans(self) -> None:
        a = _make_plan().to_json()
        b = _make_plan().to_json()
        assert a == b

    def test_to_json_uses_sorted_keys(self) -> None:
        encoded = _make_plan().to_json()
        decoded = json.loads(encoded)
        # Re-encoding with sort_keys must round-trip byte-identical.
        reencoded = json.dumps(decoded, sort_keys=True, separators=(",", ":"))
        assert encoded == reencoded

    def test_to_json_has_no_whitespace(self) -> None:
        encoded = _make_plan().to_json()
        assert ", " not in encoded
        assert ": " not in encoded

    def test_as_dict_round_trip_through_json(self) -> None:
        plan = _make_plan()
        decoded = json.loads(plan.to_json())
        assert decoded["intent"]["tag"] == "definition"
        assert decoded["intent"]["subject"] == "truth"
        assert decoded["mode"] == "paragraph"
        assert len(decoded["moves"]) == 3
        assert decoded["moves"][0]["kind"] == "anchor"
        assert decoded["moves"][0]["relation_to_previous"] is None
        assert decoded["moves"][1]["relation_to_previous"] == "elaboration"
        assert decoded["moves"][2]["relation_to_previous"] == "cause"
        assert decoded["moves"][0]["fact"]["source"] == "pack"

    def test_grounded_fact_as_dict_has_object_key_not_obj(self) -> None:
        fact = _make_facts()[0]
        encoded = fact.as_dict()
        assert "object" in encoded
        assert "obj" not in encoded

    def test_bundle_as_dict_is_sorted(self) -> None:
        unordered = (
            GroundedFact("z", "p", "o", FactSource.OPERATOR, "op:0"),
            GroundedFact("a", "p", "o", FactSource.PACK, "pack:0"),
        )
        bundle = GroundingBundle(facts=unordered)
        encoded = bundle.as_dict()
        facts_out = encoded["facts"]
        assert isinstance(facts_out, tuple)
        assert facts_out[0]["source"] == "pack"
        assert facts_out[1]["source"] == "operator"


# ---------------------------------------------------------------------------
# Plan-level shape helpers
# ---------------------------------------------------------------------------


class TestPlanHelpers:
    def test_empty_plan_reports_empty(self) -> None:
        plan = DiscoursePlan(
            intent=_make_intent(),
            mode=ResponseMode.BRIEF,
        )
        assert plan.is_empty()
        assert plan.anchor() is None
        assert plan.topics() == ()

    def test_anchor_returns_first_anchor_move(self) -> None:
        plan = _make_plan()
        anchor = plan.anchor()
        assert anchor is not None
        assert anchor.kind is DiscourseMoveKind.ANCHOR
        assert anchor.topic == "truth"

    def test_topics_preserves_first_introduction_order(self) -> None:
        plan = _make_plan()
        assert plan.topics() == ("truth",)

    def test_empty_bundle_helpers(self) -> None:
        bundle = GroundingBundle()
        assert bundle.is_empty()
        assert bundle.sorted_facts() == ()
        assert bundle.facts_by_source(FactSource.PACK) == ()


# ---------------------------------------------------------------------------
# Planner function signature is pure and contract-only
# ---------------------------------------------------------------------------


class TestPlannerSignature:
    def test_plan_discourse_signature(self) -> None:
        # ``from __future__ import annotations`` makes annotations strings;
        # resolve them via ``get_type_hints`` for an identity comparison.
        from typing import get_type_hints

        sig = inspect.signature(plan_discourse)
        assert list(sig.parameters) == ["intent", "mode", "bundle"]
        hints = get_type_hints(plan_discourse)
        assert hints["intent"] is DialogueIntent
        assert hints["mode"] is ResponseMode
        assert hints["bundle"] is GroundingBundle
        assert hints["return"] is DiscoursePlan

    def test_plan_discourse_is_contract_only(self) -> None:
        with pytest.raises(NotImplementedError):
            plan_discourse(
                _make_intent(),
                ResponseMode.PARAGRAPH,
                GroundingBundle(facts=_make_facts()),
            )

    def test_no_runtime_imports(self) -> None:
        import generate.discourse_planner as dp

        src = inspect.getsource(dp)
        assert "from chat" not in src
        assert "import chat" not in src
        # No clock reads, no env reads, no filesystem.
        assert "time.time" not in src
        assert "datetime.now" not in src
        assert "os.environ" not in src
        assert "open(" not in src
