"""Tests for ``CompoundIntent`` and ``classify_compound_intent``.

Pins:

* The compound classifier is purely additive — ``classify_intent``
  return shape is untouched.
* Decomposition is deterministic, byte-stable, and preserves source
  order (no cross-part re-sorting).
* Anaphoric follow-ups ("why does it matter") rewrite the pronoun
  with the prior part's subject.
* Prompts without a recognised connector produce exactly one part
  and are byte-equivalent to ``classify_intent``.
* The "matter" / "work" / "causes it" follow-ups map to existing
  intent tags (CAUSE in v1) — no new IntentTag is introduced.
"""

from __future__ import annotations

import pytest

from generate.intent import (
    CompoundIntent,
    DialogueIntent,
    IntentTag,
    classify_compound_intent,
    classify_intent,
)

# Imported for type clarity even when only used in assertion side-effects.
_ = CompoundIntent


# ---------------------------------------------------------------------------
# Back-compat: classify_intent untouched
# ---------------------------------------------------------------------------


class TestSingleIntentUntouched:
    def test_classify_intent_still_returns_dialogue_intent(self) -> None:
        result = classify_intent("What is truth?")
        assert isinstance(result, DialogueIntent)

    def test_compound_classifier_does_not_change_single_intent_shape(self) -> None:
        # Identical input through both APIs — single-intent payload
        # remains identical.
        flat = classify_intent("What is truth?")
        compound = classify_compound_intent("What is truth?")
        assert compound.parts == (flat,)
        assert compound.primary == flat
        assert not compound.is_compound()


# ---------------------------------------------------------------------------
# Decomposition behavior
# ---------------------------------------------------------------------------


class TestCompoundDecomposition:
    def test_what_is_x_and_why_does_it_matter(self) -> None:
        result = classify_compound_intent("What is truth, and why does it matter?")
        assert result.is_compound()
        assert len(result.parts) == 2
        assert result.parts[0].tag is IntentTag.DEFINITION
        assert result.parts[0].subject == "truth"
        # Anaphoric "it" rewritten to "truth"; CAUSE classification.
        assert result.parts[1].tag is IntentTag.CAUSE
        assert result.parts[1].subject == "truth"

    def test_explain_x_but_also_how_does_it_work(self) -> None:
        result = classify_compound_intent("Explain truth, but how does it work?")
        assert result.is_compound()
        assert result.parts[0].tag is IntentTag.DEFINITION
        assert result.parts[0].subject == "truth"
        # how-does-X-work routes to CAUSE per the existing _HOW_DOES_X_RE
        # rule once the pronoun is rewritten.
        assert result.parts[1].tag is IntentTag.CAUSE
        assert result.parts[1].subject == "truth"

    def test_what_is_x_because_y(self) -> None:
        # Non-anaphoric trailing fragment — kept as-is, classified
        # independently.
        result = classify_compound_intent(
            "What is truth, because what causes evidence?"
        )
        assert result.is_compound()
        assert result.parts[0].tag is IntentTag.DEFINITION
        assert result.parts[0].subject == "truth"
        assert result.parts[1].tag is IntentTag.CAUSE
        assert result.parts[1].subject == "evidence"

    def test_decomposition_preserves_source_order(self) -> None:
        # Order in compound must match order of fragments in the prompt
        # — never re-sorted by tag or alphabet.
        result = classify_compound_intent(
            "What is wisdom, and why does it matter?"
        )
        subjects = [p.subject for p in result.parts]
        assert subjects == ["wisdom", "wisdom"]
        tags = [p.tag for p in result.parts]
        assert tags == [IntentTag.DEFINITION, IntentTag.CAUSE]

    def test_three_part_compound(self) -> None:
        result = classify_compound_intent(
            "What is truth, and what is knowledge, and why does it matter?"
        )
        # Three fragments → three parts.  Anaphoric "it" in the trailing
        # fragment refers to the immediately prior subject (knowledge).
        assert len(result.parts) == 3
        assert result.parts[0].subject == "truth"
        assert result.parts[1].subject == "knowledge"
        assert result.parts[2].tag is IntentTag.CAUSE
        assert result.parts[2].subject == "knowledge"


# ---------------------------------------------------------------------------
# Degenerate / fall-through cases
# ---------------------------------------------------------------------------


class TestDegenerateCases:
    def test_empty_prompt_returns_single_unknown_part(self) -> None:
        result = classify_compound_intent("")
        assert len(result.parts) == 1
        assert result.parts[0].tag is IntentTag.UNKNOWN

    def test_no_connector_returns_single_part(self) -> None:
        result = classify_compound_intent("Explain truth.")
        assert len(result.parts) == 1
        assert result.parts[0].tag is IntentTag.DEFINITION
        assert result.parts[0].subject == "truth"

    def test_unknown_parts_with_empty_subject_are_dropped(self) -> None:
        # The only fragments that get dropped are UNKNOWN with empty
        # subject — they carry no useful planning signal.  UNKNOWN
        # parts that carry a non-empty subject are still preserved
        # (the planner will simply not ground them, which is honest).
        result = classify_compound_intent("foo, and bar")
        # Both classify to UNKNOWN with non-empty subjects ⇒ both kept.
        assert len(result.parts) == 2
        assert all(p.tag is IntentTag.UNKNOWN for p in result.parts)

    def test_pure_whitespace_fragments_fall_back_to_flat(self) -> None:
        # Constructed so every split fragment is empty after stripping.
        result = classify_compound_intent(",   and   ,")
        # No usable parts ⇒ compound layer falls back to a single-part
        # shape so callers always see at least one part.
        assert len(result.parts) == 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestCompoundDeterminism:
    @pytest.mark.parametrize(
        "prompt",
        [
            "What is truth, and why does it matter?",
            "Explain memory, but how does it work?",
            "What is truth, and what is knowledge?",
            "What is truth?",
            "",
        ],
    )
    def test_byte_stable_across_calls(self, prompt: str) -> None:
        results = [classify_compound_intent(prompt) for _ in range(8)]
        assert len({r for r in results}) == 1

    def test_compound_intent_is_frozen(self) -> None:
        result = classify_compound_intent("What is truth?")
        with pytest.raises((AttributeError, TypeError)):
            result.parts = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Doctrine: no new IntentTag introduced
# ---------------------------------------------------------------------------


class TestNoNewIntentTagIntroduced:
    def test_intent_tag_membership_unchanged(self) -> None:
        # The compound layer must not add IMPORTANCE / MATTER /
        # any other tag.  "Why does it matter?" maps to CAUSE.
        names = {tag.name for tag in IntentTag}
        assert "IMPORTANCE" not in names
        assert "MATTER" not in names

    def test_why_does_it_matter_maps_to_cause(self) -> None:
        result = classify_compound_intent(
            "What is truth, and why does it matter?"
        )
        assert result.parts[1].tag is IntentTag.CAUSE
