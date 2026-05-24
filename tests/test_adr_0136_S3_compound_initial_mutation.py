"""ADR-0136.S.3 — compound initial-mutation extractor tests.

Covers: regex matching, closed-verb enforcement, negative-result refusal,
indefinite-quantifier refusal, gsm8k-0010 sentence-1 extraction,
gsm8k-0010 barrier shift, and cross-lane regression gates.
"""

from __future__ import annotations

import json
from pathlib import Path

from generate.math_candidate_parser import (
    _INIT_MUTATION_RE,
    _init_mutation_candidates,
    extract_initial_candidates,
)
from generate.math_candidate_graph import parse_and_solve


class TestInitMutationRegex:
    def test_canonical_subtract(self) -> None:
        assert _INIT_MUTATION_RE.match("Tom had 20 marbles, but then lost 8")

    def test_canonical_add(self) -> None:
        assert _INIT_MUTATION_RE.match("Gina had 10 books, but then gained 5")

    def test_with_initially(self) -> None:
        assert _INIT_MUTATION_RE.match(
            "Yun had 20 paperclips initially, but then lost 12"
        )

    def test_without_then(self) -> None:
        assert _INIT_MUTATION_RE.match("Bob had 30 coins, but lost 10")

    def test_multi_word_verb_gave_away(self) -> None:
        assert _INIT_MUTATION_RE.match("Alice had 15 toys, but then gave away 5")

    def test_multi_word_verb_picked_up(self) -> None:
        assert _INIT_MUTATION_RE.match("Bob had 10 rocks, but then picked up 3")

    def test_non_closed_verb_rejects(self) -> None:
        assert _INIT_MUTATION_RE.match("Bob had 10 balls, but then juggled 5") is None

    def test_non_closed_verb_shuffled(self) -> None:
        assert _INIT_MUTATION_RE.match(
            "Sam had 20 cards, but then shuffled 8"
        ) is None


class TestInitMutationCandidates:
    def test_subtract_produces_correct_value(self) -> None:
        cands = _init_mutation_candidates("Tom had 20 marbles, but then lost 8.")
        assert len(cands) == 1
        assert cands[0].initial.entity == "Tom"
        assert cands[0].initial.quantity.value == 12
        assert cands[0].initial.quantity.unit == "marbles"

    def test_add_produces_correct_value(self) -> None:
        cands = _init_mutation_candidates("Gina had 10 books, but then gained 5.")
        assert len(cands) == 1
        assert cands[0].initial.quantity.value == 15

    def test_negative_result_refuses(self) -> None:
        cands = _init_mutation_candidates("Pat had 10 toys, but then lost 20.")
        assert cands == []

    def test_indefinite_quantifier_refuses(self) -> None:
        cands = _init_mutation_candidates(
            "Bob had several marbles, but then lost 3."
        )
        assert cands == []

    def test_indefinite_mutation_refuses(self) -> None:
        cands = _init_mutation_candidates(
            "Bob had 10 marbles, but then lost some."
        )
        assert cands == []

    def test_closed_verb_miss_refuses(self) -> None:
        cands = _init_mutation_candidates(
            "Rob had 10 balls, but then juggled 5."
        )
        assert cands == []

    def test_gave_away_subtract(self) -> None:
        cands = _init_mutation_candidates(
            "Tina had 80 beads initially, but gave away 33."
        )
        assert len(cands) == 1
        assert cands[0].initial.quantity.value == 47

    def test_picked_up_add(self) -> None:
        cands = _init_mutation_candidates(
            "Bob had 10 rocks, but then picked up 3."
        )
        assert len(cands) == 1
        assert cands[0].initial.quantity.value == 13

    def test_zero_result_allowed(self) -> None:
        cands = _init_mutation_candidates("Bob had 10 balls, but then lost 10.")
        assert len(cands) == 1
        assert cands[0].initial.quantity.value == 0


class TestExtractInitialCandidatesWiring:
    def test_gsm8k_0010_sentence_1(self) -> None:
        cands = extract_initial_candidates(
            "Yun had 20 paperclips initially, but then lost 12."
        )
        assert len(cands) == 1
        assert cands[0].initial.entity == "Yun"
        assert cands[0].initial.quantity.value == 8
        assert cands[0].initial.quantity.unit == "paperclips"


class TestGsm8k0010BarrierShift:
    def test_barrier_shifts_to_sentence_2(self) -> None:
        r = parse_and_solve(
            "Yun had 20 paperclips initially, but then lost 12. "
            "Marion has 1/4 more than what Yun currently has, plus 7. "
            "How many paperclips does Marion have?"
        )
        assert r.answer is None
        assert r.refusal_reason is not None
        assert "Marion" in r.refusal_reason
        assert "1/4" in r.refusal_reason


class TestCrossLaneRegression:
    def test_s3_lane_wrong_is_zero(self) -> None:
        from evals.math_capability_axes.S3_compound_initial_mutation.v1.runner import (
            build_report,
        )

        report = build_report()
        assert report["metrics"]["wrong"] == 0
        assert report["metrics"]["passed"] == report["metrics"]["cases_total"]

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
        assert wrong_count == 0
        required = {
            "gsm8k-train-sample-v1-0014",
            "gsm8k-train-sample-v1-0018",
            "gsm8k-train-sample-v1-0042",
        }
        assert admitted >= required, f"Missing: {required - admitted}"

    def test_s3_deterministic(self) -> None:
        from evals.math_capability_axes.S3_compound_initial_mutation.v1.runner import (
            build_report,
        )

        r1 = json.dumps(build_report(), indent=2, sort_keys=True)
        r2 = json.dumps(build_report(), indent=2, sort_keys=True)
        assert r1 == r2
