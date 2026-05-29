"""ADR-0178 GB-3b.1 — wire the accumulation composer into the sealed practice lane.

Mirrors :mod:`evals.gsm8k_math.practice.v1.search_runner`: when the base engine
*refuses*, the practice regime is allowed to *attempt* the single-referent
accumulation reading (:func:`generate.derivation.accumulate.compose_accumulation`)
and checks it against gold (Tier-1, available in practice). Correct attempts flip;
wrong attempts become elimination records. The base (serving) outcome is never
altered — the composer only fires on cases the engine already declined, inside the
sealed lane. Serving stays ``3/47/0``.
"""

from __future__ import annotations

from evals.gsm8k_math.practice.v1.runner import (
    PracticeReport,
    _load_practice_cases,
    run_practice,
)
from evals.gsm8k_math.practice.v1.search_runner import _TOL, _SearchOutcome
from evals.gsm8k_math.runner import _score_one_candidate_graph
from generate.derivation.accumulate import compose_accumulation


def accumulation_augmented_scorer(adapted: dict) -> object:
    """Base scorer, then a practice-only accumulation attempt on refusals."""
    base = _score_one_candidate_graph(adapted)
    if base.outcome != "refused":
        return base  # the serving path already committed — leave it untouched

    resolution = compose_accumulation(adapted["problem"])
    if resolution is None:
        return base  # accumulation also declined -> still refused

    attempted = resolution.answer
    gold = float(adapted["expected_answer"])
    correct = abs(attempted - gold) <= _TOL
    return _SearchOutcome(
        case_id=adapted["id"],
        outcome="correct" if correct else "wrong",
        reason=(
            f"compose_accumulation -> {attempted:g}"
            if correct
            else f"compose_accumulation wrong: got {attempted:g}, gold {gold:g}"
        ),
        actual_answer=attempted,
    )


def build_accumulation_report() -> PracticeReport:
    """Practice report with the accumulation reading enabled (attempts live)."""
    return run_practice(_load_practice_cases(), scorer=accumulation_augmented_scorer)
