"""Focused tests for off-serving ASK delivery integration in the contemplation pass manager (N6).

Ensures that the pass manager seam delegates to deliver_ask, correctly handles fallback dispositions,
avoids direct rendering imports/text construction, and preserves the Q1-B carve-out.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.epistemic_disclosure.limitation import (
    Q1B_ASK_CARVE_OUT,
    LimitationAssessment,
    MissingSlot,
)
from core.epistemic_state import EpistemicState
from generate.contemplation import Terminal, contemplate
from generate.contemplation.pass_manager import (
    _delivery_outcome_for_limitation,
)
from core.comprehension_attempt.failure_family import family_by_name


def _make_assessment(
    *,
    blocking_reason: str,
    slots: tuple[MissingSlot, ...],
    resolution_action: str = "ask_question",
) -> LimitationAssessment:
    return LimitationAssessment(
        limitation_kind="missing_information",
        resolution_action=resolution_action,  # type: ignore[arg-type]
        epistemic_state=EpistemicState.UNDETERMINED,
        owner_organ="r2_constraint",
        blocking_reason=blocking_reason,
        missing_slots=slots,
    )


_TOTAL_COUNT_SLOT = MissingSlot(
    slot_name="total_count",
    expected_unit_or_type="count_int",
    binding_target="collective_unit_total",
)
_WEIGHTED_SLOT = MissingSlot(
    slot_name="weighted_total",
    expected_unit_or_type="measured_unit_int",
    binding_target="weighted_total_value",
)


def test_pass_manager_uses_deliver_ask_for_renderable_ask() -> None:
    assessment = _make_assessment(
        blocking_reason="missing_total_count", slots=(_TOTAL_COUNT_SLOT,)
    )
    outcome = _delivery_outcome_for_limitation(assessment)
    assert outcome.terminal == Terminal.QUESTION_NEEDED
    assert outcome.question is not None
    assert outcome.fallback_reason is None


def test_pass_manager_unrenderable_ask_falls_back_without_question_needed() -> None:
    # Multi-slot => unrenderable, falls back to standing disposition (PROPOSAL_EMITTED since missing_total_count is carve-out)
    assessment = _make_assessment(
        blocking_reason="missing_total_count",
        slots=(_TOTAL_COUNT_SLOT, _WEIGHTED_SLOT),
    )
    outcome = _delivery_outcome_for_limitation(assessment)
    assert outcome.terminal == Terminal.PROPOSAL_EMITTED
    assert outcome.terminal is not Terminal.QUESTION_NEEDED
    assert outcome.question is None
    assert outcome.fallback_reason == "multi_slot_not_supported"


def test_pass_manager_does_not_import_or_call_render_question_directly() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "generate"
        / "contemplation"
        / "pass_manager.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        # Ensure render_question is not imported
        if isinstance(node, ast.ImportFrom):
            assert node.module != "core.epistemic_questions.render"
            if node.names:
                for alias in node.names:
                    assert alias.name != "render_question"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "core.epistemic_questions.render"

        # Ensure render_question is not called directly
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "render_question"


def test_pass_manager_does_not_construct_question_text() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "generate"
        / "contemplation"
        / "pass_manager.py"
    )
    content = path.read_text(encoding="utf-8")
    forbidden_templates = ["What ", "Which ", "How many", "Please provide"]
    for template in forbidden_templates:
        assert template not in content, (
            f"pass_manager.py must not construct prose templates like {template!r}"
        )


def test_q1b_carveout_preserved_during_pass_manager_ask_integration() -> None:
    assert "missing_total_count" in Q1B_ASK_CARVE_OUT
    assert "missing_weighted_total" in Q1B_ASK_CARVE_OUT

    for name in Q1B_ASK_CARVE_OUT:
        family = family_by_name(name)
        assert family is not None
        assert family.proposal_allowed is True
