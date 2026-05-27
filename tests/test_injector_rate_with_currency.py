"""Wave-Next A2 — ``rate_with_currency`` injector.

This test file is the load-bearing artifact for the A2 injector.  The
A2 outcome is an explicit, documented schema-refusal: ``Rate`` (ADR-0122)
DOES structurally model a per-unit rate, but it is not a member of the
``SentenceChoice = Union[CandidateInitial, CandidateOperation]`` union
the per-sentence injector contract requires.  The injector therefore
returns ``()`` and the load-bearing assertions in this file pin:

  a. SCHEMA EVIDENCE          — ``Rate`` exists and structurally models
                                a (value, numerator_unit, denominator_unit)
                                per-unit rate, distinct from ``Quantity``.
  b. SCHEMA REFUSAL           — the injector returns ``()`` for every
                                shape (broad and narrow canonical forms).
  c. DISPATCH WIRED           — dispatch table routes
                                ``RATE_WITH_CURRENCY`` to the injector
                                (no longer the empty-tuple default).
  d. CASE 0050 HAZARD PIN     — case
                                ``gsm8k-train-sample-v1-0050`` remains
                                refused at sentence_index=0 (sentence
                                carries no currency, so it neither
                                matches nor would be lifted by A2).
  e. DETERMINISM              — identical ``(match, sentence)`` →
                                byte-identical injector output.
  f. NO STATE INJECTED        — the injector never produces a
                                ``CandidateInitial`` (would be a wrong=0
                                hazard, since Rate ≠ Quantity).
"""

from __future__ import annotations

import json
from pathlib import Path

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.math_candidate_graph import SentenceChoice, parse_and_solve
from generate.math_problem_graph import Quantity, Rate
from generate.recognizer_anchor_inject import (
    _INJECTORS,
    inject_from_match,
    inject_rate_with_currency,
)
from generate.recognizer_match import RecognizerMatch
from generate.recognizer_registry import RatifiedRecognizer


# ---------------------------------------------------------------------------
# Synthetic match builder — mirrors the A1/D.2 test pattern.
# ---------------------------------------------------------------------------


def _make_match(parsed_anchors: tuple[dict, ...]) -> RecognizerMatch:
    rec = RatifiedRecognizer(
        proposal_id="test-rate-with-currency",
        shape_category=ShapeCategory.RATE_WITH_CURRENCY,
        canonical_pattern={
            "anchor_kind": "currency_per_unit_rate",
            "shape_category": "rate_with_currency",
            "graph_intent": "rate",
            "anchor_count_min": 1,
            "anchor_count_max": 1,
            "outcome": "admissible",
            "observed_currency_symbols": ["$"],
            "observed_per_units": ["hour", "day", "week"],
        },
        spec_digest="test-digest",
        review_date="2026-05-27",
        ratified_at_revision="test",
    )
    return RecognizerMatch(
        recognizer=rec,
        category=ShapeCategory.RATE_WITH_CURRENCY,
        outcome="admissible",
        graph_intent="rate",
        parsed_anchors=parsed_anchors,
    )


# ---------------------------------------------------------------------------
# (a) Schema evidence — Rate models a per-unit rate.
# ---------------------------------------------------------------------------


class TestSchemaEvidence:
    """The schema decision: does ``Quantity`` model a per-unit rate?

    Answer: NO — ``Quantity`` is a scalar+unit pair, not a rate.  BUT
    a separate ``Rate`` type (ADR-0122) DOES structurally model the
    per-unit rate via ``numerator_unit`` / ``denominator_unit``.  The
    A2 schema-refusal hinges not on the absence of ``Rate`` but on
    its absence from the ``SentenceChoice`` union.
    """

    def test_quantity_does_not_model_a_rate(self) -> None:
        # Quantity is value + unit; no numerator/denominator distinction.
        q = Quantity(value=18.0, unit="dollars")
        assert q.value == 18.0
        assert q.unit == "dollars"
        # No rate-shaped attributes: this is exactly the gap A2 documents.
        assert not hasattr(q, "numerator_unit")
        assert not hasattr(q, "denominator_unit")

    def test_rate_type_exists_and_models_per_unit_rate(self) -> None:
        # Rate(18, "dollars", "hour") means "18 dollars per hour".
        r = Rate(value=18.0, numerator_unit="dollars", denominator_unit="hour")
        assert r.value == 18.0
        assert r.numerator_unit == "dollars"
        assert r.denominator_unit == "hour"

    def test_sentence_choice_union_excludes_rate(self) -> None:
        # The per-sentence injector contract is
        # ``SentenceChoice = Union[CandidateInitial, CandidateOperation]``.
        # No CandidateRate exists.  This is the load-bearing reason the
        # A2 injector cannot meaningfully emit a rate primitive.
        from generate.math_candidate_parser import CandidateInitial
        from generate.math_roundtrip import CandidateOperation

        # The Union is realised structurally — every SentenceChoice
        # must be one of these two types.  The test pins the closed
        # set; expanding it is the explicit follow-up.
        allowed = {CandidateInitial, CandidateOperation}
        # Best-effort introspection of the Union type.  Python's
        # ``Union`` exposes its members via ``__args__`` on the alias.
        import typing

        args = set(typing.get_args(SentenceChoice))
        assert args == allowed


# ---------------------------------------------------------------------------
# (b) Schema refusal — every shape returns ().
# ---------------------------------------------------------------------------


class TestSchemaRefusal:
    """A2 v1 refuses every input shape, by design."""

    def test_canonical_per_form_refuses(self) -> None:
        m = _make_match((
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "18.00",
                "amount_kind": "decimal",
                "per_unit": "hour",
            },
        ))
        out = inject_rate_with_currency(m, "Tina makes $18.00 an hour.")
        assert out == ()

    def test_canonical_for_form_refuses(self) -> None:
        m = _make_match((
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "30",
                "amount_kind": "integer",
                "per_unit": "hour",
            },
        ))
        out = inject_rate_with_currency(m, "Sam charges $30 for each hour.")
        assert out == ()

    def test_empty_parsed_anchors_refuses(self) -> None:
        # No anchors → no possible state regardless of schema.
        m = _make_match(())
        out = inject_rate_with_currency(m, "Tina makes $18.00 an hour.")
        assert out == ()

    def test_returns_empty_tuple_never_raises(self) -> None:
        # Adversarial input: malformed anchor payload.  The injector
        # MUST NOT raise; it MUST return ``()``.
        m = _make_match(({"kind": "currency_per_unit_rate", "junk": True},))
        out = inject_rate_with_currency(m, "")
        assert out == ()

    def test_injector_never_emits_candidate_initial(self) -> None:
        # Iterate over a spread of shapes; none may admit any candidate.
        sentences = (
            "Tina makes $18.00 an hour.",
            "Sam charges $30 for each hour.",
            "Bob pays $5 per cup.",
            "Alice earns $100 a day.",
        )
        for s in sentences:
            m = _make_match((
                {
                    "kind": "currency_per_unit_rate",
                    "currency_symbol": "$",
                    "amount": "1",
                    "amount_kind": "integer",
                    "per_unit": "hour",
                },
            ))
            assert inject_rate_with_currency(m, s) == ()


# ---------------------------------------------------------------------------
# (c) Dispatch wired — registry routes RATE_WITH_CURRENCY to injector.
# ---------------------------------------------------------------------------


class TestDispatchWired:
    def test_injector_table_registers_rate_with_currency(self) -> None:
        # Before A2: RATE_WITH_CURRENCY was absent from _INJECTORS
        # (default empty-tuple skip).  After A2: present and routed
        # to inject_rate_with_currency.
        assert ShapeCategory.RATE_WITH_CURRENCY in _INJECTORS
        assert _INJECTORS[ShapeCategory.RATE_WITH_CURRENCY] is inject_rate_with_currency

    def test_dispatch_returns_empty_tuple_via_registry(self) -> None:
        m = _make_match((
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "18.00",
                "amount_kind": "decimal",
                "per_unit": "hour",
            },
        ))
        out = inject_from_match(m, "Tina makes $18.00 an hour.")
        assert out == ()

    def test_dispatch_equals_direct_call(self) -> None:
        m = _make_match((
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "18.00",
                "amount_kind": "decimal",
                "per_unit": "hour",
            },
        ))
        s = "Tina makes $18.00 an hour."
        assert inject_from_match(m, s) == inject_rate_with_currency(m, s)


# ---------------------------------------------------------------------------
# (d) Case 0050 hazard pin — sentence_index=0 stays refused.
# ---------------------------------------------------------------------------


_CASES_PATH = (
    Path(__file__).resolve().parent.parent
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "cases.jsonl"
)


def _load_case_0050() -> dict:
    """Look up case 0050 from the fixed eval cases file."""
    with _CASES_PATH.open() as f:
        for line in f:
            c = json.loads(line)
            if c["case_id"] == "gsm8k-train-sample-v1-0050":
                return c
    raise AssertionError("case gsm8k-train-sample-v1-0050 not found in cases.jsonl")


class TestCase0050HazardPin:
    """Case 0050: "Mark does a gig every other day for 2 weeks. ..."

    Sentence 0 carries no currency symbol — rate_with_currency never
    matches it.  Even if A2 v1 emitted state (it doesn't), this case
    would not be reachable through the A2 path.  This test makes the
    invariant explicit so a future A2 widening cannot silently lift
    the case 0050 hazard.
    """

    def test_sentence_zero_has_no_currency_symbol(self) -> None:
        case = _load_case_0050()
        # The case's question text is the full problem; split into
        # sentences on '.' the same way the candidate-graph does.
        sentences = [s.strip() for s in case["question"].split(".") if s.strip()]
        sentence_zero = sentences[0]
        assert "Mark does a gig" in sentence_zero
        for symbol in "$£€¥":
            assert symbol not in sentence_zero

    def test_case_0050_remains_refused_end_to_end(self) -> None:
        case = _load_case_0050()
        r = parse_and_solve(case["question"])
        assert r.answer is None
        # The wrong reading (~3 minutes, per the audit_brief_11 note)
        # MUST never appear.  280 is the correct expected answer; the
        # injector must not regress to either.
        assert r.is_admitted is False


# ---------------------------------------------------------------------------
# (e) Determinism — same input, byte-identical output.
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_injection_is_deterministic(self) -> None:
        m = _make_match((
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "18.00",
                "amount_kind": "decimal",
                "per_unit": "hour",
            },
        ))
        s = "Tina makes $18.00 an hour."
        out1 = inject_rate_with_currency(m, s)
        out2 = inject_rate_with_currency(m, s)
        assert out1 == out2
        assert out1 == ()  # explicitly pinned: refusal

    def test_dispatch_is_deterministic(self) -> None:
        m = _make_match((
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "18.00",
                "amount_kind": "decimal",
                "per_unit": "hour",
            },
        ))
        s = "Tina makes $18.00 an hour."
        out1 = inject_from_match(m, s)
        out2 = inject_from_match(m, s)
        assert out1 == out2


# ---------------------------------------------------------------------------
# (f) Wrong=0 invariant — no candidate is ever produced.
# ---------------------------------------------------------------------------


class TestWrongZeroInvariant:
    """The strongest possible wrong=0 statement: the injector emits
    nothing.  A wider follow-up must replace this assertion with a
    grounded admissibility check on the (Rate, Quantity) composition.
    """

    def test_no_candidate_emitted_for_any_known_shape(self) -> None:
        # Every shape the existing matcher could produce.
        anchor_variants = (
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "18.00",
                "amount_kind": "decimal",
                "per_unit": "hour",
            },
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "5",
                "amount_kind": "integer",
                "per_unit": "cup",
            },
            {
                "kind": "currency_per_unit_rate",
                "currency_symbol": "$",
                "amount": "1/2",
                "amount_kind": "word",
                "per_unit": "pound",
            },
        )
        for anchor in anchor_variants:
            m = _make_match((anchor,))
            out = inject_rate_with_currency(m, "irrelevant under refusal")
            assert out == ()
            assert len(out) == 0
