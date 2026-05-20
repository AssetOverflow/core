from __future__ import annotations

from generate.articulation_legality import (
    ArticulationLegality,
    SlotKind,
    validate_finite_predicate_legality,
)
from generate.graph_planner import RhetoricalMove
from generate.templates import render_step


def test_c15_rejects_known_nonverb_finite_predicate_under_negation() -> None:
    verdict = validate_finite_predicate_legality(
        predicate_humanized="thought",
        negated=True,
    )
    assert verdict.legality is ArticulationLegality.ILLEGAL_NON_VERB_FINITE_PREDICATE
    assert verdict.predicate_kind is SlotKind.NON_VERB


def test_c15_fail_open_on_unknown_predicate_kind() -> None:
    verdict = validate_finite_predicate_legality(
        predicate_humanized="quuxified",
        negated=True,
    )
    assert verdict.legality is ArticulationLegality.LEGAL
    assert verdict.predicate_kind is SlotKind.UNKNOWN


def test_render_step_discloses_when_illegal_shape_detected() -> None:
    surface = render_step(
        RhetoricalMove.ASSERT,
        "right",
        "thought",
        "truth",
        negated=True,
    )
    assert surface == "I cannot realize that proposition coherently yet."


def test_render_step_keeps_unknown_predicate_fail_open() -> None:
    surface = render_step(
        RhetoricalMove.ASSERT,
        "signal",
        "quuxified",
        "truth",
        negated=True,
    )
    assert surface == "signal does not quuxified truth"

