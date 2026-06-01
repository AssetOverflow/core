"""ADR-0175 Phase 2 — sealed practice lane over the GSM8K train sample.

ADR-0199: this lane is now the **first instance** of the cross-domain learning
arena. The domain-agnostic fold lives in :mod:`core.learning_arena.engine`; this
module supplies only the GSM8K-specific pieces — the operation classifier
(capability classes from gold), the refusal-reason router, and the
solver/gold-tether adapters around the existing candidate-graph scorer. Behavior
is unchanged: the public surface (``run_practice(cases, scorer=...)``,
``build_report``, ``build_practice_report``, ``PracticeReport``,
``EliminationRecord``, ``classify_operation``, ``diagnose_refusal``) is
preserved byte-for-byte against the prior lane.

Separate from the wrong=0-pinned serving runner (``train_sample/v1/runner.py``),
which is **never modified**. Runs the cases in *practice* mode: wrong is the
learning signal, not a lane failure.

The seal (invariant #1): this lane writes only its own ``report.json``; no
serving path reads it and no serving module imports this runner. A wrong here
never becomes a served answer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from core.learning_arena.engine import run_practice as _engine_run_practice
from core.learning_arena.protocols import Problem
# Re-exported so existing callers/tests keep importing these from the lane.
from core.learning_arena.report import (  # noqa: F401
    REFUSAL_DIAGNOSES,
    EliminationRecord,
    PracticeReport,
)
from evals.gsm8k_math.runner import _score_one_candidate_graph
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _adapt, _load_cases

OPERATION_CLASSES: tuple[str, ...] = ("multiplicative", "divisive", "additive")

_HERE = Path(__file__).resolve().parent
_REPORT_PATH = _HERE / "report.json"
_PRACTICE_CASES_PATH = _HERE / "cases.jsonl"
_CALC_RE = re.compile(r"<<([^=>]+)=")

_DOMAIN_ID = "mathematics_logic"


def classify_operation(answer_expression: str) -> str:
    """Primary gold operation class from GSM8K ``<<a*b=c>>`` calc annotations.

    ``multiplicative`` if any ``*``; else ``divisive`` if any ``/``; else
    ``additive``. Gold-derived — legitimate in practice (Tier-1 checkable).
    """
    has_mul = has_div = False
    for step in _CALC_RE.findall(answer_expression or ""):
        if "*" in step:
            has_mul = True
        if "/" in step:
            has_div = True
    if has_mul:
        return "multiplicative"
    if has_div:
        return "divisive"
    return "additive"


def diagnose_refusal(reason: str) -> str:
    """§8 router — name the missing piece behind a refusal.

    First cut from the current refusal-reason vocabulary; refined in Phase 3
    when the grounded search makes "skill" precise ("no grounded derivation
    found"). Defaults conservatively to ``knowledge_gap`` (assume a missing
    piece) rather than silently dropping a refusal.
    """
    low = (reason or "").lower()
    if "branches disagree" in low:
        return "genuine_ambiguity"
    if "produced no injection" in low or "no branch produced a solvable" in low:
        return "skill_gap"
    if "no admissible candidate" in low or "expected exactly one question" in low:
        return "knowledge_gap"
    return "knowledge_gap"


# --- GSM8K instance of the ADR-0199 DomainSolver / GoldTether ------------------


@dataclass(frozen=True, slots=True)
class _GSM8KAttempt:
    """Concrete Attempt that also carries the scorer's gold verdict.

    The candidate-graph scorer already decides correct/wrong/refused against the
    dataset's ``expected_answer`` (gold independent of the engine's derivation —
    ADR-0199 L-2). The tether reads that verdict via ``scorer_outcome`` so the
    classification is reproduced exactly, not re-derived.
    """

    committed: bool
    answer: Any
    reason: str
    case_id: str
    scorer_outcome: str
    derivations: tuple[Any, ...] = field(default_factory=tuple)
    trace_sha256: str = ""


@dataclass(frozen=True, slots=True)
class _GSM8KSolver:
    score: Callable[[dict[str, Any]], Any]
    domain_id: str = _DOMAIN_ID

    def attempt(self, problem: Problem) -> _GSM8KAttempt:
        outcome = self.score(_adapt(problem.payload))
        return _GSM8KAttempt(
            committed=(outcome.outcome != "refused"),
            answer=getattr(outcome, "actual_answer", None),
            reason=outcome.reason or "",
            case_id=outcome.case_id,
            scorer_outcome=outcome.outcome,
        )


@dataclass(frozen=True, slots=True)
class _GSM8KGoldTether:
    domain_id: str = _DOMAIN_ID

    def is_correct(self, attempt: _GSM8KAttempt, problem: Problem) -> bool:
        return attempt.scorer_outcome == "correct"

    def gold_answer(self, problem: Problem) -> float:
        return float(problem.payload["answer_numeric"])


def _to_problem(raw: dict[str, Any]) -> Problem:
    return Problem(
        problem_id=str(raw.get("id", raw.get("case_id", ""))),
        class_name=classify_operation(raw.get("answer_expression", "")),
        payload=raw,
    )


def run_practice(
    cases: list[dict[str, Any]],
    *,
    scorer: Callable[[dict[str, Any]], Any] | None = None,
) -> PracticeReport:
    """Run the cases in practice mode and build the report.

    Unchanged signature and behavior. ``scorer`` is injectable for testing; it
    defaults to the candidate-graph scorer. The fold is delegated to the
    domain-agnostic :func:`core.learning_arena.engine.run_practice` (ADR-0199);
    this lane supplies the GSM8K solver/tether and the §8 diagnosis router.
    """
    score = scorer if scorer is not None else _score_one_candidate_graph
    solver = _GSM8KSolver(score)
    tether = _GSM8KGoldTether()
    problems = [_to_problem(raw) for raw in cases]
    return _engine_run_practice(problems, solver, tether, diagnose=diagnose_refusal)


def _load_practice_cases(path: Path = _PRACTICE_CASES_PATH) -> list[dict[str, Any]]:
    """Load cases from the practice-specific cases.jsonl (no count assertion)."""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def build_report() -> PracticeReport:
    return run_practice(_load_cases(_CASES_PATH))


def build_practice_report() -> PracticeReport:
    """Run the practice lane over the dedicated practice case set."""
    return run_practice(_load_practice_cases())


def write_report(report: PracticeReport, path: Path = _REPORT_PATH) -> None:
    path.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Run the practice lane. Never fails on wrong — practice records it."""
    write_report(build_report())
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
