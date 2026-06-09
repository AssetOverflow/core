"""Q1-C — the grounded-only question renderer (off-serving).

Pins the wrong=0 grounded-rendering invariant (scoping §2 / session §1.5.7): a
rendered question may name a problem entity only if it appears verbatim in
``grounded_terms``; otherwise the renderer degrades to a generic structural
question or emits ``question_unrenderable``. ``grounded_terms`` is empty
everywhere in production today, so the renderable path is exercised here with the
closed structural-type vocabulary only.
"""

from __future__ import annotations

import ast
from pathlib import Path

from core.epistemic_disclosure.limitation import (
    LimitationAssessment,
    MissingSlot,
)
from core.epistemic_questions import EpistemicQuestion, render_question
from core.epistemic_questions.render import (
    _REASON_MULTI_SLOT,
    _REASON_NO_SLOT,
    _REASON_NOT_ASK,
    _REASON_RENDERABILITY_GAP,
    _names_only_grounded,
)
from core.epistemic_state import EpistemicState


def _ask_assessment(
    slots: tuple[MissingSlot, ...],
    grounded_terms: tuple[str, ...] = (),
) -> LimitationAssessment:
    """An ``ask_question`` assessment carrying the given typed residue."""
    return LimitationAssessment(
        limitation_kind="missing_information",
        resolution_action="ask_question",
        epistemic_state=EpistemicState.UNDETERMINED,
        owner_organ="r2_constraint",
        blocking_reason="missing_total_count",
        missing_slots=slots,
        grounded_terms=grounded_terms,
    )


_TOTAL_COUNT_SLOT = MissingSlot(
    slot_name="total_count",
    expected_unit_or_type="count_int",
    binding_target="collective_unit_total",
)


# --- the wrong=0 invariant: nothing named that is not grounded -----------------


def test_ask_with_slot_and_empty_grounded_renders_generic_without_ungrounded_tokens() -> None:
    """ASK + one slot + empty grounded_terms → a generic question whose every
    token is closed-vocab scaffold (nothing absent from grounded_terms is named).
    """
    q = render_question(_ask_assessment((_TOTAL_COUNT_SLOT,)))

    assert isinstance(q, EpistemicQuestion)
    assert not q.unrenderable
    assert q.slot == _TOTAL_COUNT_SLOT
    assert q.text is not None
    # The whole point: with empty grounded_terms, the text names nothing beyond
    # the closed structural vocabulary.
    assert _names_only_grounded(q.text, ())
    # The closed type phrase for ``count_int`` is conveyed.
    assert "whole-number count" in q.text


def test_rendered_text_never_surfaces_snake_case_identifiers() -> None:
    """Neither ``slot_name`` nor ``binding_target`` (snake_case) reaches prose."""
    q = render_question(_ask_assessment((_TOTAL_COUNT_SLOT,)))

    assert q.text is not None
    assert "total_count" not in q.text
    assert "collective_unit_total" not in q.text
    assert "count_int" not in q.text  # the type is translated, never raw


# --- the fabrication guard: snake_case must never become an entity -------------


def test_fabrication_guard_slot_name_ben_rate_yields_no_named_ben() -> None:
    """A slot whose ``slot_name``/``binding_target`` is ``ben_rate`` must NOT
    produce a question naming "Ben" — slot_name and binding_target are never
    surfaced, prettified, or capitalized.
    """
    ben_slot = MissingSlot(
        slot_name="ben_rate",
        expected_unit_or_type="count_int",  # mapped → renders
        binding_target="ben_rate",
    )
    q = render_question(_ask_assessment((ben_slot,)))

    assert q.text is not None  # renders (type is mapped)
    assert "Ben" not in q.text
    assert "ben" not in _tokens_lower(q.text)
    assert "ben_rate" not in q.text


def test_fabrication_guard_predicate_rejects_ungrounded_entity() -> None:
    """The guard predicate itself flags a fabricated name when not grounded, and
    admits it once it is grounded verbatim.
    """
    assert not _names_only_grounded("What is Ben rate?", ())
    assert _names_only_grounded("What is Ben rate?", ("Ben", "rate"))


# --- non-ASK / no-slot / multi-slot / unmapped-type ---------------------------


def test_non_ask_assessment_is_unrenderable() -> None:
    refuse = LimitationAssessment(
        limitation_kind="hard_boundary",
        resolution_action="refuse_known_boundary",
        epistemic_state=EpistemicState.UNDETERMINED,
        owner_organ="r2_constraint",
        blocking_reason="non_integer_solution",
        missing_slots=(_TOTAL_COUNT_SLOT,),  # present, but action is not ask
    )
    q = render_question(refuse)

    assert q.unrenderable
    assert q.text is None
    assert q.slot is None
    assert q.reason == _REASON_NOT_ASK


def test_ask_with_zero_slots_is_unrenderable() -> None:
    q = render_question(_ask_assessment(()))

    assert q.unrenderable
    assert q.text is None
    assert q.slot is None
    assert q.reason == _REASON_NO_SLOT


def test_multi_slot_does_not_claim_all_missing_information_was_asked() -> None:
    """Two missing slots → refuse with ``multi_slot_not_supported``.

    The template asserts "one more value is still needed" (exactly one). With two
    slots that claim is false, so the renderer must NOT render the first and drop
    the second — it refuses outright, naming no slot. This is the wrong=0-honest
    choice: Q1-C is strictly single-slot, not first-of-many.
    """
    second = MissingSlot(
        slot_name="weighted_total",
        expected_unit_or_type="measured_unit_int",
        binding_target="weighted_total_value",
    )
    q = render_question(_ask_assessment((_TOTAL_COUNT_SLOT, second)))

    assert q.unrenderable
    assert q.text is None
    assert q.slot is None
    assert q.reason == _REASON_MULTI_SLOT


def test_unmapped_structural_type_degrades_to_renderability_gap() -> None:
    """An unknown ``expected_unit_or_type`` refuses rather than dumping raw
    snake_case — the slot is bound but no text is produced.
    """
    exotic = MissingSlot(
        slot_name="mystery",
        expected_unit_or_type="some_unmapped_type",
        binding_target="mystery_target",
    )
    q = render_question(_ask_assessment((exotic,)))

    assert q.unrenderable
    assert q.text is None
    assert q.slot == exotic
    assert q.reason == _REASON_RENDERABILITY_GAP


# --- off-serving structural guard ---------------------------------------------


def test_renderer_is_off_serving() -> None:
    """The renderer must not import the sealed GSM8K serving substrate."""
    src = Path(__file__).resolve().parents[1] / "core" / "epistemic_questions"
    forbidden = ("generate.derivation", "core.reliability_gate")
    for path in src.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(
                    node.module == f or node.module.startswith(f + ".")
                    for f in forbidden
                ), f"{path.name} imports forbidden serving module {node.module}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(
                        alias.name == f or alias.name.startswith(f + ".")
                        for f in forbidden
                    ), f"{path.name} imports forbidden serving module {alias.name}"


def _tokens_lower(text: str) -> set[str]:
    import re

    return set(re.findall(r"[a-z]+", text.lower()))
