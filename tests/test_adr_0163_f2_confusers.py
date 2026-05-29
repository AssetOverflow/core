"""ADR-0163-F2 — confuser corpus discrimination probe.

The corpus is scored opposite to a coverage lane: the bar is ``wrong`` trending to
0, and the genuine-positive twins solving. These tests pin the **honest current
baseline** as a no-regression gate — confuser ``wrong`` may never rise, and the
positives must keep solving — while explicitly NOT asserting ``wrong == 0`` (the
sealed composers genuinely misfire today; that is the defect surface the probe
exists to quantify, and the fixes must be general, not reactive patches).
"""

from __future__ import annotations

from evals.gsm8k_math.confusers.v1.runner import (
    load_cases,
    pair_inconsistencies,
    run_probe,
    summarize,
)

# Honest measured baseline (2026-05-29). The probe revealed the sealed composers
# wrongly answer these confuser categories; this pins them so they cannot grow.
_BASELINE_WRONG = 7
_BASELINE_PAIR_TELLS = 4


class TestSchema:
    def test_every_case_well_formed(self) -> None:
        valid_cat = {
            "disguised-polarity", "pseudo-accumulation", "multi-referent",
            "multi-actor-pronoun", "distractor-quantity", "temporal-scope",
            "comparative-referent", "unit-confuser", "genuine-positive",
        }
        ids = set()
        for c in load_cases():
            assert {"case_id", "question", "answer_numeric", "category", "expected"} <= c.keys()
            assert c["category"] in valid_cat
            assert c["expected"] in {"refuse", "solve"}
            assert c["case_id"] not in ids  # unique
            ids.add(c["case_id"])

    def test_pair_ids_resolve_and_are_mutual(self) -> None:
        cases = {c["case_id"]: c for c in load_cases()}
        for cid, c in cases.items():
            pair = c.get("pair_id")
            if pair:
                assert pair in cases, f"{cid} -> missing pair {pair}"
                assert cases[pair]["pair_id"] == cid, f"{cid}/{pair} not mutual"


class TestProbeBaseline:
    def test_wrong_does_not_regress(self) -> None:
        results = run_probe()
        wrong = sum(1 for r in results if r.verdict == "wrong")
        assert wrong <= _BASELINE_WRONG, (
            f"confuser wrong rose to {wrong} (baseline {_BASELINE_WRONG}); a change "
            f"made the engine answer more confusers — investigate before merge."
        )

    def test_genuine_positives_mostly_solve(self) -> None:
        # the capability signal: the clean accumulation twins read correctly.
        results = run_probe()
        positives = [r for r in results if r.expected == "solve"]
        solved = sum(1 for r in positives if r.verdict == "solved")
        assert solved >= 7, f"genuine positives solving dropped to {solved}"
        # and a positive must never be answered WRONG (that would be a real defect).
        assert all(r.verdict != "wrong" for r in positives)

    def test_pair_tells_do_not_regress(self) -> None:
        assert len(pair_inconsistencies()) <= _BASELINE_PAIR_TELLS

    def test_deterministic(self) -> None:
        assert summarize(run_probe()) == summarize(run_probe())
