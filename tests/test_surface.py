"""tests/test_surface.py — Unit tests for generate.surface.SentenceAssembler.

Covers:
  - All four DialogueRole templates in English (assert, elaborate, question, refute)
  - Empty-slot guard (both subject and predicate empty)
  - Elaboration token weaving (elaborate role with walk tokens)
  - Stop-surface filtering (function words not woven into elaboration)
  - Deduplication of elaboration tokens
  - Hebrew VSO word order
  - Ancient Greek SOV word order
  - SentencePlan dataclass fields populated correctly
  - Module-level assemble() convenience function
  - Determinism: identical inputs produce identical outputs
"""
from __future__ import annotations

import pytest

from generate.articulation import ArticulationPlan
from generate.surface import SentenceAssembler, SentencePlan, assemble


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plan(
    subject: str = "truth",
    predicate: str = "speaks",
    object_: str | None = "light",
    lang: str = "en",
    frame_id: str = "test-frame",
) -> ArticulationPlan:
    surface = " ".join(p for p in [subject, predicate, object_] if p)
    return ArticulationPlan(
        subject=subject,
        predicate=predicate,
        object=object_,
        surface=surface,
        output_language=lang,
        frame_id=frame_id,
    )


ASSEMBLER = SentenceAssembler()


# ---------------------------------------------------------------------------
# English SVO — four roles
# ---------------------------------------------------------------------------

class TestEnglishRoles:
    def test_assert_with_object(self):
        plan = _plan("truth", "speaks", "light")
        sp = ASSEMBLER.assemble(plan, [], role="assert")
        assert sp.surface == "Truth speaks light."
        assert sp.dialogue_role == "assert"
        assert sp.elaboration is None

    def test_assert_no_object(self):
        plan = _plan("truth", "speaks", None)
        sp = ASSEMBLER.assemble(plan, [], role="assert")
        assert sp.surface == "Truth speaks."

    def test_elaborate_no_walk_tokens(self):
        plan = _plan("truth", "speaks", "light")
        sp = ASSEMBLER.assemble(plan, [], role="elaborate")
        # No walk tokens — falls back to plain assert-style with period.
        assert sp.surface == "Truth speaks light."
        assert sp.elaboration is None

    def test_elaborate_with_walk_tokens(self):
        plan = _plan("truth", "speaks", "light")
        tokens = ["covenant", "wisdom", "glory", "word"]
        sp = ASSEMBLER.assemble(plan, tokens, role="elaborate")
        assert " — " in sp.surface
        assert sp.surface.endswith(".")
        assert sp.elaboration is not None
        assert "covenant" in sp.elaboration

    def test_question_with_object(self):
        plan = _plan("truth", "speak", "light")
        sp = ASSEMBLER.assemble(plan, [], role="question")
        assert sp.surface == "Does truth speak light?"
        assert sp.surface.endswith("?")

    def test_question_no_object(self):
        plan = _plan("truth", "speak", None)
        sp = ASSEMBLER.assemble(plan, [], role="question")
        assert sp.surface == "Does truth speak?"

    def test_refute_with_object(self):
        plan = _plan("truth", "deny", "light")
        sp = ASSEMBLER.assemble(plan, [], role="refute")
        assert sp.surface == "Truth does not deny light."

    def test_refute_no_object(self):
        plan = _plan("truth", "deny", None)
        sp = ASSEMBLER.assemble(plan, [], role="refute")
        assert sp.surface == "Truth does not deny."


# ---------------------------------------------------------------------------
# Empty-slot guard
# ---------------------------------------------------------------------------

class TestEmptySlotGuard:
    def test_both_empty_falls_back_to_plan_surface(self):
        plan = _plan("", "", None)
        # Override surface on the plan to a non-trivial fallback.
        plan_with_surface = ArticulationPlan(
            subject="",
            predicate="",
            object=None,
            surface="covenant light",
            output_language="en",
            frame_id="test",
        )
        sp = ASSEMBLER.assemble(plan_with_surface, [], role="assert")
        assert sp.surface == "covenant light"

    def test_both_empty_falls_back_to_tokens(self):
        plan = ArticulationPlan(
            subject="",
            predicate="",
            object=None,
            surface="",
            output_language="en",
            frame_id="test",
        )
        sp = ASSEMBLER.assemble(plan, ["covenant", "light"], role="assert")
        assert "covenant" in sp.surface or "light" in sp.surface

    def test_subject_only_empty_still_assembles(self):
        """Only the both-empty case triggers the guard."""
        plan = _plan("", "speaks", "light")
        sp = ASSEMBLER.assemble(plan, [], role="assert")
        # Subject is empty string — capitalised empty + predicate + object.
        assert sp.surface.endswith(".")
        assert "speaks" in sp.surface


# ---------------------------------------------------------------------------
# Elaboration filtering
# ---------------------------------------------------------------------------

class TestElaborationFiltering:
    def test_stop_surfaces_excluded(self):
        plan = _plan("truth", "speaks", "light")
        # All tokens are stop surfaces — elaboration should be None.
        tokens = ["the", "a", "is", "are", "and", "or", "to"]
        sp = ASSEMBLER.assemble(plan, tokens, role="elaborate")
        assert sp.elaboration is None

    def test_slot_words_excluded_from_elaboration(self):
        plan = _plan("truth", "speaks", "light")
        # Slot words themselves should not appear in elaboration.
        tokens = ["truth", "speaks", "light", "covenant"]
        sp = ASSEMBLER.assemble(plan, tokens, role="elaborate")
        if sp.elaboration:
            assert "truth" not in sp.elaboration
            assert "speaks" not in sp.elaboration
            assert "light" not in sp.elaboration
            assert "covenant" in sp.elaboration

    def test_deduplication_in_elaboration(self):
        plan = _plan("truth", "speaks", "light")
        # Repeated token should appear only once.
        tokens = ["covenant", "covenant", "covenant", "wisdom"]
        sp = ASSEMBLER.assemble(plan, tokens, role="elaborate")
        if sp.elaboration:
            elab_list = sp.elaboration.split(", ")
            assert len(set(elab_list)) == len(elab_list)

    def test_max_elaboration_tokens_capped(self):
        plan = _plan("truth", "speaks", "light")
        # Feed more unique tokens than _MAX_ELAB_TOKENS (4).
        tokens = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]
        sp = ASSEMBLER.assemble(plan, tokens, role="elaborate")
        if sp.elaboration:
            elab_list = sp.elaboration.split(", ")
            assert len(elab_list) <= 4


# ---------------------------------------------------------------------------
# Language routing
# ---------------------------------------------------------------------------

class TestLanguageRouting:
    def test_hebrew_vso_assert(self):
        plan = _plan("emet", "medaber", "or", lang="he")
        sp = ASSEMBLER.assemble(plan, [], role="assert")
        # VSO: predicate first, then subject, then object.
        parts = sp.surface.rstrip(".").split()
        assert parts[0] == "medaber"
        assert parts[1] == "emet"
        assert parts[2] == "or"

    def test_hebrew_question_prefix(self):
        plan = _plan("emet", "medaber", "or", lang="he")
        sp = ASSEMBLER.assemble(plan, [], role="question")
        # Hebrew question: האם prefix.
        assert sp.surface.startswith("\u05d4\u05d0\u05dd")
        assert sp.surface.endswith("?")

    def test_greek_sov_assert(self):
        plan = _plan("logos", "esti", "phos", lang="grc")
        sp = ASSEMBLER.assemble(plan, [], role="assert")
        # SOV: subject, object, verb.
        parts = sp.surface.rstrip(".").split()
        assert parts[0] == "Logos"
        assert parts[1] == "phos"
        assert parts[2] == "esti"

    def test_greek_question_semicolon(self):
        plan = _plan("logos", "esti", "phos", lang="grc")
        sp = ASSEMBLER.assemble(plan, [], role="question")
        assert sp.surface.endswith(";")

    def test_unknown_language_falls_back_to_english(self):
        plan = _plan("truth", "speaks", "light", lang="fr")
        sp = ASSEMBLER.assemble(plan, [], role="assert")
        assert sp.surface == "Truth speaks light."


# ---------------------------------------------------------------------------
# SentencePlan field invariants
# ---------------------------------------------------------------------------

class TestSentencePlanFields:
    def test_all_fields_populated(self):
        plan = _plan("truth", "speaks", "light")
        sp = ASSEMBLER.assemble(plan, ["covenant"], role="elaborate")
        assert isinstance(sp, SentencePlan)
        assert sp.subject == "truth"
        assert sp.predicate_phrase == "speaks"
        assert sp.object_phrase == "light"
        assert sp.output_language == "en"
        assert sp.dialogue_role == "elaborate"
        assert sp.surface  # non-empty

    def test_surface_is_string(self):
        plan = _plan()
        sp = ASSEMBLER.assemble(plan, [], role="assert")
        assert isinstance(sp.surface, str)


# ---------------------------------------------------------------------------
# Module-level assemble() wrapper
# ---------------------------------------------------------------------------

class TestAssembleWrapper:
    def test_returns_string(self):
        plan = _plan()
        result = assemble(plan, [], role="assert")
        assert isinstance(result, str)
        assert result == "Truth speaks light."


# ---------------------------------------------------------------------------
# Determinism guarantee
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_identical_inputs_identical_outputs(self):
        plan = _plan("truth", "speaks", "light")
        tokens = ["covenant", "wisdom", "glory"]
        results = [
            ASSEMBLER.assemble(plan, tokens, role="elaborate").surface
            for _ in range(10)
        ]
        assert len(set(results)) == 1, "Non-deterministic output detected"
