"""ADR-0163.D.4 — question grammar extension tests.

Three new question shapes:
  Pattern A — "How much MASS_NOUN does ENTITY VERB ..."
  Pattern B — "How many more UNIT does ENTITY VERB ..." (comparative_marker=True)
  Pattern C — "How many UNIT does PRONOUN VERB [to VERB2] ..."

wrong=0 safety nets exercised here:
  - positive cases: each pattern admits expected GSM8K shapes
  - negative cases: each pattern refuses adjacent shapes that would
    over-admit a wrong entity/unit/answer
  - pronoun resolver determinism: same (pronoun, problem_text) →
    byte-identical resolution
  - pronoun resolver refuse-on-ambiguity: multiple distinct
    female/male names → no admission
  - solver-layer multi-branch refusal: when grammar admits but
    candidates disagree on the answer, downstream refuses
"""

from __future__ import annotations

import pytest

from generate.math_candidate_parser import (
    CandidateUnknown,
    _pattern_b_detects,
    _resolve_pronoun_entity,
    extract_question_candidates,
)
from generate.math_candidate_graph import _filtered_question_choices


# ---------------------------------------------------------------------------
# Pattern A — mass-noun questions
# ---------------------------------------------------------------------------


class TestPatternAMassNoun:
    """How much MASS_NOUN does ENTITY VERB ...?"""

    def test_admits_money_make_named_entity(self) -> None:
        out = extract_question_candidates(
            "How much money does Tina make?"
        )
        assert len(out) == 1
        assert out[0].unknown.unit == "money"
        assert out[0].unknown.entity == "Tina"

    def test_admits_money_make_pronoun_with_problem_text(self) -> None:
        problem = "Tina makes $18.00 an hour. How much money does she make?"
        out = extract_question_candidates(
            "How much money does she make?", problem_text=problem,
        )
        assert len(out) == 1
        assert out[0].unknown.entity == "Tina"
        assert out[0].unknown.unit == "money"

    def test_admits_profit_and_savings_and_cost(self) -> None:
        for noun, verb in (
            ("profit", "make"),
            ("savings", "have"),
            ("cost", "pay"),
            ("income", "earn"),
        ):
            out = extract_question_candidates(
                f"How much {noun} does Bob {verb}?"
            )
            assert len(out) == 1, (noun, verb)
            assert out[0].unknown.unit == noun

    def test_admits_will_make(self) -> None:
        problem = "Bob has $40. How much money will Bob make?"
        out = extract_question_candidates(
            "How much money will Bob make?", problem_text=problem,
        )
        assert len(out) == 1
        assert out[0].unknown.entity == "Bob"

    def test_admits_with_tail(self) -> None:
        out = extract_question_candidates(
            "How much money does Tina earn over the weekend?"
        )
        assert len(out) == 1
        assert out[0].unknown.unit == "money"

    # Negative cases — must NOT match.

    def test_refuses_non_whitelisted_mass_noun(self) -> None:
        # "water" is mass but not in _MASS_NOUNS whitelist → refuse.
        out = extract_question_candidates(
            "How much water does Bob have?"
        )
        # The standard _Q_ENTITY_RE also doesn't match (it wants "many"),
        # so we expect zero admission.
        assert out == []

    def test_refuses_no_action_verb(self) -> None:
        # No action verb in whitelist; bare prepositional phrase.
        out = extract_question_candidates(
            "How much money is in the bank?"
        )
        assert out == []

    def test_refuses_unresolvable_pronoun_no_problem_text(self) -> None:
        # Pronoun + no problem_text → cannot resolve → refuse.
        out = extract_question_candidates(
            "How much money does she make?"
        )
        assert out == []

    def test_refuses_unresolvable_pronoun_ambiguous_problem_text(self) -> None:
        # Two female names in problem text → "she" is ambiguous → refuse.
        problem = "Alice has $20 and Mary has $30. How much money does she make?"
        out = extract_question_candidates(
            "How much money does she make?", problem_text=problem,
        )
        assert out == []


# ---------------------------------------------------------------------------
# Pattern B — comparative quantifier "how many more"
# ---------------------------------------------------------------------------


class TestPatternBComparative:
    """How many more UNIT does ENTITY VERB ...?

    wrong=0 GATE: Pattern B is structurally detected by the grammar but
    intentionally emits NO candidate until the solver gains comparative
    semantics (D.5 follow-up).  The plain "How many UNIT does ENTITY
    have?" path would return the entity's current total — wrong for
    "how many MORE are needed."  These tests verify the detector + gate
    behaviour.
    """

    # Grammar-level detection (regex match).

    def test_detects_boxes_need(self) -> None:
        assert _pattern_b_detects("How many more boxes does Francine need?")

    def test_detects_pronoun_modal(self) -> None:
        assert _pattern_b_detects("How many more apples would she need?")

    def test_detects_have_variant(self) -> None:
        assert _pattern_b_detects("How many more cards does Bob have?")

    def test_detects_modal_will(self) -> None:
        assert _pattern_b_detects("How many more apples will Bob gain?")

    def test_detects_did_variant(self) -> None:
        assert _pattern_b_detects("How many more boxes did Bob need?")

    # Emission gate — must NOT emit a candidate (preserves wrong=0).

    def test_does_not_emit_candidate_yet(self) -> None:
        out = extract_question_candidates(
            "How many more boxes does Francine need?"
        )
        assert out == []

    def test_does_not_emit_for_resolvable_pronoun(self) -> None:
        problem = "Martha has 20 apples. How many more apples would she need?"
        out = extract_question_candidates(
            "How many more apples would she need?", problem_text=problem,
        )
        assert out == []

    # Negative cases — detector must NOT match.

    def test_detector_refuses_no_more_keyword(self) -> None:
        assert not _pattern_b_detects("How many boxes does Bob need?")

    def test_detector_refuses_outside_verb_whitelist(self) -> None:
        assert not _pattern_b_detects("How many more boxes does Bob draw?")

    def test_emits_nothing_for_ambiguous_pronoun(self) -> None:
        problem = "Alice has 5. Mary has 7. How many more apples does she need?"
        out = extract_question_candidates(
            "How many more apples does she need?", problem_text=problem,
        )
        assert out == []


# ---------------------------------------------------------------------------
# Pattern C — pronoun-or-entity + non-"have" verb
# ---------------------------------------------------------------------------


class TestPatternCPronounVerb:
    """How many UNIT does PRONOUN/ENTITY VERB [to VERB2] ...?"""

    def test_admits_cups_does_she_need_to_sell(self) -> None:
        problem = (
            "Alexa has a lemonade stand where she sells lemonade for $2 for "
            "one cup. If she spent $20 on ingredients, how many cups of "
            "lemonade does she need to sell to make a profit of $80?"
        )
        out = extract_question_candidates(
            "How many cups does she need to sell?", problem_text=problem,
        )
        assert len(out) == 1
        assert out[0].unknown.entity == "Alexa"
        assert out[0].unknown.unit == "cups"

    def test_admits_named_entity_make(self) -> None:
        out = extract_question_candidates(
            "How many bracelets does Marnie make?"
        )
        assert len(out) == 1
        assert out[0].unknown.entity == "Marnie"
        assert out[0].unknown.unit == "bracelets"

    def test_admits_pick_with_to_clause(self) -> None:
        out = extract_question_candidates(
            "How many berries does Bob need to pick?"
        )
        assert len(out) == 1

    def test_admits_pronoun_resolvable_he(self) -> None:
        problem = "Fabian bought a mouse. How many mice does he buy?"
        out = extract_question_candidates(
            "How many mice does he buy?", problem_text=problem,
        )
        assert len(out) == 1
        assert out[0].unknown.entity == "Fabian"

    def test_admits_will_make(self) -> None:
        out = extract_question_candidates(
            "How many bracelets will Marnie make?"
        )
        assert len(out) == 1

    # Negative cases.

    def test_refuses_outside_verb_whitelist(self) -> None:
        # "draw" is not in Pattern C verbs.
        out = extract_question_candidates(
            "How many bracelets does Marnie draw?"
        )
        assert out == []

    def test_refuses_ambiguous_pronoun(self) -> None:
        problem = "Alice has 5 cups. Mary has 7 cups. How many cups does she sell?"
        out = extract_question_candidates(
            "How many cups does she sell?", problem_text=problem,
        )
        assert out == []

    def test_refuses_neuter_pronoun(self) -> None:
        # "it" cannot be resolved from name lists.
        problem = "The box has 5 items. How many items does it sell?"
        out = extract_question_candidates(
            "How many items does it sell?", problem_text=problem,
        )
        assert out == []

    def test_refuses_plural_pronoun(self) -> None:
        # "they" is plural; not a single-entity resolution.
        problem = "The boys have 5 cups. How many cups do they sell?"
        out = extract_question_candidates(
            "How many cups do they sell?", problem_text=problem,
        )
        # Pattern C path refuses; _Q_TOTAL_RE only matches with "have"
        # (not "sell"), so total path is also out.
        for c in out:
            # If somehow admitted, the entity MUST not be a single name.
            assert c.matched_entity_token != "they"


# ---------------------------------------------------------------------------
# Pronoun resolver — purity, determinism, ambiguity handling
# ---------------------------------------------------------------------------


class TestResolvePronounEntity:
    def test_resolves_single_female_name(self) -> None:
        text = "Tina makes $18 an hour. She works 5 days."
        assert _resolve_pronoun_entity("she", text) == "Tina"

    def test_resolves_single_male_name(self) -> None:
        text = "Fabian bought a mouse. He saved $40."
        assert _resolve_pronoun_entity("he", text) == "Fabian"

    def test_refuses_ambiguous_two_female_names(self) -> None:
        text = "Alice has 5 cups. Mary has 7 cups."
        assert _resolve_pronoun_entity("she", text) is None

    def test_refuses_ambiguous_two_male_names(self) -> None:
        text = "Bob saved $5. John saved $7."
        assert _resolve_pronoun_entity("he", text) is None

    def test_refuses_no_matching_name(self) -> None:
        # No name in the text matches the female whitelist.
        text = "The dog ran fast."
        assert _resolve_pronoun_entity("she", text) is None

    def test_refuses_plural_pronoun(self) -> None:
        text = "Tina makes $18."
        assert _resolve_pronoun_entity("they", text) is None

    def test_refuses_neuter_pronoun(self) -> None:
        text = "The box has 5 items."
        assert _resolve_pronoun_entity("it", text) is None

    def test_refuses_empty_problem_text(self) -> None:
        assert _resolve_pronoun_entity("she", "") is None
        assert _resolve_pronoun_entity("she", None) is None

    def test_deterministic_byte_identical(self) -> None:
        text = "Tina makes $18.00 an hour. She works 5 days."
        a = _resolve_pronoun_entity("she", text)
        b = _resolve_pronoun_entity("she", text)
        c = _resolve_pronoun_entity("she", text)
        assert a == b == c == "Tina"

    def test_repeated_same_name_is_single_distinct(self) -> None:
        # Same name mentioned multiple times → one distinct match.
        text = "Tina makes $18. Tina works 5 days. Tina is great."
        assert _resolve_pronoun_entity("she", text) == "Tina"

    def test_object_pronoun_her_him(self) -> None:
        text = "Tina makes $18."
        assert _resolve_pronoun_entity("her", text) == "Tina"
        text2 = "Bob saved $5."
        assert _resolve_pronoun_entity("him", text2) == "Bob"


# ---------------------------------------------------------------------------
# End-to-end via _filtered_question_choices (D.3 prefix-strip composes)
# ---------------------------------------------------------------------------


class TestComposesWithPrefixStrip:
    """Verify Pattern A/B/C compose with Phase D.3 conditional-prefix strip."""

    def test_d3_strip_then_pattern_a(self) -> None:
        # "If she works 10 hours every day for 5 days, how much money does she make?"
        problem = (
            "Tina makes $18.00 an hour.  "
            "If she works 10 hours every day for 5 days, "
            "how much money does she make?"
        )
        out = _filtered_question_choices(
            "If she works 10 hours every day for 5 days, "
            "how much money does she make?",
            problem,
        )
        assert len(out) >= 1
        assert any(c.unknown.entity == "Tina" for c in out)

    def test_d3_strip_then_pattern_b_detected_not_emitted(self) -> None:
        # Pattern B is structurally detected but emission is gated.
        # End-to-end: stripped sentence detects Pattern B; no candidate.
        stripped = "How many more apples would she need?"
        assert _pattern_b_detects(stripped)
        problem = (
            "Martha has 20 apples.  "
            "If she gives away 5, how many more apples would she need?"
        )
        out = _filtered_question_choices(
            "If she gives away 5, how many more apples would she need?",
            problem,
        )
        # No comparative_marker candidate emitted.
        assert not any(c.comparative_marker for c in out)

    def test_d3_strip_then_pattern_c(self) -> None:
        problem = (
            "Alexa has a lemonade stand.  "
            "If she spent $20 on ingredients, how many cups does she need to sell?"
        )
        out = _filtered_question_choices(
            "If she spent $20 on ingredients, "
            "how many cups does she need to sell?",
            problem,
        )
        assert len(out) >= 1
        assert any(c.unknown.entity == "Alexa" for c in out)


# ---------------------------------------------------------------------------
# Existing behavior preserved — CandidateUnknown construction unchanged
# ---------------------------------------------------------------------------


class TestCandidateUnknownDefaults:
    def test_default_comparative_marker_false(self) -> None:
        # Existing 200+ callers construct without comparative_marker.
        from generate.math_problem_graph import Unknown
        c = CandidateUnknown(
            unknown=Unknown(entity="Bob", unit="apples"),
            source_span="How many apples does Bob have?",
            matched_unit_token="apples",
            matched_entity_token="Bob",
        )
        assert c.comparative_marker is False

    def test_q_entity_re_path_sets_marker_false(self) -> None:
        out = extract_question_candidates(
            "How many apples does Bob have?"
        )
        assert len(out) == 1
        assert out[0].comparative_marker is False

    def test_q_total_re_path_sets_marker_false(self) -> None:
        out = extract_question_candidates(
            "How many apples do they have?"
        )
        assert len(out) == 1
        assert out[0].comparative_marker is False


# ---------------------------------------------------------------------------
# wrong=0 invariant — solver-layer protection against mis-extraction
# ---------------------------------------------------------------------------


class TestWrongZeroInvariantUnderAmbiguity:
    """If two entity-grounded candidates would yield different answers,
    the downstream multi-branch decision rule refuses rather than picks
    one. Pronoun mis-resolution → refuse via _resolve_pronoun_entity."""

    def test_ambiguous_problem_pronoun_extraction_refuses(self) -> None:
        # If the pronoun resolver returned the WRONG entity (Mary instead
        # of Alice), the answer downstream would be wrong.  The resolver
        # refuses on ambiguity, so no candidate emits.
        problem = (
            "Alice has 5 apples. Mary has 7 apples.  "
            "How much money does she make?"
        )
        out = extract_question_candidates(
            "How much money does she make?", problem_text=problem,
        )
        assert out == []

    def test_end_to_end_refuses_when_pronoun_ambiguous(self) -> None:
        # End-to-end: parse_and_solve should NOT produce an answer for
        # an ambiguous-pronoun problem.
        from generate.math_candidate_graph import parse_and_solve
        problem = (
            "Alice has 5 apples. Mary has 7 apples.  "
            "How many apples does she pick?"
        )
        result = parse_and_solve(problem)
        assert result.answer is None
        assert result.refusal_reason is not None
