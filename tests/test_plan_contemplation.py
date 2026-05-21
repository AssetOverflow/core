"""Phase 3 — plan-level contemplation tests.

Pins ``core.contemplation.plan_preflight.contemplate_plan`` against
the three v1 rules:

  * ``PLANNER_GAP``        — anchor-only depth on non-BRIEF mode
  * ``WEAK_SURFACE``       — predicate repeats >= threshold
  * ``COVERAGE_GAP``       — single ``FactSource`` across multi-move plan

Plus invariants:

  * Empty plans yield no findings.
  * Single-fact BRIEF plans yield no findings (substrate-thin by
    design, not a gap).
  * Determinism: same plan in → same findings (with byte-identical
    ``finding_id`` and ``substrate_hash``).
  * All findings are SPECULATIVE (schema's ``__post_init__`` enforces
    this; we still pin it explicitly so the doctrine is visible).
"""

from __future__ import annotations

from core.contemplation.plan_preflight import contemplate_plan
from core.contemplation.schema import FindingKind
from generate.discourse_planner import (
    DiscourseMove,
    DiscourseMoveKind,
    DiscoursePlan,
    FactSource,
    GroundedFact,
)
from generate.intent import DialogueIntent, IntentTag, ResponseMode
from teaching.epistemic import EpistemicStatus


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
        kind=kind,
        topic=topic,
        given=(),
        new=(fact.obj,) if fact is not None else (),
        relation_to_previous=None,
        fact=fact,
    )


# ---------------------------------------------------------------------------
# Empty / trivial plans yield no findings
# ---------------------------------------------------------------------------


def test_empty_plan_yields_no_findings() -> None:
    plan = DiscoursePlan(intent=_intent(), mode=ResponseMode.BRIEF, moves=())
    assert contemplate_plan(plan) == ()


def test_brief_single_move_yields_no_findings() -> None:
    """BRIEF mode is anchor-only by design; not a gap."""
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
    assert contemplate_plan(plan) == ()


# ---------------------------------------------------------------------------
# PLANNER_GAP — anchor-only depth on non-BRIEF mode
# ---------------------------------------------------------------------------


def test_planner_gap_fires_when_explain_emits_only_anchor() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.EXPLAIN,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
        ),
    )
    findings = contemplate_plan(plan)
    assert len(findings) == 1
    f = findings[0]
    assert f.kind is FindingKind.PLANNER_GAP
    assert f.subject == "truth"
    assert f.predicate == "anchor_only_depth"
    assert f.object == "explain"
    assert "widen substrate" in f.proposed_action
    assert f.epistemic_status is EpistemicStatus.SPECULATIVE


def test_planner_gap_does_not_fire_on_multi_move_plans() -> None:
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
    kinds = {f.kind for f in contemplate_plan(plan)}
    assert FindingKind.PLANNER_GAP not in kinds


# ---------------------------------------------------------------------------
# WEAK_SURFACE — predicate monotony
# ---------------------------------------------------------------------------


def test_weak_surface_fires_on_three_same_predicate_moves() -> None:
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
    findings = contemplate_plan(plan)
    weak = [f for f in findings if f.kind is FindingKind.WEAK_SURFACE]
    assert len(weak) == 1
    assert weak[0].subject == "truth"
    assert weak[0].predicate == "predicate_repeats_in_plan"
    assert weak[0].object == "belongs_to"


def test_weak_surface_does_not_fire_on_two_same_predicate() -> None:
    """Two repetitions read naturally; threshold is 3."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.EXPLAIN,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "epistemic.ground"),
            ),
        ),
    )
    weak = [
        f for f in contemplate_plan(plan)
        if f.kind is FindingKind.WEAK_SURFACE
    ]
    assert weak == []


# ---------------------------------------------------------------------------
# COVERAGE_GAP — single FactSource across multi-move plan
# ---------------------------------------------------------------------------


def test_coverage_gap_fires_on_all_pack_multi_move_plan() -> None:
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
    coverage = [
        f for f in contemplate_plan(plan)
        if f.kind is FindingKind.COVERAGE_GAP
    ]
    assert len(coverage) == 1
    assert coverage[0].object == "pack"
    assert "single_source_plan" == coverage[0].predicate


def test_coverage_gap_does_not_fire_with_mixed_sources() -> None:
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
    coverage = [
        f for f in contemplate_plan(plan)
        if f.kind is FindingKind.COVERAGE_GAP
    ]
    assert coverage == []


# ---------------------------------------------------------------------------
# Determinism: same plan → byte-identical findings
# ---------------------------------------------------------------------------


def test_contemplation_is_deterministic() -> None:
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
    a = contemplate_plan(plan)
    b = contemplate_plan(plan)
    # Byte-equal IDs prove the substrate_hash + identity payload are
    # deterministic; the schema's ``_sha256_16`` derives ``finding_id``
    # from those.
    assert tuple(f.finding_id for f in a) == tuple(f.finding_id for f in b)
    assert tuple(f.substrate_hash for f in a) == tuple(
        f.substrate_hash for f in b
    )


def test_all_findings_remain_speculative() -> None:
    """Pinned to make the ADR-0080 doctrine visible at the test
    layer.  The schema's ``__post_init__`` raises on non-SPECULATIVE
    findings; if a future refactor changes that, this test fails
    first and loudly."""
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
    findings = contemplate_plan(plan)
    assert findings  # would-be-failing rules at the top of this file
    for f in findings:
        assert f.epistemic_status is EpistemicStatus.SPECULATIVE


# ---------------------------------------------------------------------------
# Combined: multiple rules fire on a single plan
# ---------------------------------------------------------------------------


def test_multiple_rules_fire_on_same_plan() -> None:
    """Both WEAK_SURFACE and COVERAGE_GAP fire when a plan is
    predicate-monotonous AND source-homogeneous."""
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
    kinds = {f.kind for f in contemplate_plan(plan)}
    assert FindingKind.WEAK_SURFACE in kinds
    assert FindingKind.COVERAGE_GAP in kinds
