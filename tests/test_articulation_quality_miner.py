"""Phase 5 — articulation-quality miner unit tests.

Tests ``core.contemplation.miners.articulation_quality.
mine_articulation_observations`` against synthetic observations:

  * Empty stream → no findings
  * Single observation → no findings (threshold not met)
  * recurring_predicate_monotony — fires at >= _MIN_RECURRENCE
  * recurring_planner_gap — fires at >= _MIN_RECURRENCE
  * low_average_predicate_diversity — fires when mean < threshold
  * Determinism: byte-equal finding IDs across two runs
  * All emitted findings stay SPECULATIVE
"""

from __future__ import annotations

import pytest

from chat.articulation_telemetry import (
    ArticulationObservation,
    format_articulation_observation_jsonl,
    load_articulation_observations,
)
from core.contemplation.miners.articulation_quality import (
    mine_articulation_observations,
)
from core.contemplation.schema import FindingKind
from teaching.epistemic import EpistemicStatus


def _obs(
    *,
    turn_id: int = 0,
    anchor: str = "truth",
    prompt_h: str = "p0000000000000000",
    plan_h: str = "s0000000000000000",
    metrics: dict | None = None,
    findings: tuple[dict, ...] = (),
) -> ArticulationObservation:
    return ArticulationObservation(
        turn_id=turn_id,
        anchor_subject=anchor,
        prompt_hash=prompt_h,
        plan_substrate_hash=plan_h,
        metrics=metrics or {
            "move_count": 4,
            "fact_bearing_count": 4,
            "anchor_count": 1,
            "support_count": 1,
            "relation_count": 1,
            "transition_count": 1,
            "closure_count": 0,
            "unique_predicates": 4,
            "unique_subjects": 1,
            "unique_sources": 2,
            "topic_shift_count": 0,
            "pronominalization_opportunities": 3,
            "predicate_diversity_ratio": 1.0,
            "subject_focus_ratio": 1.0,
        },
        findings=findings,
    )


def _weak_surface_finding(
    subject: str, predicate: str,
) -> dict[str, str | None]:
    return {
        "kind": FindingKind.WEAK_SURFACE.value,
        "subject": subject,
        "predicate": "predicate_repeats_in_plan",
        "object": predicate,
    }


def _planner_gap_finding(
    subject: str, mode: str = "explain",
) -> dict[str, str | None]:
    return {
        "kind": FindingKind.PLANNER_GAP.value,
        "subject": subject,
        "predicate": "anchor_only_depth",
        "object": mode,
    }


# ---------------------------------------------------------------------------
# Trivial cases
# ---------------------------------------------------------------------------


def test_empty_stream_yields_no_findings() -> None:
    assert mine_articulation_observations(observations=()) == ()


def test_below_threshold_recurrence_yields_no_findings() -> None:
    """Two ``WEAK_SURFACE`` observations is below the default
    ``_MIN_RECURRENCE = 3`` — nothing should fire."""
    observations = (
        _obs(turn_id=0, findings=(_weak_surface_finding("truth", "belongs_to"),)),
        _obs(turn_id=1, findings=(_weak_surface_finding("truth", "belongs_to"),)),
    )
    findings = mine_articulation_observations(observations=observations)
    assert findings == ()


# ---------------------------------------------------------------------------
# Rule: recurring_predicate_monotony
# ---------------------------------------------------------------------------


def test_recurring_predicate_monotony_fires_at_threshold() -> None:
    observations = tuple(
        _obs(turn_id=i, findings=(_weak_surface_finding("truth", "belongs_to"),))
        for i in range(3)
    )
    findings = mine_articulation_observations(observations=observations)
    matching = [
        f for f in findings
        if f.predicate == "recurring_predicate_monotony"
    ]
    assert len(matching) == 1
    f = matching[0]
    assert f.kind is FindingKind.PACK_MUTATION_CANDIDATE
    assert f.subject == "truth"
    assert f.object == "belongs_to"
    assert "diversify substrate" in f.proposed_action
    assert f.epistemic_status is EpistemicStatus.SPECULATIVE


def test_recurring_predicate_monotony_separates_by_subject() -> None:
    """Two different subjects each above threshold → two separate
    findings, not one merged finding."""
    observations = (
        *(
            _obs(turn_id=i, anchor="truth",
                 findings=(_weak_surface_finding("truth", "belongs_to"),))
            for i in range(3)
        ),
        *(
            _obs(turn_id=i + 100, anchor="memory",
                 findings=(_weak_surface_finding("memory", "requires"),))
            for i in range(3)
        ),
    )
    findings = mine_articulation_observations(observations=observations)
    matching = [
        f for f in findings
        if f.predicate == "recurring_predicate_monotony"
    ]
    assert len(matching) == 2
    by_subject = {f.subject: f for f in matching}
    assert "truth" in by_subject and by_subject["truth"].object == "belongs_to"
    assert "memory" in by_subject and by_subject["memory"].object == "requires"


# ---------------------------------------------------------------------------
# Rule: recurring_planner_gap
# ---------------------------------------------------------------------------


def test_recurring_planner_gap_fires_at_threshold() -> None:
    observations = tuple(
        _obs(turn_id=i, anchor="rare_lemma",
             findings=(_planner_gap_finding("rare_lemma", "explain"),))
        for i in range(3)
    )
    findings = mine_articulation_observations(observations=observations)
    matching = [
        f for f in findings
        if f.predicate == "recurring_planner_gap"
    ]
    assert len(matching) == 1
    assert matching[0].subject == "rare_lemma"
    assert "widen substrate" in matching[0].proposed_action


def test_recurring_planner_gap_collects_distinct_modes() -> None:
    """When the same subject hits PLANNER_GAP across different modes,
    the finding's ``object`` lists all of them, sorted."""
    observations = (
        _obs(turn_id=0, anchor="rare",
             findings=(_planner_gap_finding("rare", "explain"),)),
        _obs(turn_id=1, anchor="rare",
             findings=(_planner_gap_finding("rare", "paragraph"),)),
        _obs(turn_id=2, anchor="rare",
             findings=(_planner_gap_finding("rare", "example"),)),
    )
    findings = mine_articulation_observations(observations=observations)
    matching = [
        f for f in findings if f.predicate == "recurring_planner_gap"
    ]
    assert len(matching) == 1
    assert matching[0].object == "example,explain,paragraph"


# ---------------------------------------------------------------------------
# Rule: low_average_predicate_diversity
# ---------------------------------------------------------------------------


def test_low_average_predicate_diversity_fires_below_threshold() -> None:
    low_metrics = dict(
        move_count=6, fact_bearing_count=6,
        anchor_count=1, support_count=2, relation_count=2,
        transition_count=1, closure_count=0,
        unique_predicates=2, unique_subjects=1, unique_sources=1,
        topic_shift_count=0, pronominalization_opportunities=5,
        predicate_diversity_ratio=2.0 / 6.0,  # 0.333 — well below 0.5
        subject_focus_ratio=1.0,
    )
    observations = tuple(
        _obs(turn_id=i, anchor="truth", metrics=low_metrics)
        for i in range(3)
    )
    findings = mine_articulation_observations(observations=observations)
    matching = [
        f for f in findings
        if f.predicate == "low_average_predicate_diversity"
    ]
    assert len(matching) == 1
    f = matching[0]
    assert f.kind is FindingKind.PACK_MUTATION_CANDIDATE
    assert f.subject == "truth"
    # object is the average ratio as a string, formatted to 3 decimals
    assert f.object is not None
    assert float(f.object) == pytest.approx(2.0 / 6.0, abs=1e-3)


def test_low_average_predicate_diversity_skips_when_above_threshold() -> None:
    high_metrics = dict(
        move_count=4, fact_bearing_count=4,
        anchor_count=1, support_count=1, relation_count=2,
        transition_count=0, closure_count=0,
        unique_predicates=4, unique_subjects=1, unique_sources=2,
        topic_shift_count=0, pronominalization_opportunities=3,
        predicate_diversity_ratio=1.0,
        subject_focus_ratio=1.0,
    )
    observations = tuple(
        _obs(turn_id=i, anchor="truth", metrics=high_metrics)
        for i in range(5)
    )
    findings = mine_articulation_observations(observations=observations)
    assert not [
        f for f in findings
        if f.predicate == "low_average_predicate_diversity"
    ]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_miner_is_deterministic_across_runs() -> None:
    observations = tuple(
        _obs(turn_id=i, findings=(_weak_surface_finding("truth", "belongs_to"),))
        for i in range(3)
    )
    a = mine_articulation_observations(observations=observations)
    b = mine_articulation_observations(observations=observations)
    assert tuple(f.finding_id for f in a) == tuple(f.finding_id for f in b)
    assert tuple(f.substrate_hash for f in a) == tuple(f.substrate_hash for f in b)


# ---------------------------------------------------------------------------
# SPECULATIVE doctrine pin
# ---------------------------------------------------------------------------


def test_all_findings_remain_speculative() -> None:
    observations = (
        *(
            _obs(turn_id=i,
                 findings=(_weak_surface_finding("truth", "belongs_to"),))
            for i in range(3)
        ),
        *(
            _obs(turn_id=i + 100, anchor="rare",
                 findings=(_planner_gap_finding("rare", "explain"),))
            for i in range(3)
        ),
    )
    findings = mine_articulation_observations(observations=observations)
    assert findings  # at least the two recurring rules fired
    for f in findings:
        assert f.epistemic_status is EpistemicStatus.SPECULATIVE


# ---------------------------------------------------------------------------
# Round-trip via JSONL
# ---------------------------------------------------------------------------


def test_jsonl_round_trip_preserves_observation_identity() -> None:
    original = _obs(
        turn_id=42,
        anchor="truth",
        findings=(_weak_surface_finding("truth", "belongs_to"),),
    )
    line = format_articulation_observation_jsonl(original)
    [recovered] = load_articulation_observations([line])
    assert recovered.turn_id == original.turn_id
    assert recovered.anchor_subject == original.anchor_subject
    assert recovered.metrics == original.metrics
    assert recovered.findings == original.findings
