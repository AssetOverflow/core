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


def test_renderable_ask_path_returns_question_needed_under_exercise_ask(monkeypatch, tmp_path) -> None:
    from core.comprehension_attempt import ComprehensionAttempt, RouteResult
    import generate.contemplation.pass_manager as pm
    from generate.binding_graph.model import SourceSpanLink

    span = SourceSpanLink(source_id="src", start=0, end=8, text="chickens")
    attempt = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="missing_total_count",
        evidence=(span,),
    )

    monkeypatch.setattr(pm, "route_setup", lambda text, case_id=None: RouteResult((attempt,), None, "all_refused"))

    question_root = tmp_path / "teaching" / "questions"
    proposal_root = tmp_path / "teaching" / "proposals"

    repo_questions_dir = Path(__file__).resolve().parents[1] / "teaching" / "questions"
    before_files = set(repo_questions_dir.glob("**/*")) if repo_questions_dir.exists() else set()

    # 1. Assert that without exercise_ask, it falls back to PROPOSAL_EMITTED (due to carve-out)
    res_normal = contemplate(
        "chickens",
        proposal_root=proposal_root,
        question_root=question_root,
    )
    assert res_normal.terminal == Terminal.PROPOSAL_EMITTED

    # 2. Assert that with exercise_ask=True, it returns QUESTION_NEEDED
    calls = []
    orig = pm._delivery_outcome_for_limitation
    def wrapped(assessment):
        calls.append(assessment)
        return orig(assessment)
    monkeypatch.setattr(pm, "_delivery_outcome_for_limitation", wrapped)

    res_ask = contemplate(
        "chickens",
        proposal_root=proposal_root,
        question_root=question_root,
        exercise_ask=True,
    )
    assert res_ask.terminal == Terminal.QUESTION_NEEDED
    assert len(calls) == 1  # Verify it is called exactly once! No double delivery / double render!

    # Verify the question artifact path
    assert res_ask.proposal_path is not None
    artifact_path = Path(res_ask.proposal_path)
    assert artifact_path.exists()

    # Assert question artifact is under question_root
    assert question_root in artifact_path.parents
    # Assert question artifact is not under proposal_root
    assert proposal_root not in artifact_path.parents

    # Assert no repo-local teaching/questions artifact is created during tests
    after_files = set(repo_questions_dir.glob("**/*")) if repo_questions_dir.exists() else set()
    assert before_files == after_files


def test_unrenderable_ask_falls_back_in_pass_manager(monkeypatch, tmp_path) -> None:
    from core.comprehension_attempt import ComprehensionAttempt, RouteResult
    import generate.contemplation.pass_manager as pm
    from core.epistemic_questions.delivery import DeliveryOutcome

    attempt = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="missing_total_count",
    )

    monkeypatch.setattr(pm, "route_setup", lambda text, case_id=None: RouteResult((attempt,), None, "all_refused"))
    monkeypatch.setattr(
        pm,
        "_delivery_outcome_for_limitation",
        lambda assessment: DeliveryOutcome(Terminal.PROPOSAL_EMITTED, None, "multi_slot_not_supported")
    )

    question_root = tmp_path / "teaching" / "questions"
    proposal_root = tmp_path / "teaching" / "proposals"

    res = contemplate(
        "chickens",
        proposal_root=proposal_root,
        question_root=question_root,
        exercise_ask=True,
    )
    assert res.terminal == Terminal.PROPOSAL_EMITTED
    assert res.terminal is not Terminal.QUESTION_NEEDED
    assert res.proposal_path is not None
    assert Path(res.proposal_path).exists()


def test_family_none_does_not_crash_ask_branch(monkeypatch, tmp_path) -> None:
    from core.comprehension_attempt import ComprehensionAttempt, RouteResult
    import generate.contemplation.pass_manager as pm
    from core.epistemic_disclosure.limitation import LimitationAssessment
    import core.epistemic_disclosure.limitation as lim_mod

    fake_assessment = LimitationAssessment(
        limitation_kind="missing_information",
        resolution_action="ask_question",
        epistemic_state=EpistemicState.UNDETERMINED,
        owner_organ="r2_constraint",
        blocking_reason="nonexistent_family_name",
    )

    attempt = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="nonexistent_family_name",
    )

    monkeypatch.setattr(pm, "route_setup", lambda text, case_id=None: RouteResult((attempt,), None, "all_refused"))
    monkeypatch.setattr(lim_mod, "assess_from_attempt", lambda att: fake_assessment)

    question_root = tmp_path / "teaching" / "questions"
    proposal_root = tmp_path / "teaching" / "proposals"

    res = contemplate(
        "chickens",
        proposal_root=proposal_root,
        question_root=question_root,
        exercise_ask=True,
    )
    assert res.terminal == Terminal.NO_PROGRESS


def test_boundary_wins_over_ask_in_pass_manager(monkeypatch, tmp_path) -> None:
    from core.comprehension_attempt import ComprehensionAttempt, RouteResult
    import generate.contemplation.pass_manager as pm
    from generate.binding_graph.model import SourceSpanLink

    span = SourceSpanLink(source_id="src", start=0, end=8, text="chickens")
    attempt_boundary = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="too_many_categories",  # maps to unsupported_system_size (must_remain_refused = True)
        evidence=(span,),
    )
    attempt_ask = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="missing_total_count",  # ask carve-out
        evidence=(span,),
    )

    monkeypatch.setattr(
        pm,
        "route_setup",
        lambda text, case_id=None: RouteResult((attempt_boundary, attempt_ask), None, "all_refused"),
    )

    question_root = tmp_path / "teaching" / "questions"
    proposal_root = tmp_path / "teaching" / "proposals"

    res = contemplate(
        "chickens",
        proposal_root=proposal_root,
        question_root=question_root,
        exercise_ask=True,
    )
    # Assert terminal remains REFUSED_UNSUPPORTED_FAMILY or REFUSED_KNOWN_BOUNDARY, not QUESTION_NEEDED
    assert res.terminal == Terminal.REFUSED_UNSUPPORTED_FAMILY
    # Ensure no question is written under question_root
    assert not question_root.exists() or len(list(question_root.glob("**/*"))) == 0
