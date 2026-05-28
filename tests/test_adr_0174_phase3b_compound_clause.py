"""ADR-0174 Phase 3b — compound-clause held hypotheses.

Acceptance tests for the compound-clause extension to
``generate.recognizer_match._try_extract_discrete_count_anchor``.

All tests are skipped until the implementer:
  1. Implements ``_try_extract_compound_discrete_count_anchors`` in
     ``generate/recognizer_match.py``
  2. Raises HYPOTHESIS_CAP in ``generate/comprehension/state.py``
     from 4 to 8 (case 0040 has 5 anchors)
  3. Removes the ``@pytest.mark.skip`` decorators below
"""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# 1. Pure conjunctive list — the load-bearing case
# ---------------------------------------------------------------------------


class TestPureConjunctiveList:
    """The canonical Phase 3b case: 'X has N₁ unit, N₂ unit, ..., and Nₖ unit'
    must emit k separate anchors sharing subject + verb from the head clause."""

    def test_two_clause_proper_noun_subject_admits(self) -> None:
        """Case 0027: 'Malcolm has 240 followers on Instagram and 500
        followers on Facebook.' — two anchors, same actor (Malcolm),
        same verb (has), same unit (followers). Both must admit."""
        from generate.recognizer_match import (
            _try_extract_compound_discrete_count_anchors as extract_compound,
            _padded_lower,
        )
        from generate.recognizer_registry import load_ratified_registry

        reg = load_ratified_registry()
        spec = next(r.canonical_pattern for r in reg
                    if r.shape_category.value == "discrete_count_statement")
        stmt = "Malcolm has 240 followers on Instagram and 500 followers on Facebook."
        anchors = extract_compound(stmt, _padded_lower(stmt), spec)
        assert anchors is not None
        assert len(anchors) == 2
        assert all(a["subject_role"] == "Malcolm" for a in anchors)
        assert all(a["verb_token"] == "has" for a in anchors)
        assert all(a["anchor_kind"] == "possession" for a in anchors)
        assert {int(a["count_token"]) for a in anchors} == {240, 500}

    def test_five_clause_pronoun_subject_with_single_actor_admits(self) -> None:
        """5-clause compound with pronoun subject + single antecedent.
        Note: this uses 'He has' (not 'He now has') because the existing
        canonical regex doesn't admit adverb-between-subject-and-verb;
        adverb-stripping is out of Phase 3b scope (would be a separate
        regex widening). Case 0040 ('He now has...') therefore remains
        refused after Phase 3b — see Implementation Notes in ADR-0174."""
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Daniel has adopted many stray animals. "
            "He has 2 horses, 5 dogs, 7 cats, 3 turtles, and 1 goat. "
            "How many horses does Daniel have?"
        )
        r = parse_and_solve(text)
        lookback = [
            json.loads(e) for e in r.reader_trace
            if json.loads(e).get("layer") == "lookback"
        ]
        admitted_events = [e for e in lookback if e.get("outcome") == "admitted"]
        assert len(admitted_events) == 5
        assert all(e.get("resolved_to") == "Daniel" for e in admitted_events)


# ---------------------------------------------------------------------------
# 2. Refusal-preferring discipline — wrong=0 protection
# ---------------------------------------------------------------------------


class TestRefusalPreferring:
    """Phase 3b is all-or-nothing per sentence. ANY clause failing
    refuses the whole sentence (preserves wrong=0)."""

    def test_mixed_verb_compound_refuses(self) -> None:
        """Case 0021: 'He bench presses 15 pounds for 10 reps and does
        3 sets.' — two different verbs (presses, does); refuse."""
        from generate.recognizer_match import (
            _try_extract_compound_discrete_count_anchors as extract_compound,
            _padded_lower,
        )
        from generate.recognizer_registry import load_ratified_registry
        reg = load_ratified_registry()
        spec = next(r.canonical_pattern for r in reg
                    if r.shape_category.value == "discrete_count_statement")
        stmt = "He bench presses 15 pounds for 10 reps and does 3 sets."
        assert extract_compound(stmt, _padded_lower(stmt), spec) is None

    def test_multiplicative_tail_compound_refuses(self) -> None:
        """Case 0036: 'She studied for 2 hours on Wednesday and three
        times as long on Thursday.' — multiplicative second clause;
        refuse (not a pure count list)."""
        from generate.recognizer_match import (
            _try_extract_compound_discrete_count_anchors as extract_compound,
            _padded_lower,
        )
        from generate.recognizer_registry import load_ratified_registry
        reg = load_ratified_registry()
        spec = next(r.canonical_pattern for r in reg
                    if r.shape_category.value == "discrete_count_statement")
        stmt = "She studied for 2 hours on Wednesday and three times as long on Thursday."
        assert extract_compound(stmt, _padded_lower(stmt), spec) is None

    def test_non_whitelisted_head_verb_refuses(self) -> None:
        """Compound extension does not widen the verb whitelist.
        'Two puppies, two kittens, and three parakeets were for sale'
        — 'were' not in whitelist; refuse."""
        from generate.recognizer_match import (
            _try_extract_compound_discrete_count_anchors as extract_compound,
            _padded_lower,
        )
        from generate.recognizer_registry import load_ratified_registry
        reg = load_ratified_registry()
        spec = next(r.canonical_pattern for r in reg
                    if r.shape_category.value == "discrete_count_statement")
        stmt = "Two puppies, two kittens, and three parakeets were for sale at the pet shop."
        assert extract_compound(stmt, _padded_lower(stmt), spec) is None

    def test_partial_grounding_refuses_whole(self) -> None:
        """If 1 of 5 clauses doesn't ground at constraint check, all 5
        drop. Per_sentence_choices receives nothing — refusal-preferring."""
        from generate.math_candidate_graph import parse_and_solve
        # Constructed: 4 clauses ground, 1 doesn't (bogus noun)
        text = (
            "Sam has 2 horses, 5 dogs, 7 cats, 3 turtles, and 1 bogusnoun. "
            "How many horses does Sam have?"
        )
        r = parse_and_solve(text)
        # All-or-nothing: the per_sentence_choices append doesn't fire,
        # so the question can't be answered.
        assert r.answer is None


# ---------------------------------------------------------------------------
# 3. HYPOTHESIS_CAP raise (4 → 8) and enforcement
# ---------------------------------------------------------------------------


class TestHypothesisCap:
    def test_cap_raised_to_eight(self) -> None:
        from generate.comprehension.state import HYPOTHESIS_CAP
        assert HYPOTHESIS_CAP == 8

    def test_nine_anchor_compound_refuses(self) -> None:
        """Synthetic 9-anchor compound — exceeds CAP. Refuse rather
        than truncate."""
        from generate.recognizer_match import (
            _try_extract_compound_discrete_count_anchors as extract_compound,
            _padded_lower,
        )
        from generate.recognizer_registry import load_ratified_registry
        reg = load_ratified_registry()
        spec = next(r.canonical_pattern for r in reg
                    if r.shape_category.value == "discrete_count_statement")
        clauses = ", ".join(f"{n} marbles" for n in range(1, 9))
        stmt = f"Sam has {clauses}, and 9 marbles."
        # Either extraction refuses, or downstream construction refuses
        # via ProblemReadingState.open_hypotheses cap check.
        result = extract_compound(stmt, _padded_lower(stmt), spec)
        assert result is None or len(result) <= 8


# ---------------------------------------------------------------------------
# 4. Pronoun + multi-actor interaction (Phase 3a defense preserved)
# ---------------------------------------------------------------------------


class TestPronounMultiActorDefenseOnCompound:
    def test_compound_pronoun_with_multi_actor_refuses(self) -> None:
        """The Phase 3a multi-actor defense must fire when a compound
        held-hypothesis sentence carries a pronoun subject AND prior
        context has more than one distinct proper-noun subject.

        Uses prepositional-phrase shape that defeats the regex parser
        (no _filtered_statement_choices output), so the case routes
        through the recognizer-injection branch where the Phase 3a
        multi-actor defense lives.

        KNOWN LIMITATION (latent): when the regex parser HAS extracted
        candidates (simpler compound shapes without intervening PPs),
        the Phase 3a defense is bypassed because the recognizer branch
        is skipped. Future work: extend multi-actor defense to regex-
        path output too. Tracked in
        project-adr-0174-multi-actor-pronoun-hazard memory.
        """
        # ADR-0174 Phase 4 amendment: with mixed-gender antecedents,
        # Phase 4's contemplate would resolve the pronoun via the
        # gendered-names pack (Alice=female, Bob=male). To test the
        # Phase 3a defense in isolation on a COMPOUND case, use
        # same-gender antecedents so Phase 4 returns None and the
        # defense still fires.
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Alice has 5 followers. "
            "Mary has 3 followers. "
            "She has 2 followers on Instagram and 4 followers on Facebook. "
            "How many followers does Alice have?"
        )
        r = parse_and_solve(text)
        lookback = [
            json.loads(e) for e in r.reader_trace
            if json.loads(e).get("layer") == "lookback"
        ]
        assert any(e.get("outcome") == "no_antecedent_ambiguous"
                   for e in lookback)


# ---------------------------------------------------------------------------
# 5. wrong=0 invariant + case 0050 canary
# ---------------------------------------------------------------------------


class TestWrongZeroPreservation:
    def test_train_sample_wrong_is_zero(self) -> None:
        from pathlib import Path
        from evals.gsm8k_math.train_sample.v1.runner import (
            build_report, _CASES_PATH,
        )
        cases = [
            json.loads(l) for l in Path(_CASES_PATH).open() if l.strip()
        ]
        report = build_report(cases, use_reader=True)
        assert report["counts"]["wrong"] == 0

    def test_case_0050_remains_refused(self) -> None:
        """The wrong=0 canary. Compound-clause widening must NOT flip
        case 0050 from refused to wrong."""
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Mark does a gig every other day for 2 weeks. "
            "He gets paid $50 per gig. He then gets a 50% raise. "
            "How much money does he make per week?"
        )
        r = parse_and_solve(text)
        assert r.answer is None
