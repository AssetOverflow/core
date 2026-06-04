"""ADR-0207 §5 step 2 / R4 — goal-residual production + its wrong=0 firewall.

The corpus lift-target cv-0005 (train_sample 0037) must read `goal − Σprogress`.
The load-bearing test is the **gain-goal divergence** (`test_reads_goal_not_possession`):
it proves the production reads the goal, not the possession, on a case where the two
arithmetics differ — the coincidental-correctness trap cv-0005 alone cannot catch.
"""
from __future__ import annotations

from generate.derivation.goal_residual import build_goal_residual, compose_goal_residual

# cv-0005 / train_sample 0037 (loss goal — residual and possession coincide at 3).
CV0005 = (
    "Michael wants to lose 10 pounds by June. He lost 3 pounds in March and 4 pounds "
    "in April. How much weight does he have to lose in May to meet his goal?"
)
# Adversarial gain goal — residual (20-5-6=9) DIVERGES from possession (20+5+6=31).
# Uses a recognized gain verb ("earned") so the progress cue is licensed.
SAVE_GOAL = (
    "Maria wants to earn 20 dollars for a gift. She earned 5 dollars in May and 6 dollars "
    "in June. How much more does she need to earn to reach her goal?"
)


def _answer(text):
    res = compose_goal_residual(text)
    return None if res is None else res.answer


def test_cv0005_goal_residual_solves() -> None:
    """cv-0005: goal 10 − (3 + 4) = 3, read as a goal (start=10, all-subtract)."""
    deriv = build_goal_residual(CV0005)
    assert deriv is not None
    assert deriv.start.value == 10.0
    assert all(s.op == "subtract" for s in deriv.steps)
    assert _answer(CV0005) == 3.0


def test_reads_goal_not_possession() -> None:
    """WRONG=0 FIREWALL. On a gain goal, goal-residual (9) diverges from possession-
    accumulation (31). The production must give 9 (reads the goal) — never 31, and the
    chain must be all-subtract (progress reduces the residual regardless of polarity)."""
    deriv = build_goal_residual(SAVE_GOAL)
    assert deriv is not None
    assert _answer(SAVE_GOAL) == 9.0, "must read goal-residual, not possession 31"
    assert all(s.op == "subtract" for s in deriv.steps), "progress always subtracts"
    assert deriv.start.value == 20.0


def test_no_goal_language_does_not_fire() -> None:
    """A possession case (no goal-intent lexeme) must NOT fire this production —
    it belongs to accumulation, not goal-residual."""
    possession = "Sam has 14 apples. He gives away 3 apples and 2 apples. How many are left?"
    assert build_goal_residual(possession) is None


def test_no_residual_question_does_not_fire() -> None:
    """Goal language but no residual question → does not fire."""
    no_residual = (
        "Michael wants to lose 10 pounds by June. He lost 3 pounds in March and 4 pounds "
        "in April. How much weight did he lose in total?"
    )
    assert build_goal_residual(no_residual) is None


def test_incomplete_reading_refuses() -> None:
    """A progress clause with a new named actor (referent hazard) must refuse — the
    same-referent guard is inherited, never weakened."""
    cross_referent = (
        "Michael wants to lose 10 pounds by June. Sarah lost 3 pounds in March. "
        "How much more does Michael need to lose to meet his goal?"
    )
    assert build_goal_residual(cross_referent) is None
