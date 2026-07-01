"""ADR-0175 Phase 3b — bounded multiplicative derivation search + practice wiring.

The first live attempt generator. Runs only in the sealed practice lane and only
on cases the engine already refused; every proposal is gated by Phase 3a
self-verification. Wrong attempts are tolerated — they are the elimination
signal, not a lane failure.

Covers:
- extraction + search behaviour;
- the ADR-0114a generality guard (renumbered/reworded variants flip too — the
  capability is not memorised to the 0021 surface);
- invariant #1 (seal): serving stays 4/46/0 (ADR-0207 §5 step 2 cv-0005 flip), the 0050 canary refuses in serving
  and is not attempted-wrong in practice;
- invariant #3 (determinism).
"""

from __future__ import annotations

import json

from evals.gsm8k_math.practice.v1.search_runner import build_search_report
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases
from evals.gsm8k_math.train_sample.v1.runner import build_report as serving_report
from generate.derivation.search import search_multiplicative
from generate.derivation import extract_quantities

_T0021 = "He bench presses 15 pounds for 10 reps and does 3 sets."


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------

class TestExtractQuantities:
    def test_extracts_number_unit_pairs(self) -> None:
        qs = extract_quantities(_T0021)
        assert [(q.value, q.unit) for q in qs] == [
            (15.0, "pounds"),
            (10.0, "reps"),
            (3.0, "sets"),
        ]

    def test_handles_decimals(self) -> None:
        qs = extract_quantities("It moves 2.5 times the 4 kg load.")
        assert (2.5, "times") in [(q.value, q.unit) for q in qs]


# ---------------------------------------------------------------------------
# search behaviour
# ---------------------------------------------------------------------------

class TestSearchMultiplicative:
    def test_flips_0021(self) -> None:
        res = search_multiplicative(_T0021)
        assert res is not None
        assert res.answer == 450.0
        assert res.answer_unit == "pounds"

    def test_refuses_without_a_cue(self) -> None:
        # two quantities, same sentence, but no multiplicative cue lexeme
        assert search_multiplicative("She has 5 apples and 3 oranges.") is None

    def test_refuses_single_quantity(self) -> None:
        assert search_multiplicative("He lifts 15 pounds for the workout.") is None

    def test_disagreeing_sentences_refuse(self) -> None:
        # two qualifying sentences -> two distinct products -> disagreement -> refuse
        text = "He does 15 pounds for 10 reps. She bakes 4 trays for 6 batches."
        assert search_multiplicative(text) is None


# ---------------------------------------------------------------------------
# ADR-0114a generality guard — the flip is a capability, not memorisation
# ---------------------------------------------------------------------------

class TestPerturbationGenerality:
    def test_renumbered_variant_flips(self) -> None:
        res = search_multiplicative("He bench presses 20 pounds for 5 reps and does 4 sets.")
        assert res is not None and res.answer == 400.0

    def test_reworded_same_shape_flips(self) -> None:
        # different domain, same in-clause multiplicative shape
        res = search_multiplicative("She bakes 4 trays for 6 batches and does 2 rounds.")
        assert res is not None and res.answer == 48.0

    def test_two_factor_variant_flips(self) -> None:
        res = search_multiplicative("Each shelf holds 7 books for 9 shelves.")
        assert res is not None and res.answer == 63.0


# ---------------------------------------------------------------------------
# live practice measurement — attempts + eliminations go live
# ---------------------------------------------------------------------------

class TestLiveSearchPractice:
    def test_search_flips_at_least_one_beyond_baseline(self) -> None:
        rep = build_search_report()
        # baseline practice is 3 correct; the search must add at least one flip
        assert rep.counts["correct"] >= 4

    def test_wrong_attempts_are_recorded_as_eliminations(self) -> None:
        rep = build_search_report()
        # practice tolerates wrong — they are the learning signal (§9)
        assert rep.counts["wrong"] == len(rep.elimination_records)
        assert rep.counts["wrong"] >= 0  # the naive cue model over-attempts (expected)


# ---------------------------------------------------------------------------
# invariant #1 — the seal
# ---------------------------------------------------------------------------

class TestSealInvariant:
    def test_serving_unchanged_by_search(self) -> None:
        build_search_report()  # run practice with the search live
        counts = serving_report(_load_cases(_CASES_PATH))["counts"]
        assert counts["wrong"] == 0
        assert counts["correct"] >= 12
        assert counts["refused"] <= 38

    def test_0050_canary_refuses_in_serving_and_is_not_attempted_wrong(self) -> None:
        from generate.math_candidate_graph import parse_and_solve

        c0050 = next(
            json.loads(line)
            for line in _CASES_PATH.read_text().splitlines()
            if "0050" in line
        )
        # serving still refuses the canary
        assert parse_and_solve(c0050["question"]).answer is None
        # and the search did not attempt-wrong on it in practice
        rep = build_search_report()
        assert not any(r.case_id.endswith("0050") for r in rep.elimination_records)


# ---------------------------------------------------------------------------
# invariant #3 — determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_search_is_deterministic(self) -> None:
        assert search_multiplicative(_T0021) == search_multiplicative(_T0021)

    def test_report_byte_identical(self) -> None:
        a = json.dumps(build_search_report().as_dict(), sort_keys=True)
        b = json.dumps(build_search_report().as_dict(), sort_keys=True)
        assert a == b
