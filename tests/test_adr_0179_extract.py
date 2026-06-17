"""ADR-0179 — extraction richness tests (sealed lane: generate/derivation/extract).

Integration of the EX-1 (word-numbers), EX-4 (list-unit inheritance), and EX-5
(sentence-final numbers) sub-phases. EX-3 (multi-word units) is deferred — see
the module docstring and docs/handoff/AUDIT-ADR-0179-EX-RECONCILE.md — so there
is no multi-word-unit test class here by design.

Every assertion is a plain input-string → extracted-quantity check. Over-extraction
in this lane costs refusals (the gate is refuse-preferring), never wrong answers.
"""

from __future__ import annotations

from generate.derivation import extract_quantities


def _triples(text: str) -> list[tuple[float, str, str]]:
    return [(q.value, q.unit, q.source_token) for q in extract_quantities(text)]


class TestEX1WordNumbers:
    def test_word_number_extracts_as_quantity(self) -> None:
        assert _triples("She picked three apples.") == [(3.0, "apples", "three")]

    def test_digit_and_word_numbers_extract_left_to_right(self) -> None:
        assert _triples("She picked 2 apples and three oranges.") == [
            (2.0, "apples", "2"),
            (3.0, "oranges", "three"),
        ]

    def test_hyphenated_tens_one_compound(self) -> None:
        assert _triples("The team scored twenty-four points.") == [
            (24.0, "points", "twenty-four"),
        ]

    def test_non_tens_one_compound_is_not_guessed(self) -> None:
        # "one-third" is not a tens-one compound; the resolver declines the whole
        # hyphen match rather than invent a composition rule (no fraction support,
        # no fall-back to "one" alone). Conservative: nothing extracted.
        assert _triples("He ate one-third pizza.") == []

    def test_factor_words_are_not_extracted_as_counts(self) -> None:
        # half/third/quarter read as divisors, not counts — excluded from EX-1.
        assert _triples("She drank half cup.") == []


class TestEX4ListUnitInheritance:
    def test_trailing_unit_attaches_to_every_number_in_list(self) -> None:
        qs = extract_quantities("20, 36, 40 and 50 push-ups")
        assert [q.value for q in qs] == [20.0, 36.0, 40.0, 50.0]
        assert [q.unit for q in qs] == ["push-ups"] * 4
        assert [q.source_token for q in qs] == ["20", "36", "40", "50"]

    def test_left_to_right_order_with_surrounding_quantities(self) -> None:
        assert _triples("She had 2 bags, then did 20, 36 and 40 reps.") == [
            (2.0, "bags", "2"),
            (20.0, "reps", "20"),
            (36.0, "reps", "36"),
            (40.0, "reps", "40"),
        ]

    def test_list_numbers_not_double_counted(self) -> None:
        # the trailing number's "50 push-ups" must not also surface via the
        # single-unit pass.
        qs = extract_quantities("20, 36, 40 and 50 push-ups")
        assert len(qs) == 4


class TestEX5SentenceFinalNumbers:
    def test_sentence_final_number_extracts_with_empty_unit(self) -> None:
        assert _triples("She had 5.") == [(5.0, "", "5")]

    def test_question_final_number_extracts_with_empty_unit(self) -> None:
        assert _triples("The answer is 7?") == [(7.0, "", "7")]

    def test_unit_quantity_and_final_number_extract_left_to_right(self) -> None:
        assert _triples("She picked 6 apples and had 4.") == [
            (6.0, "apples", "6"),
            (4.0, "", "4"),
        ]

    def test_number_with_unit_is_not_duplicated_as_final_number(self) -> None:
        assert _triples("She picked 6 apples.") == [(6.0, "apples", "6")]


class TestNoRegression:
    def test_simple_digit_units_still_work(self) -> None:
        assert _triples("She picked 6 apples and 4 apples.") == [
            (6.0, "apples", "6"),
            (4.0, "apples", "4"),
        ]

    def test_decimal_value_preserved(self) -> None:
        assert _triples("It costs 0.75 dollars.") == [(0.75, "dollars", "0.75")]


class TestEX6HyphenatedUnitNumbers:
    """ADR-0163-F2 — hyphen-bonded number-unit tokens (``25-foot``, ``20-inch``).

    The base ``_QTY_RE`` requires ``number + whitespace + unit word``, so a number
    bonded to its unit by a hyphen (``25-foot sections``, ``20-inch pieces``) was
    invisible — the very blind spot behind the pseudo-accumulation confusers
    (0005 ``→796``, 0007 ``→996``): the completeness clause could not see the
    ``25``/``20`` divisor, so the accumulation reading was wrongly "complete".

    This is a tight, ADR-0165-safe lexeme pattern (digit run, a hyphen, an
    alphabetic unit word) — strictly distinct from the deferred EX-3 multi-word
    *space-separated* unit problem. Over-extraction here only costs refusals
    (the gate is refuse-preferring), never a wrong answer.
    """

    def test_hyphen_bonded_unit_extracts_value_and_unit(self) -> None:
        assert _triples("She cuts it into 20-inch pieces.") == [(20.0, "inch", "20")]

    def test_hyphen_bonded_unit_mid_sentence(self) -> None:
        assert _triples("She splits it into 25-foot sections.") == [(25.0, "foot", "25")]

    def test_decimal_hyphen_bonded_unit(self) -> None:
        assert _triples("He ran a 2.5-mile loop.") == [(2.5, "mile", "2.5")]

    def test_hyphen_unit_not_double_counted_as_final_number(self) -> None:
        # the hyphen pass claims the digit span; the bare-final pass must not
        # also surface "25" with an empty unit.
        assert len(extract_quantities("It was 25-foot.")) == 1

    def test_word_compound_still_takes_word_number_path(self) -> None:
        # digit-hyphen is a different lexeme from the EX-1 word-word compound;
        # "twenty-four" must still resolve via the word-number path, unaffected.
        assert _triples("The team scored twenty-four points.") == [
            (24.0, "points", "twenty-four"),
        ]

    def test_numeric_range_is_not_read_as_unit(self) -> None:
        # "3-5" is digit-hyphen-DIGIT; the unit group requires letters, so the
        # hyphen pass must not fire and invent a unit from the second number.
        assert all(q.unit != "5" for q in extract_quantities("Pick 3-5 apples."))


class TestSlashFractionLeakHazard:
    """Honest pin (deferred hazard): a slash-fraction leaks its denominator.

    ``"gives 1/4 to a friend"`` extracts the bare ``4`` (the base ``_QTY_RE``
    sees ``4`` + space + the function-word ``to``, blanks the unit, and emits a
    standalone quantity ``4``). This is a grounded-but-wrong operand — it is the
    second half of the pseudo-accumulation misfire (``1000 - 4 = 996``).

    It is **not** fixed in this PR on purpose. Suppressing the leaked ``4`` *removes*
    a quantity, which can *unblock* the completeness clause (a derivation that was
    "incomplete" because it ignored the spurious ``4`` could become "complete" and
    commit) — i.e. the fix is not unambiguously refuse-preferring and needs its own
    train_sample + probe validation. The hyphen-unit pass (TestEX6) already drives
    confusers 0005/0007 to *refuse* via the polarity-None ``cuts``/``splits`` clause,
    so this leak is currently dormant behind that refusal. This test pins the leak
    so a future fraction-operand PR addresses it deliberately, not by accident.
    """

    def test_slash_fraction_denominator_currently_leaks(self) -> None:
        # documents current (leaky) behavior — flip this when fractions are modeled.
        assert (4.0, "", "4") in _triples("She gives 1/4 to a friend.")


class TestEX3StillDeferred:
    """Honest pin: EX-3 (multi-word units) remains deferred after the Track C redo.

    The brief in ``docs/handoff/PARALLEL-WORK-PLAN-2026-05-29.md`` Track C asked
    for a *tight* rule satisfying:

    * (a) ``"12 jumping jacks."`` → unit ``"jumping jacks"`` only where tight;
    * (b) ``"6 apples and 4 apples."`` → two ``apples`` quantities (not
      ``"apples and"``);
    * (c) all GB-1/GB-2/GB-3 tests stay green;

    plus the plan's global rule that *no currently-green test* be regressed.

    A candidate rule —
    ``(?<![\\w.])(\\d+(?:\\.\\d+)?)\\s+([a-z]+\\s+[a-z]+)(?=\\s*[.?!,]|\\s*$)``
    — satisfies (a)+(b)+(c) against the four listed test files but **regresses
    a different green test**: ``test_adr_0176_ms1_question_target.py
    ::TestQuestionQuantities::test_extracts_quantity_stated_in_question``,
    which pins ``"25 years old?"`` → unit ``"years"``. The candidate rule fires
    on ``"25 years old"`` and produces unit ``"years old"`` — and the
    postmodifier-adjective tail (``"old"`` / ``"tall"`` / ``"long"`` / ``"wide"``
    / ``"away"`` / ``"ago"`` / …) is endemic in GSM8K (cases 0006, 0033 and
    several MS2 chain tests all use ``"X years old"``).

    The audit at ``docs/handoff/AUDIT-ADR-0179-EX-RECONCILE.md`` named the first
    trap (connective-crossing). This pin names the second one
    (postmodifier-adjective tails), so the deferred status of EX-3 is owned by
    *both* known traps and a future redo cannot silently land without addressing
    them.

    These assertions hold against the *current* (no-EX-3) extractor. Any patch
    that introduces a multi-word-unit pass without also blocking postmodifier
    tails will flip them — that is the point.
    """

    def test_postmodifier_adjective_does_not_inflate_unit_to_two_words(self) -> None:
        # The trap. Naive tight EX-3 produces "years old"; the correct unit is
        # "years" alone.
        qs = extract_quantities("How old will the father be when she is 25 years old?")
        assert [(q.value, q.unit) for q in qs] == [(25.0, "years")]

    def test_postmodifier_trap_present_for_full_sentence_form_too(self) -> None:
        # The same trap with a period instead of a question mark, paralleling
        # ``"Rachel is 12 years old."`` from GSM8K case 0033 / the MS2 chain tests.
        qs = extract_quantities("Rachel is 12 years old.")
        assert qs[0].value == 12.0
        assert qs[0].unit == "years"


class TestRealCase0024StillBlocked:
    """Honest pin: the EX-4 unit-list pattern does NOT recover real case 0024.

    The actual gold text interleaves numbers with temporal phrases
    ("36 on Tuesday, 40 on Wednesday"), so the bare-list regex never fires and the
    36/40/50 do not inherit "jumping jacks". This test documents the current
    boundary so no future change silently claims 0024 is "unblocked" without
    proving the (20+36+40+50)*3 = 438 chain end-to-end.
    """

    def test_only_first_number_carries_the_unit(self) -> None:
        qs = extract_quantities(
            "Sidney does 20 jumping jacks on Monday, 36 on Tuesday, "
            "40 on Wednesday, and 50 on Thursday."
        )
        values = [q.value for q in qs]
        assert values == [20.0, 36.0, 40.0, 50.0]
        # 20 keeps a unit word; the bare 36/40/50 do not inherit "jumping" — they
        # are sentence-internal, not a bare comma-list, so EX-4 cannot reach them.
        units = [q.unit for q in qs]
        assert units[0] == "jumping"
        assert len(set(units)) > 1  # NOT a same-unit list -> compose refuses


class TestWorkstreamAReaderLexemeOnly:
    """Direct tests for the Workstream A lexeme-only passes (fraction/comparative).

    Per CLAUDE.md schema-proof rule and the ratified scope: the new behavior
    (surfacing component lexemes for "half of", "X/Y of", "X more/less than")
    must be provably exercised by tests that would fail under violation
    (e.g. synthesizing non-surface source_tokens or performing composition).
    """

    def test_half_of_surfaces_surface_lexeme_source(self) -> None:
        # "half" is the surface lexeme; value 0.5 is convenience, source_token preserves the casing from the input text (as with other EX passes).
        triples = _triples("Half of the kids are going to soccer camp.")
        assert any(v == 0.5 and u == "kids" and s.lower() == "half" for (v, u, s) in triples)

    def test_fraction_of_surfaces_surface_fraction_source(self) -> None:
        # "3/4" is the surface form in the text.
        triples = _triples('In one hour, Addison mountain\'s temperature will decrease to 3/4 of its temperature.')
        assert any(v == 0.75 and "3/4" in s for (v, u, s) in triples)

    def test_more_than_surfaces_two_components_no_synthesis(self) -> None:
        # Must surface the two numbers that appear ("2", "5"); never a synthesized "7.0".
        triples = _triples("On Rudolph's car trip across town, he traveled 2 more than 5 miles.")
        sources = [s for (v, u, s) in triples]
        assert "2" in sources and "5" in sources
        assert "7.0" not in sources and "7" not in sources

    def test_less_than_surfaces_components_no_clamp_synthesis(self) -> None:
        triples = _triples('On Rudolph\'s car trip across town, he traveled 2 more than 5 miles and encountered 3 less than 17 stop signs.')
        sources = [s for (v, u, s) in triples]
        assert "3" in sources and "17" in sources
        assert all(s not in ("14.0", "14", "0") for s in sources)  # no synthesis or clamp in extract

    def test_source_tokens_are_surface_text(self) -> None:
        # All source_tokens for the new phrases must be literal substrings of the input.
        text = "2 more than 5 miles and 3 less than 17 stop signs and half of the kids and 3/4 of the group."
        for q in extract_quantities(text):
            assert q.source_token in text or q.source_token == ""
