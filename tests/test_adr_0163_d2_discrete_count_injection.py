"""ADR-0163.D.2 — discrete_count_statement injection v1.

This test file is the single load-bearing artifact of D.2 v1.  It
enforces the wrong=0 safety net by testing five categories:

  a. EXTRACTION CORRECTNESS — matcher extracts correct anchors.
  b. EXTRACTION REFUSAL — matcher refuses on ambiguous shapes.
  c. INJECTION CORRECTNESS — injector builds CandidateInitial that
     passes _initial_admissible.
  d. NO-FALSE-LIFT INVARIANT — synthetic adversarial cases never
     produce a wrong answer.
  e. END-TO-END LIFT — discrete_count injection wires through the
     candidate-graph and lifts a refusal to a correct answer when
     the statement is unambiguous and groundable.
"""

from __future__ import annotations

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import CandidateInitial
from generate.math_problem_graph import InitialPossession, Quantity
from generate.recognizer_anchor_inject import (
    inject_discrete_count_statement,
    inject_from_match,
)
from generate.recognizer_match import (
    RecognizerMatch,
    _padded_lower,
    _try_extract_discrete_count_anchor,
    match,
)
from generate.recognizer_registry import load_ratified_registry


# Spec mirror — kept locally so the tests don't depend on registry
# load order.  The values mirror the ratified Phase C round-2 spec for
# discrete_count_statement.
_SPEC = {
    "anchor_kind": "discrete_count",
    "shape_category": "discrete_count_statement",
    "graph_intent": "count",
    "anchor_count_min": 1,
    "anchor_count_max": 5,
    "outcome": "admissible",
    "observed_count_kinds": ["integer", "word"],
    "observed_counted_nouns": [
        "Pokemon cards", "apples", "balloons", "books", "cats",
        "chickens", "dogs", "followers", "goat", "horses", "kittens",
        "marbles", "motorcycles", "nephews", "paintbrushes",
        "paperclips", "parakeets", "pounds", "puppies", "seashells",
        "stickers", "sunflowers", "swallows", "turtles", "typewriters",
    ],
}


def _try_extract(statement: str):
    return _try_extract_discrete_count_anchor(
        statement, _padded_lower(statement), _SPEC,
    )


def _ratified_registry():
    """Live ratified registry; resolved once for end-to-end tests."""
    return load_ratified_registry()


# ---------------------------------------------------------------------------
# (a) Extraction correctness — matcher extracts the right anchors.
# ---------------------------------------------------------------------------


class TestExtractionCorrectness:
    def test_basic_integer_count(self) -> None:
        a = _try_extract("Sam has 5 apples.")
        # Post-W2 (ADR-0170): anchor carries anchor_kind discriminator
        # and verb_token for the injector's dispatch + admissibility.
        assert a == {
            "kind": "discrete_count",
            "subject_role": "Sam",
            "count_token": "5",
            "count_kind": "integer",
            "counted_noun": "apples",
            "anchor_kind": "possession",
            "verb_token": "has",
        }

    def test_past_tense_had(self) -> None:
        a = _try_extract("Nicole had 400 paperclips.")
        assert a is not None
        assert a["subject_role"] == "Nicole"
        assert a["count_token"] == "400"
        assert a["count_kind"] == "integer"
        assert a["counted_noun"] == "paperclips"

    def test_word_form_count(self) -> None:
        a = _try_extract("Sam has twenty books.")
        assert a is not None
        assert a["count_token"] == "twenty"
        assert a["count_kind"] == "word"

    def test_hyphenated_word_form(self) -> None:
        a = _try_extract("Sam has twenty-five books.")
        assert a is not None
        assert a["count_token"] == "twenty-five"
        assert a["count_kind"] == "word"

    def test_multi_word_counted_noun(self) -> None:
        a = _try_extract("Sam has 5 Pokemon cards.")
        assert a is not None
        # Canonicalized to spec casing.
        assert a["counted_noun"] == "Pokemon cards"

    def test_trailing_modifier(self) -> None:
        # Trailing prepositional phrase is allowed; the regex anchors
        # on the noun and tolerates benign tail content (no
        # clause-split markers).
        a = _try_extract("Sam has 5 apples on the table.")
        assert a is not None
        assert a["count_token"] == "5"
        assert a["counted_noun"] == "apples"


# ---------------------------------------------------------------------------
# (b) Extraction refusal — refuse on ambiguity, never over-admit.
# ---------------------------------------------------------------------------


class TestExtractionRefusal:
    def test_multi_subject_refused(self) -> None:
        assert _try_extract("Tom and Mary have 5 apples.") is None

    def test_indefinite_quantifier_refused(self) -> None:
        # 'some apples' — no concrete count.  The detection-level
        # check filters this through _has_any_quantity_marker
        # already, but the extractor must independently refuse when
        # the count token cannot be resolved.
        assert _try_extract("Sam has some apples.") is None

    def test_missing_counted_noun_refused(self) -> None:
        assert _try_extract("Sam has 5.") is None

    def test_pronoun_subject_refused(self) -> None:
        assert _try_extract("He has 5 apples.") is None

    def test_lowercase_subject_refused(self) -> None:
        assert _try_extract("sam has 5 apples.") is None

    def test_clause_split_refused(self) -> None:
        # "but then" indicates a trailing operation; v1 refuses.
        assert _try_extract(
            "Yun had 20 paperclips initially, but then lost 12."
        ) is None

    def test_enumeration_and_refused(self) -> None:
        # Multi-anchor enumeration: " and " split refuses.
        assert _try_extract(
            "Malcolm has 240 followers on Instagram and 500 followers on Facebook."
        ) is None

    def test_multi_count_refused(self) -> None:
        # Two digit runs — v1 admits exactly one count.
        assert _try_extract("He has 2 horses, 5 dogs.") is None

    def test_unobserved_counted_noun_now_admits(self) -> None:
        # ADR-0192 — the counted-noun slot is OPEN: an unobserved noun
        # ('widgets', not in the spec's observed_counted_nouns) admits
        # under the simple possession shape. The other narrowness layers
        # (subject/verb/count/clause) and the downstream ADR-0191
        # completeness guard + round-trip hold wrong=0, not the noun list.
        result = _try_extract("Sam has 5 widgets.")
        assert result is not None
        assert result["counted_noun"].lower() == "widgets"
        assert result["count_token"] == "5"
        assert result["anchor_kind"] == "possession"

    def test_non_possession_non_acquisition_verb_refused(self) -> None:
        # Post-W2 (ADR-0170): possession verbs (has/have/had) AND
        # acquisition verbs (collected/received/bought/got) extract
        # successfully — the latter dispatched to CandidateOperation(add)
        # in the injector. Verbs outside both sets still refuse.
        assert _try_extract("Michael wants 10 pounds.") is None
        # 'gained' is deliberately EXCLUDED from _ACQUISITION_VERBS
        # (delta-of-attribute hazard); must still refuse.
        assert _try_extract("Orlando gained 5 pounds.") is None
        # 'donated' is a SUBTRACT verb (actor gives away); deferred
        # until a separate W2.1 PR adds depletion-verb handling.
        assert _try_extract("Alice donated 3 books.") is None

    def test_acquisition_verbs_extract_with_anchor_kind(self) -> None:
        # Post-W2 (ADR-0170): acquisition verbs extract with
        # anchor_kind='acquisition'. The injector then emits
        # CandidateOperation(add) rather than CandidateInitial.
        result = _try_extract("Nicole collected 400 paperclips.")
        assert result is not None
        assert result["anchor_kind"] == "acquisition"
        assert result["verb_token"] == "collected"

        result_buy = _try_extract("Sam bought 5 apples.")
        assert result_buy is not None
        assert result_buy["anchor_kind"] == "acquisition"
        assert result_buy["verb_token"] == "bought"

    def test_possession_verbs_extract_with_possession_kind(self) -> None:
        # Pre-W2 behavior preserved: possession verbs extract with
        # anchor_kind='possession'; injector emits CandidateInitial.
        result = _try_extract("Sam has 5 apples.")
        assert result is not None
        assert result["anchor_kind"] == "possession"
        assert result["verb_token"] == "has"

    def test_owns_outside_v1_whitelist(self) -> None:
        # v1 restricts to has/have/had to align with CandidateInitial's
        # post-init whitelist.  Broader possession verbs (owns/holds/
        # contains) defer to follow-up.
        assert _try_extract("Sam owns 12 books.") is None


# ---------------------------------------------------------------------------
# (c) Injection correctness — built CandidateInitial passes the
#     structural admissibility check.
# ---------------------------------------------------------------------------


def _make_match(parsed_anchors) -> RecognizerMatch:
    """Build a synthetic RecognizerMatch for injector unit tests."""
    from generate.recognizer_registry import RatifiedRecognizer

    rec = RatifiedRecognizer(
        proposal_id="test-discrete-count",
        shape_category=ShapeCategory.DISCRETE_COUNT_STATEMENT,
        canonical_pattern=dict(_SPEC),
        spec_digest="test-digest",
        review_date="2026-05-27",
        ratified_at_revision="test",
    )
    return RecognizerMatch(
        recognizer=rec,
        category=ShapeCategory.DISCRETE_COUNT_STATEMENT,
        outcome="admissible",
        graph_intent="count",
        parsed_anchors=tuple(parsed_anchors),
    )


class TestInjectionCorrectness:
    def test_injects_candidate_initial(self) -> None:
        m = _make_match([{
            "kind": "discrete_count",
            "subject_role": "Sam",
            "count_token": "5",
            "count_kind": "integer",
            "counted_noun": "apples",
        }])
        out = inject_discrete_count_statement(m, "Sam has 5 apples.")
        assert len(out) == 1
        cand = out[0]
        assert isinstance(cand, CandidateInitial)
        assert cand.initial == InitialPossession(
            entity="Sam",
            quantity=Quantity(value=5, unit="apples"),
        )
        assert cand.matched_anchor == "has"
        assert cand.matched_value_token == "5"
        assert cand.matched_unit_token == "apples"
        assert cand.matched_entity_token == "Sam"
        assert cand.source_span == "Sam has 5 apples."

    def test_injects_word_form(self) -> None:
        m = _make_match([{
            "kind": "discrete_count",
            "subject_role": "Sam",
            "count_token": "twenty",
            "count_kind": "word",
            "counted_noun": "books",
        }])
        out = inject_discrete_count_statement(m, "Sam has twenty books.")
        assert len(out) == 1
        assert out[0].initial.quantity.value == 20

    def test_empty_parsed_anchors_returns_empty(self) -> None:
        m = _make_match([])
        out = inject_discrete_count_statement(m, "Sam has 5 apples.")
        assert out == ()

    def test_injector_passes_initial_admissible(self) -> None:
        # The candidate-graph's _initial_admissible MUST accept the
        # injected CandidateInitial.  This is the structural-grounding
        # safety net.
        from generate.math_candidate_graph import _initial_admissible

        m = _make_match([{
            "kind": "discrete_count",
            "subject_role": "Sam",
            "count_token": "5",
            "count_kind": "integer",
            "counted_noun": "apples",
        }])
        out = inject_discrete_count_statement(m, "Sam has 5 apples.")
        assert out
        assert _initial_admissible(out[0]) is True

    def test_dispatch_routes_to_per_category_injector(self) -> None:
        m = _make_match([{
            "kind": "discrete_count",
            "subject_role": "Sam",
            "count_token": "5",
            "count_kind": "integer",
            "counted_noun": "apples",
        }])
        out_dispatch = inject_from_match(m, "Sam has 5 apples.")
        out_direct = inject_discrete_count_statement(m, "Sam has 5 apples.")
        assert out_dispatch == out_direct

    def test_dispatch_unsupported_category_returns_empty(self) -> None:
        from generate.recognizer_registry import RatifiedRecognizer

        rec = RatifiedRecognizer(
            proposal_id="test-rate",
            shape_category=ShapeCategory.RATE_WITH_CURRENCY,
            canonical_pattern={},
            spec_digest="test",
            review_date="2026-05-27",
            ratified_at_revision="test",
        )
        m = RecognizerMatch(
            recognizer=rec,
            category=ShapeCategory.RATE_WITH_CURRENCY,
            outcome="admissible",
            graph_intent="rate",
            parsed_anchors=({"any": "thing"},),
        )
        assert inject_from_match(m, "Tina makes $18.00 an hour.") == ()

    def test_injection_under_admits_on_unresolvable_verb(self) -> None:
        # If the source sentence has no possession-anchor verb, the
        # injector refuses (returns ()).  This is the under-admit
        # safety net for matcher/sentence disagreement.
        m = _make_match([{
            "kind": "discrete_count",
            "subject_role": "Sam",
            "count_token": "5",
            "count_kind": "integer",
            "counted_noun": "apples",
        }])
        out = inject_discrete_count_statement(m, "Sam collected 5 apples.")
        assert out == ()


# ---------------------------------------------------------------------------
# (d) No-false-lift invariant — adversarial cases never produce a
#     wrong answer.  The case must either refuse or produce the
#     entity-consistent correct answer; wrong=0 is non-negotiable.
# ---------------------------------------------------------------------------


class TestNoFalseLiftInvariant:
    def test_clause_split_adversarial(self) -> None:
        # "Yun had 20 paperclips initially, but then lost 12.  How
        # many paperclips does Yun have?"  Wrong reading is 20;
        # correct reading is 8.  The matcher MUST refuse extraction
        # so the case refuses.
        r = parse_and_solve(
            "Yun had 20 paperclips initially, but then lost 12. "
            "How many paperclips does Yun have?"
        )
        # Under v1, this refuses; the answer must never be 20.0.
        assert r.answer != 20
        assert r.answer != 20.0

    def test_enumeration_adversarial(self) -> None:
        # "Malcolm has 240 followers on Instagram and 500 followers
        # on Facebook.  How many followers does Malcolm have?"  Wrong
        # reading injects only 240 (missing the 500); a wrong=0
        # violation if admitted.  The matcher MUST refuse.
        r = parse_and_solve(
            "Malcolm has 240 followers on Instagram and 500 followers on Facebook. "
            "How many followers does Malcolm have?"
        )
        assert r.answer != 240
        assert r.answer != 240.0

    def test_branch_disagreement_safety_net(self) -> None:
        # Construct a problem where the existing parser already
        # handles the statement; the recognizer would also match but
        # the injection path is never consulted because choices is
        # non-empty.  This proves injection is upstream-gated.
        r = parse_and_solve(
            "Sam has 5 apples. Sam buys 3 apples. "
            "How many apples does Sam have?"
        )
        assert r.is_admitted
        assert r.answer == 8

    def test_existing_parser_unchanged_for_canonical_form(self) -> None:
        # Canonical "X has N Y" is handled by the existing parser
        # without ever reaching injection.  Confirms no behavioral
        # regression on the base case.
        r = parse_and_solve("Sam has 5 apples. How many apples does Sam have?")
        assert r.is_admitted
        assert r.answer == 5


# ---------------------------------------------------------------------------
# (e) End-to-end lift — injection wires through and lifts a refusal
#     to a correct answer when the statement is unambiguous and
#     groundable.
# ---------------------------------------------------------------------------


class TestEndToEndLift:
    def test_trailing_clause_lift(self) -> None:
        # The existing _INITIAL_HAS_RE refuses statements with
        # arbitrary trailing prepositional phrases (e.g., 'on the
        # table top above the shelf').  The discrete_count matcher
        # admits, the injector builds a CandidateInitial, and the
        # solver answers correctly.
        problem = (
            "Sam has 5 apples on the table top above the shelf where books are. "
            "How many apples does Sam have?"
        )
        r = parse_and_solve(problem)
        assert r.is_admitted
        assert r.answer == 5

    def test_lift_uses_recognizer_path(self) -> None:
        # Confirm the lift specifically comes through recognizer
        # injection: the same sentence in isolation produces zero
        # candidates from the existing parser.
        from generate.math_candidate_graph import _filtered_statement_choices

        s = "Sam has 5 apples on the table top above the shelf where books are."
        assert _filtered_statement_choices(s) == []
        # But the recognizer matches it.
        m = match(s, _ratified_registry())
        assert m is not None
        assert m.category is ShapeCategory.DISCRETE_COUNT_STATEMENT
        assert m.parsed_anchors  # non-empty

    def test_unobserved_noun_refuses_end_to_end(self) -> None:
        # 'widgets' is not in the spec's observed_counted_nouns.
        # The detection-only fallback is taken (skip-only), but the
        # question still needs an entity ground — without state, the
        # problem refuses.
        r = parse_and_solve(
            "Sam has 5 widgets blah blah blah blah blah. "
            "How many widgets does Sam have?"
        )
        assert not r.is_admitted
        assert r.answer is None


# ---------------------------------------------------------------------------
# Replay-gate sanity (safety net #4) — the existing replay gate is
# evaluated outside the test harness, but the injection MUST be
# deterministic so the gate's byte-equality comparison holds.
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_extraction_is_deterministic(self) -> None:
        s = "Sam has 5 apples."
        a1 = _try_extract(s)
        a2 = _try_extract(s)
        assert a1 == a2

    def test_injection_is_deterministic(self) -> None:
        m = _make_match([{
            "kind": "discrete_count",
            "subject_role": "Sam",
            "count_token": "5",
            "count_kind": "integer",
            "counted_noun": "apples",
        }])
        out1 = inject_discrete_count_statement(m, "Sam has 5 apples.")
        out2 = inject_discrete_count_statement(m, "Sam has 5 apples.")
        assert out1 == out2

    def test_end_to_end_is_deterministic(self) -> None:
        problem = (
            "Sam has 5 apples on the table top above the shelf where books are. "
            "How many apples does Sam have?"
        )
        r1 = parse_and_solve(problem)
        r2 = parse_and_solve(problem)
        assert r1.answer == r2.answer
        assert r1.refusal_reason == r2.refusal_reason
