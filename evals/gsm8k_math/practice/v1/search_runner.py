"""ADR-0175 Phase 3b — wire the multiplicative search into the sealed practice lane.

The practice lane (Phase 2) runs the base candidate-graph scorer. Here we augment
it: when the base engine *refuses*, the practice regime is allowed to *attempt* —
it runs the Phase 3b multiplicative search and checks the result against gold
(Tier-1, available in practice). Correct attempts flip; wrong attempts become
elimination records (§9). The base (serving) outcome is never altered — the search
only fires on cases the engine already declined, and only inside the sealed lane.

This is the first phase where attempts and eliminations go live.
"""

from __future__ import annotations

from dataclasses import dataclass

from evals.gsm8k_math.practice.v1.runner import PracticeReport, run_practice
from evals.gsm8k_math.runner import _score_one_candidate_graph
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases
from generate.derivation.search import search_multiplicative

_TOL = 1e-6


@dataclass(frozen=True, slots=True)
class _SearchOutcome:
    case_id: str
    outcome: str
    reason: str | None
    actual_answer: float | None


def search_augmented_scorer(adapted: dict) -> object:
    """Base scorer, then a practice-only multiplicative attempt on refusals."""
    base = _score_one_candidate_graph(adapted)
    if base.outcome != "refused":
        return base  # the serving path already committed — leave it untouched

    resolution = search_multiplicative(adapted["problem"])
    if resolution is None:
        return base  # search also declined -> still refused

    attempted = resolution.answer
    gold = float(adapted["expected_answer"])
    correct = abs(attempted - gold) <= _TOL
    return _SearchOutcome(
        case_id=adapted["id"],
        outcome="correct" if correct else "wrong",
        reason=(
            f"search_multiplicative -> {attempted:g}"
            if correct
            else f"search_multiplicative wrong: got {attempted:g}, gold {gold:g}"
        ),
        actual_answer=attempted,
    )


def build_search_report() -> PracticeReport:
    """Practice report with the multiplicative search enabled (attempts live)."""
    return run_practice(_load_cases(_CASES_PATH), scorer=search_augmented_scorer)
