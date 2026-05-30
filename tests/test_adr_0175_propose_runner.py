"""ADR-0175 PROPOSE runner — the loop closes: attempt → tether → ledger → propose.

Fast + deterministic via an injected scorer + cases (no heavy reader run).
"""

from __future__ import annotations

from typing import Any

from evals.gsm8k_math.practice.v1.propose_runner import build_ratification_queue
from evals.gsm8k_math.runner import CaseOutcome


def _cases(n: int) -> list[dict[str, Any]]:
    # answer_expression carries a single '+' calc → one gold operation class.
    return [
        {
            "case_id": f"c{i}",
            "question": "irrelevant",
            "answer_expression": "1+1 = <<1+1=2>>2",
            "answer_numeric": 2,
        }
        for i in range(n)
    ]


def _scorer(outcomes: list[str]):
    it = iter(outcomes)

    def score(adapted: dict[str, Any]) -> CaseOutcome:
        verdict = next(it)
        gold = float(adapted["expected_answer"])
        return CaseOutcome(
            case_id=adapted["id"],
            outcome=verdict,
            reason="mock",
            expected_answer=gold,
            expected_unit="",
            actual_answer=gold if verdict == "correct" else (gold + 1 if verdict == "wrong" else None),
            actual_unit=None,
            trace_hash=None,
            realized_prose=None,
        )

    return score


def test_loop_proposes_a_reliable_class() -> None:
    # 45 correct → the Wilson floor on 45/45 (≈0.87) clears θ=0.85. The floor is
    # deliberately conservative at small N (30/30 ≈ 0.82 does NOT clear) — that
    # strictness, demanding evidence before promotion, is the point.
    q = build_ratification_queue(cases=_cases(45), scorer=_scorer(["correct"] * 45))
    assert q["proposal_count"] == 1
    p = q["proposals"][0]
    assert p["correct"] == 45 and p["wrong"] == 0 and p["committed"] == 45
    assert p["measured"] >= p["required"] >= 0.85
    assert p["action"] == "propose"


def test_loop_filters_unreliable_class() -> None:
    # 6 correct + 6 wrong → reliability far below 0.85 → no proposal.
    q = build_ratification_queue(
        cases=_cases(12), scorer=_scorer(["correct", "wrong"] * 6)
    )
    assert q["proposal_count"] == 0
    assert q["practice_counts"]["wrong"] == 6


def test_loop_respects_n_min_floor() -> None:
    # 9 correct (< N_MIN committed) → reliability 0 → no proposal.
    q = build_ratification_queue(cases=_cases(9), scorer=_scorer(["correct"] * 9))
    assert q["proposal_count"] == 0


def test_queue_is_deterministic_and_proposal_only() -> None:
    a = build_ratification_queue(cases=_cases(45), scorer=_scorer(["correct"] * 45))
    b = build_ratification_queue(cases=_cases(45), scorer=_scorer(["correct"] * 45))
    assert a == b
    assert a["regime"] == "propose"
    assert "never a serving mutation" in a["note"]
