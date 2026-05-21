"""Phase 4 — per-plan articulation telemetry metrics.

Pins ``core.contemplation.plan_metrics.compute_plan_metrics`` against:

  * Trivial cases (empty plan, single anchor)
  * Structural counts (move_kind distribution)
  * Diversity counts (unique predicates / subjects / sources)
  * Topic dynamics (pronominalization opportunities, topic shifts)
  * Derived ratios (predicate_diversity_ratio, subject_focus_ratio)
  * Determinism (same plan → byte-equal metrics dict)
  * Bridge-move handling (fact=None resets focus channel)
"""

from __future__ import annotations

from core.contemplation.plan_metrics import compute_plan_metrics
from generate.discourse_planner import (
    DiscourseMove,
    DiscourseMoveKind,
    DiscoursePlan,
    FactSource,
    GroundedFact,
)
from generate.intent import DialogueIntent, IntentTag, ResponseMode


def _fact(
    subject: str,
    predicate: str,
    obj: str,
    *,
    source: FactSource = FactSource.PACK,
    source_id: str = "test_pack_v1",
) -> GroundedFact:
    return GroundedFact(
        subject=subject,
        predicate=predicate,
        obj=obj,
        source=source,
        source_id=source_id,
    )


def _intent(subject: str = "truth") -> DialogueIntent:
    return DialogueIntent(tag=IntentTag.DEFINITION, subject=subject)


def _move(
    kind: DiscourseMoveKind, fact: GroundedFact | None = None,
) -> DiscourseMove:
    topic = fact.subject if fact is not None else ""
    return DiscourseMove(
        kind=kind, topic=topic, given=(), new=(),
        relation_to_previous=None, fact=fact,
    )


# ---------------------------------------------------------------------------
# Empty plan
# ---------------------------------------------------------------------------


def test_empty_plan_yields_zero_metrics() -> None:
    plan = DiscoursePlan(intent=_intent(), mode=ResponseMode.BRIEF, moves=())
    m = compute_plan_metrics(plan)
    assert m.move_count == 0
    assert m.fact_bearing_count == 0
    assert m.anchor_count == 0
    assert m.unique_predicates == 0
    assert m.unique_subjects == 0
    assert m.unique_sources == 0
    assert m.topic_shift_count == 0
    assert m.pronominalization_opportunities == 0
    assert m.predicate_diversity_ratio is None
    assert m.subject_focus_ratio is None


# ---------------------------------------------------------------------------
# Single-anchor plan
# ---------------------------------------------------------------------------


def test_single_anchor_plan_metrics() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.BRIEF,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
        ),
    )
    m = compute_plan_metrics(plan)
    assert m.move_count == 1
    assert m.fact_bearing_count == 1
    assert m.anchor_count == 1
    assert m.support_count == 0
    assert m.unique_predicates == 1
    assert m.unique_subjects == 1
    assert m.unique_sources == 1
    assert m.topic_shift_count == 0
    assert m.pronominalization_opportunities == 0
    assert m.predicate_diversity_ratio == 1.0
    # No consecutive pairs to measure — ratio undefined
    assert m.subject_focus_ratio is None


# ---------------------------------------------------------------------------
# Move-kind distribution
# ---------------------------------------------------------------------------


def test_move_kind_distribution_counts() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
            _move(
                DiscourseMoveKind.RELATION,
                _fact("truth", "grounds", "knowledge"),
            ),
            _move(
                DiscourseMoveKind.TRANSITION,
                _fact("knowledge", "belongs_to", "cognition.knowledge"),
            ),
            _move(DiscourseMoveKind.CLOSURE),  # fact=None
        ),
    )
    m = compute_plan_metrics(plan)
    assert m.move_count == 5
    assert m.fact_bearing_count == 4
    assert m.anchor_count == 1
    assert m.support_count == 1
    assert m.relation_count == 1
    assert m.transition_count == 1
    assert m.closure_count == 1


# ---------------------------------------------------------------------------
# Pronominalization opportunities vs. topic shifts
# ---------------------------------------------------------------------------


def test_three_same_subject_moves_yield_two_pronominalization_opportunities() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
            _move(
                DiscourseMoveKind.RELATION,
                _fact("truth", "grounds", "knowledge"),
            ),
        ),
    )
    m = compute_plan_metrics(plan)
    assert m.pronominalization_opportunities == 2
    assert m.topic_shift_count == 0
    assert m.subject_focus_ratio == 1.0


def test_topic_shift_counted_when_subject_changes() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.TRANSITION,
                _fact("knowledge", "belongs_to", "cognition.knowledge"),
            ),
        ),
    )
    m = compute_plan_metrics(plan)
    assert m.topic_shift_count == 1
    assert m.pronominalization_opportunities == 0
    assert m.subject_focus_ratio == 0.0


def test_bridge_move_resets_focus_channel() -> None:
    """A fact-bearing move followed by a bridge (``fact=None``) followed
    by another fact-bearing move with the SAME subject must not count
    as a pronominalization opportunity — the bridge breaks the
    consecutive-pair channel."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(DiscourseMoveKind.TRANSITION),  # bridge, fact=None
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
        ),
    )
    m = compute_plan_metrics(plan)
    # Bridge counts as a shift; no pronominalization opportunity even
    # though both fact-bearing moves share subject "truth".
    assert m.topic_shift_count == 1
    assert m.pronominalization_opportunities == 0


# ---------------------------------------------------------------------------
# Diversity counts
# ---------------------------------------------------------------------------


def test_predicate_diversity_ratio_reflects_monotony() -> None:
    """Three moves with the same predicate → diversity ratio 1/3."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "epistemic.ground"),
            ),
            _move(
                DiscourseMoveKind.RELATION,
                _fact("truth", "belongs_to", "logos.core"),
            ),
        ),
    )
    m = compute_plan_metrics(plan)
    assert m.unique_predicates == 1
    assert m.fact_bearing_count == 3
    assert m.predicate_diversity_ratio is not None
    assert abs(m.predicate_diversity_ratio - (1.0 / 3.0)) < 1e-9


def test_source_diversity_counts_pack_plus_teaching() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.EXPLAIN,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact(
                    "truth", "is_defined_as", "what is true",
                    source=FactSource.PACK,
                ),
            ),
            _move(
                DiscourseMoveKind.RELATION,
                _fact(
                    "truth", "grounds", "knowledge",
                    source=FactSource.TEACHING,
                    source_id="cognition_chains_v1",
                ),
            ),
        ),
    )
    m = compute_plan_metrics(plan)
    assert m.unique_sources == 2


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_metrics_are_deterministic_and_byte_equal_as_dict() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
            _move(
                DiscourseMoveKind.RELATION,
                _fact("truth", "grounds", "knowledge"),
            ),
        ),
    )
    a = compute_plan_metrics(plan)
    b = compute_plan_metrics(plan)
    assert a == b
    assert a.as_dict() == b.as_dict()


# ---------------------------------------------------------------------------
# as_dict surface
# ---------------------------------------------------------------------------


def test_as_dict_includes_every_field_and_derived_ratios() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.EXPLAIN,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
        ),
    )
    d = compute_plan_metrics(plan).as_dict()
    for required_field in (
        "move_count",
        "fact_bearing_count",
        "anchor_count",
        "support_count",
        "relation_count",
        "transition_count",
        "closure_count",
        "unique_predicates",
        "unique_subjects",
        "unique_sources",
        "topic_shift_count",
        "pronominalization_opportunities",
        "predicate_diversity_ratio",
        "subject_focus_ratio",
    ):
        assert required_field in d, f"missing field {required_field!r}"
