"""ADR-0136.S.4 — novel-initial-form extractor tests.

Covers: regex matching for Shape A (indefinite-article subject) and
Shape B (prepositional-prefix existential), closed-grammar refusal,
indefinite-quantifier refusal, gsm8k-0046 and gsm8k-0038 sentence-1
extraction, barrier-shift evidence for both GSM8K cases, and
cross-lane regression gates.
"""

from __future__ import annotations

import json
from pathlib import Path

from generate.math_candidate_parser import (
    _INITIAL_HAS_INDEF_RE,
    _INITIAL_THERE_ARE_PREFIX_RE,
    _init_has_indef_candidates,
    _init_there_are_prefix_candidates,
    extract_initial_candidates,
)
from generate.math_candidate_graph import parse_and_solve


# ---------------------------------------------------------------------------
# Shape A regex — _INITIAL_HAS_INDEF_RE
# ---------------------------------------------------------------------------

class TestInitHasIndefRegex:
    def test_canonical(self) -> None:
        m = _INITIAL_HAS_INDEF_RE.match("A school has 100 students")
        assert m is not None
        assert m.group("noun") == "school"
        assert m.group("value") == "100"
        assert m.group("unit") == "students"

    def test_lowercase_a(self) -> None:
        m = _INITIAL_HAS_INDEF_RE.match("a factory has 50 workers")
        assert m is not None
        assert m.group("noun") == "factory"

    def test_substance_qualifier(self) -> None:
        m = _INITIAL_HAS_INDEF_RE.match("A bin has 40 cans of soda")
        assert m is not None
        assert m.group("noun") == "bin"
        assert m.group("unit") == "cans"

    def test_with_trailing_period(self) -> None:
        m = _INITIAL_HAS_INDEF_RE.match("A school has 100 students.")
        assert m is not None

    def test_word_number_value(self) -> None:
        m = _INITIAL_HAS_INDEF_RE.match("A farm has thirty cows")
        assert m is not None
        assert m.group("value") == "thirty"

    def test_definite_article_not_matched(self) -> None:
        # "The school has" must NOT match _INITIAL_HAS_INDEF_RE
        assert _INITIAL_HAS_INDEF_RE.match("The school has 100 students") is None

    def test_proper_noun_not_matched(self) -> None:
        # "Alice has" must NOT match — goes through _INITIAL_HAS_RE
        assert _INITIAL_HAS_INDEF_RE.match("Alice has 100 marbles") is None

    def test_an_not_matched(self) -> None:
        # "An apple" — "An" starts with [Aa] then 'n', not whitespace → no match
        assert _INITIAL_HAS_INDEF_RE.match("An apple has 10 seeds") is None


# ---------------------------------------------------------------------------
# Shape B regex — _INITIAL_THERE_ARE_PREFIX_RE
# ---------------------------------------------------------------------------

class TestInitThereArePrefixRegex:
    def test_canonical(self) -> None:
        m = _INITIAL_THERE_ARE_PREFIX_RE.match("In a building, there are 100 ladies")
        assert m is not None
        assert m.group("place") == "building"
        assert m.group("value") == "100"
        assert m.group("unit") == "ladies"

    def test_with_article_before_word_number(self) -> None:
        # "a hundred" — "a" is consumed by (?:a\s+)?; value="hundred"
        m = _INITIAL_THERE_ARE_PREFIX_RE.match(
            "In a building, there are a hundred ladies on the first-floor studying"
        )
        assert m is not None
        assert m.group("place") == "building"
        assert m.group("value") == "hundred"
        assert m.group("unit") == "ladies"

    def test_ordinal_floor_only(self) -> None:
        m = _INITIAL_THERE_ARE_PREFIX_RE.match(
            "In a library, there are 50 books on the second-floor"
        )
        assert m is not None
        assert m.group("place") == "library"

    def test_ordinal_floor_with_participial(self) -> None:
        m = _INITIAL_THERE_ARE_PREFIX_RE.match(
            "In a library, there are 50 books on the second-floor shelving"
        )
        assert m is not None
        assert m.group("unit") == "books"

    def test_no_comma(self) -> None:
        m = _INITIAL_THERE_ARE_PREFIX_RE.match("In a gym there are 30 students")
        assert m is not None

    def test_bare_there_are_not_matched(self) -> None:
        # Plain "There are" must NOT match _INITIAL_THERE_ARE_PREFIX_RE
        assert _INITIAL_THERE_ARE_PREFIX_RE.match("There are 100 ladies in a building") is None

    def test_uppercase_in(self) -> None:
        m = _INITIAL_THERE_ARE_PREFIX_RE.match("In a warehouse, there are 200 boxes")
        assert m is not None
        assert m.group("place") == "warehouse"


# ---------------------------------------------------------------------------
# Shape A extractor — _init_has_indef_candidates
# ---------------------------------------------------------------------------

class TestInitHasIndefCandidates:
    def test_canonical_produces_correct_initial(self) -> None:
        cands = _init_has_indef_candidates("A school has 100 students.")
        assert len(cands) == 1
        assert cands[0].initial.entity == "school"
        assert cands[0].initial.quantity.value == 100
        assert cands[0].initial.quantity.unit == "students"

    def test_entity_is_lowercased(self) -> None:
        cands = _init_has_indef_candidates("A School has 50 chairs.")
        assert len(cands) == 1
        assert cands[0].initial.entity == "school"

    def test_substance_qualifier_discarded(self) -> None:
        cands = _init_has_indef_candidates("A bin has 40 cans of soda.")
        assert len(cands) == 1
        assert cands[0].initial.quantity.unit == "cans"
        assert cands[0].initial.quantity.value == 40

    def test_indefinite_quantifier_refuses(self) -> None:
        cands = _init_has_indef_candidates("A school has some students.")
        assert cands == []

    def test_missing_unit_refuses(self) -> None:
        cands = _init_has_indef_candidates("A school has 100.")
        assert cands == []

    def test_definite_article_not_handled(self) -> None:
        # "The school has" is NOT for this extractor (goes through _INITIAL_HAS_RE)
        cands = _init_has_indef_candidates("The school has 100 students.")
        assert cands == []

    def test_matched_anchor_is_has(self) -> None:
        cands = _init_has_indef_candidates("A library has 200 books.")
        assert len(cands) == 1
        assert cands[0].matched_anchor == "has"


# ---------------------------------------------------------------------------
# Shape B extractor — _init_there_are_prefix_candidates
# ---------------------------------------------------------------------------

class TestInitThereArePrefixCandidates:
    def test_canonical(self) -> None:
        cands = _init_there_are_prefix_candidates("In a building, there are 100 ladies.")
        assert len(cands) == 1
        assert cands[0].initial.entity == "building"
        assert cands[0].initial.quantity.value == 100
        assert cands[0].initial.quantity.unit == "ladies"

    def test_word_number_with_article(self) -> None:
        cands = _init_there_are_prefix_candidates(
            "In a building, there are a hundred ladies on the first-floor studying."
        )
        assert len(cands) == 1
        assert cands[0].initial.entity == "building"
        assert cands[0].initial.quantity.value == 100
        assert cands[0].initial.quantity.unit == "ladies"

    def test_ordinal_and_participial_discarded(self) -> None:
        cands = _init_there_are_prefix_candidates(
            "In a library, there are 50 books on the second-floor shelving."
        )
        assert len(cands) == 1
        assert cands[0].initial.quantity.value == 50
        assert cands[0].initial.quantity.unit == "books"

    def test_place_is_lowercased(self) -> None:
        cands = _init_there_are_prefix_candidates("In a Building, there are 30 chairs.")
        assert len(cands) == 1
        assert cands[0].initial.entity == "building"

    def test_indefinite_quantifier_refuses(self) -> None:
        cands = _init_there_are_prefix_candidates("In a building, there are several ladies.")
        assert cands == []

    def test_matched_anchor_is_are(self) -> None:
        cands = _init_there_are_prefix_candidates("In a gym, there are 30 students.")
        assert len(cands) == 1
        assert cands[0].matched_anchor == "are"


# ---------------------------------------------------------------------------
# Wiring — extract_initial_candidates dispatches both shapes
# ---------------------------------------------------------------------------

class TestExtractInitialCandidatesWiring:
    def test_gsm8k_0046_sentence_1(self) -> None:
        cands = extract_initial_candidates("A school has 100 students.")
        assert len(cands) == 1
        assert cands[0].initial.entity == "school"
        assert cands[0].initial.quantity.value == 100
        assert cands[0].initial.quantity.unit == "students"

    def test_gsm8k_0038_sentence_1(self) -> None:
        cands = extract_initial_candidates(
            "In a building, there are a hundred ladies on the first-floor studying."
        )
        assert len(cands) == 1
        assert cands[0].initial.entity == "building"
        assert cands[0].initial.quantity.value == 100
        assert cands[0].initial.quantity.unit == "ladies"

    def test_definite_article_still_uses_existing_path(self) -> None:
        # "The school has 100 students." must still produce an initial (via _INITIAL_HAS_RE)
        cands = extract_initial_candidates("The school has 100 students.")
        assert len(cands) == 1
        assert "school" in cands[0].initial.entity  # entity is "the school"

    def test_no_double_extraction_shape_a(self) -> None:
        # Shape A and existing _INITIAL_HAS_RE must not both fire on the same sentence.
        # "Alice has 100 marbles." → only _INITIAL_HAS_RE fires (proper noun).
        cands = extract_initial_candidates("Alice has 100 marbles.")
        assert len(cands) == 1
        assert cands[0].initial.entity == "Alice"

    def test_no_double_extraction_shape_b(self) -> None:
        # "There are 100 ladies in a building." → only _INITIAL_THERE_ARE_RE fires
        # (starts with "There", not "In a"). The existing path captures place as
        # "a building" (multi-word) since _INITIAL_THERE_ARE_RE's place group
        # allows a leading article; _INITIAL_THERE_ARE_PREFIX_RE does not fire.
        cands = extract_initial_candidates("There are 100 ladies in a building.")
        assert len(cands) == 1
        assert "building" in cands[0].initial.entity  # "a building" from existing path


# ---------------------------------------------------------------------------
# GSM8K barrier-shift evidence
# ---------------------------------------------------------------------------

class TestGsm8kBarrierShifts:
    def test_gsm8k_0046_graduated_via_partition(self) -> None:
        # GRADUATED (ADR-0190): the fraction_operand barrier that once
        # refused sentence 2 ("Half of the students are girls…") is resolved
        # by the partition operation. 0046 now reads as a chain of fractional
        # partitions (students→girls→dogs) and SOLVES to 15 — the first
        # fraction flip (serving 4/46/0 → 5/45/0, wrong=0 preserved).
        r = parse_and_solve(
            "A school has 100 students. "
            "Half of the students are girls, the other half are boys.  "
            "20% of the girls have dogs at home and 10% of the boys have dogs at home.  "
            "How many students own dogs?"
        )
        assert r.answer == 15.0
        assert r.refusal_reason is None

    def test_gsm8k_0038_barrier_shifts_to_sentence_2(self) -> None:
        # Sentence 1 extracts cleanly (In a building, there are a hundred ladies...).
        # Sentence 2 "There are three times that many girls..." is compound_comparative → refusal.
        r = parse_and_solve(
            "In a building, there are a hundred ladies on the first-floor studying. "
            "There are three times that many girls at a party being held on the second "
            "floor of the building. "
            "How many ladies are on the two floors in total?"
        )
        assert r.answer is None
        assert r.refusal_reason is not None
        assert "three" in r.refusal_reason or "girls" in r.refusal_reason or "times" in r.refusal_reason


# ---------------------------------------------------------------------------
# Cross-lane regression gates
# ---------------------------------------------------------------------------

class TestCrossLaneRegression:
    def test_s4_lane_wrong_is_zero(self) -> None:
        from evals.math_capability_axes.S4_novel_initial_form.v1.runner import build_report

        report = build_report()
        assert report["metrics"]["wrong"] == 0
        assert report["metrics"]["passed"] == report["metrics"]["cases_total"]

    def test_s4_deterministic(self) -> None:
        from evals.math_capability_axes.S4_novel_initial_form.v1.runner import build_report

        r1 = json.dumps(build_report(), indent=2, sort_keys=True)
        r2 = json.dumps(build_report(), indent=2, sort_keys=True)
        assert r1 == r2

    def test_s3_lane_wrong_is_zero(self) -> None:
        from evals.math_capability_axes.S3_compound_initial_mutation.v1.runner import build_report

        report = build_report()
        assert report["metrics"]["wrong"] == 0

    def test_s1_lane_wrong_is_zero(self) -> None:
        from evals.math_capability_axes.S1_rate_events.v1.runner import build_report

        report = build_report()
        assert report["metrics"]["wrong"] == 0

    def test_gsm8k_admission_superset(self) -> None:
        cases_path = Path("evals/gsm8k_math/train_sample/v1/cases.jsonl")
        cases = [
            json.loads(line)
            for line in cases_path.read_text().splitlines()
            if line.strip()
        ]
        admitted = set()
        wrong_count = 0
        for c in cases:
            r = parse_and_solve(c["question"])
            if r.answer is not None:
                if r.answer == c["answer_numeric"]:
                    admitted.add(c["case_id"])
                else:
                    wrong_count += 1
        assert wrong_count == 0, f"wrong answers introduced: {wrong_count}"
        required = {
            "gsm8k-train-sample-v1-0014",
            "gsm8k-train-sample-v1-0018",
            "gsm8k-train-sample-v1-0042",
        }
        assert admitted >= required, f"Missing: {required - admitted}"
