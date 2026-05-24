"""ADR-0136.S.1 — Rate/event statement parsing axis lane tests.

Pins the closed capacity-verb and earnings-verb vocabularies and the
end-to-end ``parse_and_solve`` short-circuit paths for capacity-rate
and earnings-rate shapes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.math_capability_axes.S1_rate_events.v1.runner import build_report
from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import (
    _CAPACITY_RE,
    _CAPACITY_VERBS,
    _EARNINGS_RE,
    _EARNINGS_VERBS,
    _to_seconds,
    classify_sentence,
    extract_capacity_candidates,
    extract_capacity_question_candidates,
    extract_earnings_candidates,
    extract_earnings_question_candidates,
    has_numeric_token,
)

_REPO = Path(__file__).resolve().parent.parent
_GSM8K_CG_REPORT = _REPO / "evals/gsm8k_math/train_sample/v1/report.json"


# ── Regex vocabulary tests ──────────────────────────────────────────


class TestCapacityRegex:
    @pytest.mark.parametrize("verb", ["shuck", "pick", "pack", "make", "type", "read", "write", "paint"])
    def test_canonical_verb_matches(self, verb: str) -> None:
        sentence = f"Bob can {verb} 10 apples in 5 minutes."
        cands = extract_capacity_candidates(sentence)
        assert len(cands) == 1, f"no candidate for verb {verb!r}"
        assert cands[0].actor == "Bob"
        assert cands[0].count == 10.0

    @pytest.mark.parametrize("verb", ["juggle", "knit", "solve", "bake", "eat", "swim"])
    def test_closed_verb_miss_refuses(self, verb: str) -> None:
        sentence = f"Bob can {verb} 10 balls in 5 minutes."
        cands = extract_capacity_candidates(sentence)
        assert cands == [], f"verb {verb!r} should not match"


class TestEarningsRegex:
    @pytest.mark.parametrize(
        "sentence",
        [
            "Tina makes $18.00 an hour.",
            "Bob earns $25.00 per hour.",
            "Alice receives $12.50 per hour.",
        ],
    )
    def test_earnings_shapes_match(self, sentence: str) -> None:
        cands = extract_earnings_candidates(sentence)
        assert len(cands) == 1, f"no candidate for {sentence!r}"
        assert cands[0].unit == "dollar"

    def test_for_each_pattern(self) -> None:
        cands = extract_earnings_candidates("Sam charges $30.00 for each hour.")
        assert len(cands) == 1
        assert cands[0].amount == 30.0

    def test_every_pattern(self) -> None:
        cands = extract_earnings_candidates("Bob gets $15.00 every hour.")
        assert len(cands) == 1
        assert cands[0].amount == 15.0


# ── Time conversion ─────────────────────────────────────────────────


class TestTimeConversion:
    def test_minutes_to_hours(self) -> None:
        assert _to_seconds(1, "minute") == 60.0
        assert _to_seconds(1, "hour") == 3600.0
        assert _to_seconds(2, "hours") == 7200.0

    def test_seconds_to_minutes(self) -> None:
        assert _to_seconds(1, "second") == 1.0
        assert _to_seconds(60, "seconds") == 60.0
        assert _to_seconds(1, "minutes") == 60.0


# ── End-to-end parse_and_solve tests ─────────────────────────────────


class TestGSM8K0014:
    def test_gsm8k_0014_admits_240(self) -> None:
        r = parse_and_solve(
            "Bob can shuck 10 oysters in 5 minutes.  "
            "How many oysters can he shuck in 2 hours?"
        )
        assert r.answer == 240.0
        assert r.refusal_reason is None


class TestCapacityEndToEnd:
    def test_same_unit(self) -> None:
        r = parse_and_solve(
            "Alice can pick 12 apples in 3 minutes.  "
            "How many apples can Alice pick in 9 minutes?"
        )
        assert r.answer == 36.0

    def test_cross_unit(self) -> None:
        r = parse_and_solve(
            "Sam can pack 15 boxes in 5 minutes.  "
            "How many boxes can Sam pack in 2 hours?"
        )
        assert r.answer == 360.0

    def test_pronoun_question(self) -> None:
        r = parse_and_solve(
            "Bob can shuck 10 oysters in 5 minutes.  "
            "How many oysters can he shuck in 30 minutes?"
        )
        assert r.answer == 60.0


class TestEarningsEndToEnd:
    def test_tina_simplified(self) -> None:
        r = parse_and_solve(
            "Tina makes $18.00 an hour.  "
            "How much money does Tina make in 5 hours?"
        )
        assert r.answer == 90.0

    def test_earns_per_hour(self) -> None:
        r = parse_and_solve(
            "Bob earns $25.00 per hour.  "
            "How much money does Bob earn in 8 hours?"
        )
        assert r.answer == 200.0


class TestActorMismatchRefusal:
    def test_capacity_actor_mismatch_refuses(self) -> None:
        r = parse_and_solve(
            "Bob can shuck 10 oysters in 5 minutes.  "
            "How many oysters can Alice shuck in 2 hours?"
        )
        assert r.answer is None
        assert "actor mismatch" in (r.refusal_reason or "")

    def test_earnings_actor_mismatch_refuses(self) -> None:
        r = parse_and_solve(
            "Tina makes $18.00 an hour.  "
            "How much money does Bob make in 5 hours?"
        )
        assert r.answer is None
        assert "actor mismatch" in (r.refusal_reason or "")


# ── Axis lane gate ───────────────────────────────────────────────────


class TestAxisLaneGate:
    def test_wrong_is_zero(self) -> None:
        report = build_report()
        assert report["metrics"]["wrong"] == 0
        assert report["metrics"]["wrong_count_is_zero"] is True

    def test_report_byte_equal_across_runs(self) -> None:
        r1 = build_report()
        r2 = build_report()
        s1 = json.dumps(r1, indent=2, sort_keys=True)
        s2 = json.dumps(r2, indent=2, sort_keys=True)
        assert s1 == s2

    def test_all_categories_present(self) -> None:
        report = build_report()
        expected_cats = {
            "capacity_same_unit",
            "capacity_cross_unit",
            "capacity_pronoun",
            "earnings_same_unit",
            "refusal_verb_miss",
        }
        assert set(report["per_category"].keys()) == expected_cats


# ── B3 regression guard ──────────────────────────────────────────────


def test_b3_lane_still_passes() -> None:
    from evals.math_bounded_grammar.v1.runner import build_report as b3_build, load_cases

    cases_path = _REPO / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
    report = b3_build(load_cases(cases_path))
    assert report["metrics"]["wrong"] == 0, (
        f"B3 lane regression: wrong={report['metrics']['wrong']}"
    )


# ── GSM8K safety rail ────────────────────────────────────────────────


def test_gsm8k_candidate_graph_admitted_wrong_zero() -> None:
    """Post-S.1: re-run GSM8K candidate-graph probe; wrong must stay 0."""
    data = json.loads(_GSM8K_CG_REPORT.read_text(encoding="utf-8"))
    assert data["counts"]["wrong"] == 0


def test_gsm8k_post_s1_admission_honest() -> None:
    """Honest admission delta: exactly 1 newly admitted (gsm8k-0014)."""
    import re as _re

    cases = [
        json.loads(line)
        for line in (
            _REPO / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    admitted = []
    for c in cases:
        r = parse_and_solve(c["question"])
        if r.answer is not None:
            admitted.append(c["case_id"])
            assert r.answer == c["answer_numeric"], (
                f"{c['case_id']}: answer {r.answer} != expected {c['answer_numeric']}"
            )
    assert len(admitted) >= 1, "gsm8k-0014 should admit"
    assert "gsm8k-train-sample-v1-0014" in admitted


# ── ADR-0136.S.0 — Context-sentence classifier ───────────────────────


class TestContextClassifier:
    @pytest.mark.parametrize("sentence", [
        "Jason has a carriage house that he rents out.",
        "Xavier plays football with his friends.",
        "Marnie makes bead bracelets.",
        "John decides to take up illustration.",
        "Sandra wants to buy some sweets.",
    ])
    def test_no_digit_sentences_classified_context(self, sentence: str) -> None:
        assert not has_numeric_token(sentence)
        assert classify_sentence(sentence) == "context"

    @pytest.mark.parametrize("sentence", [
        "Bob can shuck 10 oysters in 5 minutes.",
        "During 15 minutes Xavier can score 2 goals on average.",
        "Francine has five full boxes of crayons and 5 loose crayons.",
        "Tina makes $18.00 an hour.",
    ])
    def test_numeric_sentences_classified_numeric_state(self, sentence: str) -> None:
        assert has_numeric_token(sentence)
        assert classify_sentence(sentence) == "numeric_state"

    def test_gsm8k_0018_context_sentence_skipped_admits(self) -> None:
        """Context gate removed: gsm8k-0018 admits with answer 16."""
        q = (
            "Xavier plays football with his friends. "
            "During 15 minutes Xavier can score 2 goals on average. "
            "How many goals on average is Xavier able to score, "
            "when the match lasted for 2 hours?"
        )
        r = parse_and_solve(q)
        assert r.answer == 16.0, f"expected 16.0 got {r.answer} ({r.refusal_reason})"

    def test_inverted_capacity_pattern_matches(self) -> None:
        """Shape A2: 'During M <time-unit> <Actor> can <verb> N <unit>'."""
        cands = extract_capacity_candidates(
            "During 15 minutes Xavier can score 2 goals on average."
        )
        assert len(cands) == 1
        assert cands[0].count == 2.0
        assert cands[0].per_count == 15.0
        assert cands[0].per_unit == "minutes"

    def test_all_context_sentences_refused_when_no_numeric_follows(self) -> None:
        """A problem with only context sentences and no numeric state refuses."""
        r = parse_and_solve(
            "Jason has a carriage house. How many houses does Jason rent?"
        )
        assert r.answer is None
        assert r.refusal_reason is not None
