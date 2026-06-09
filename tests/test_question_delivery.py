"""Q1-D — off-serving ASK delivery (`QUESTION_NEEDED` tenant).

Pins the delivery rung: a renderable ``ask_question`` assessment routes to
``Terminal.QUESTION_NEEDED`` carrying the Q1-C question *verbatim*; an unrenderable
one takes the D2 standing-disposition fallback (``PROPOSAL_EMITTED`` if the family
still proposes, else ``NO_PROGRESS``) and writes NO artifact. Each guard is written so
it FAILS under the violation it nominally proves (CLAUDE.md schema-obligation
discipline): a contentless ``QUESTION_NEEDED`` is structurally impossible, a delivered
question is never served, and ``answer_binding`` is always the reserved ``None``.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.epistemic_disclosure.limitation import (
    LimitationAssessment,
    MissingSlot,
)
from core.epistemic_questions import (
    AnswerBinding,
    DeliveredQuestion,
    deliver_ask,
    emit_question,
    question_path,
    render_question,
)
from core.epistemic_state import EpistemicState
from generate.contemplation.findings import Terminal


def _ask(
    *,
    blocking_reason: str,
    slots: tuple[MissingSlot, ...],
    kind: str = "missing_information",
) -> LimitationAssessment:
    """An ``ask_question`` assessment with a chosen blocking family + typed residue."""
    return LimitationAssessment(
        limitation_kind=kind,  # type: ignore[arg-type]
        resolution_action="ask_question",
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


# --- the happy path: renderable ask → QUESTION_NEEDED, verbatim ----------------------- #


def test_renderable_ask_delivers_question_needed() -> None:
    outcome = deliver_ask(_ask(blocking_reason="missing_total_count", slots=(_TOTAL_COUNT_SLOT,)))

    assert outcome.terminal == Terminal.QUESTION_NEEDED
    assert outcome.fallback_reason is None
    assert outcome.question is not None
    assert outcome.question.blocking_reason == "missing_total_count"
    assert outcome.question.owner_organ == "r2_constraint"
    assert outcome.question.answer_binding is None  # reserved (Q2)


def test_delivered_question_wraps_the_q1c_render_verbatim() -> None:
    """Q1-D consumes — it does not re-render. The wrapped question must be exactly what
    the Q1-C renderer returns for the same assessment (no second prose surface)."""
    assessment = _ask(blocking_reason="missing_total_count", slots=(_TOTAL_COUNT_SLOT,))
    outcome = deliver_ask(assessment)

    assert outcome.question is not None
    assert outcome.question.question == render_question(assessment)


# --- D2: the unrenderable fallback (never a contentless QUESTION_NEEDED) --------------- #


def test_unrenderable_ask_falls_back_to_proposal_for_proposing_family() -> None:
    """Multi-slot ⇒ Q1-C refuses (multi_slot_not_supported). The family still proposes
    (missing_total_count is a carve-out, proposal_allowed=True), so the standing
    disposition is PROPOSAL_EMITTED — NOT a contentless QUESTION_NEEDED."""
    outcome = deliver_ask(
        _ask(blocking_reason="missing_total_count", slots=(_TOTAL_COUNT_SLOT, _WEIGHTED_SLOT))
    )

    assert outcome.terminal == Terminal.PROPOSAL_EMITTED
    assert outcome.question is None
    assert outcome.fallback_reason == "multi_slot_not_supported"


def test_unrenderable_ask_falls_back_to_no_progress_for_nonproposing_family() -> None:
    """Zero slots ⇒ Q1-C refuses (no_missing_slot). cmb_underdetermined does not propose
    (must_remain_refused), so the standing disposition is NO_PROGRESS."""
    outcome = deliver_ask(_ask(blocking_reason="cmb_underdetermined", slots=()))

    assert outcome.terminal == Terminal.NO_PROGRESS
    assert outcome.question is None
    assert outcome.fallback_reason == "no_missing_slot"


def test_unmapped_type_unrenderable_also_falls_back() -> None:
    """An unmapped structural type ⇒ Q1-C renderability_gap ⇒ fallback, never delivered."""
    exotic = MissingSlot(
        slot_name="mystery", expected_unit_or_type="some_unmapped_type", binding_target="x"
    )
    outcome = deliver_ask(_ask(blocking_reason="missing_total_count", slots=(exotic,)))

    assert outcome.terminal == Terminal.PROPOSAL_EMITTED  # proposing family
    assert outcome.question is None
    assert outcome.fallback_reason == "renderability_gap"


# --- structural guards: illegal DeliveredQuestion states are unrepresentable ----------- #


def test_delivered_question_cannot_wrap_unrenderable() -> None:
    """The D2 guard, structurally: a DeliveredQuestion can NEVER wrap an unrenderable
    question — so a QUESTION_NEEDED terminal always carries real rendered text."""
    unrenderable = render_question(_ask(blocking_reason="cmb_underdetermined", slots=()))
    assert unrenderable.unrenderable  # precondition

    with pytest.raises(ValueError, match="unrenderable"):
        DeliveredQuestion(
            question=unrenderable, owner_organ="r2_constraint", blocking_reason="x"
        )


def test_delivered_question_is_never_served() -> None:
    rendered = render_question(_ask(blocking_reason="missing_total_count", slots=(_TOTAL_COUNT_SLOT,)))
    with pytest.raises(ValueError, match="never served"):
        DeliveredQuestion(
            question=rendered, owner_organ="o", blocking_reason="missing_total_count", served=True
        )


def test_answer_binding_is_reserved_and_rejected_in_q1d() -> None:
    rendered = render_question(_ask(blocking_reason="missing_total_count", slots=(_TOTAL_COUNT_SLOT,)))
    binding = AnswerBinding(
        target_organ="o", target_slot="total_count", binding_target="collective_unit_total", parser="int"
    )
    with pytest.raises(ValueError, match="reserved for Q2"):
        DeliveredQuestion(
            question=rendered,
            owner_organ="o",
            blocking_reason="missing_total_count",
            answer_binding=binding,
        )


def test_deliver_ask_rejects_non_ask_assessment() -> None:
    refuse = LimitationAssessment(
        limitation_kind="hard_boundary",
        resolution_action="refuse_known_boundary",
        epistemic_state=EpistemicState.UNDETERMINED,
        owner_organ="r2_constraint",
        blocking_reason="non_integer_solution",
    )
    with pytest.raises(ValueError, match="only valid for ask_question"):
        deliver_ask(refuse)


# --- the sink: proposal-only, idempotent, no artifact on fallback ---------------------- #


def test_emit_question_writes_proposal_only_artifact_idempotently(tmp_path: Path) -> None:
    assessment = _ask(blocking_reason="missing_total_count", slots=(_TOTAL_COUNT_SLOT,))
    path1 = emit_question(assessment, root=tmp_path)

    assert path1 is not None and path1.exists()
    doc = json.loads(path1.read_text(encoding="utf-8"))
    assert doc["status"] == "question_only"
    assert doc["served"] is False
    assert doc["requires_review"] is True
    assert doc["answer_binding"] is None
    assert doc["blocking_reason"] == "missing_total_count"
    assert doc["question"]["text"]  # real rendered text, not empty

    first_bytes = path1.read_bytes()
    path2 = emit_question(assessment, root=tmp_path)  # idempotent
    assert path2 == path1
    assert path2.read_bytes() == first_bytes


def test_emit_question_writes_nothing_on_unrenderable_fallback(tmp_path: Path) -> None:
    """No contentless artifact: an unrenderable ask writes no file and returns None."""
    path = emit_question(_ask(blocking_reason="cmb_underdetermined", slots=()), root=tmp_path)

    assert path is None
    assert list(tmp_path.glob("*.json")) == []


def test_question_path_is_content_addressed(tmp_path: Path) -> None:
    assessment = _ask(blocking_reason="missing_total_count", slots=(_TOTAL_COUNT_SLOT,))
    outcome = deliver_ask(assessment)
    assert outcome.question is not None
    p = question_path(outcome.question, tmp_path)
    assert p.parent == tmp_path
    assert p.name.endswith(".json")
    assert len(p.stem) == 64  # sha256 hex


# --- off-serving structural guard ----------------------------------------------------- #


def test_delivery_is_off_serving() -> None:
    """The delivery module must not import the sealed GSM8K serving substrate."""
    path = Path(__file__).resolve().parents[1] / "core" / "epistemic_questions" / "delivery.py"
    forbidden = ("generate.derivation", "core.reliability_gate")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not any(
                node.module == f or node.module.startswith(f + ".") for f in forbidden
            ), f"delivery.py imports forbidden serving module {node.module}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == f or alias.name.startswith(f + ".") for f in forbidden
                ), f"delivery.py imports forbidden serving module {alias.name}"


def test_question_needed_is_a_distinct_terminal() -> None:
    """QUESTION_NEEDED is a real, distinct terminal — sibling of PROPOSAL_EMITTED."""
    assert Terminal.QUESTION_NEEDED.value == "QUESTION_NEEDED"
    assert Terminal.QUESTION_NEEDED is not Terminal.PROPOSAL_EMITTED
