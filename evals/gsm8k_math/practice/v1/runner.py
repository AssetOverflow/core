"""ADR-0175 Phase 2 — sealed practice lane over the GSM8K train sample.

Separate from the wrong=0-pinned serving runner (``train_sample/v1/runner.py``),
which is **never modified**. Runs the 47 cases in *practice* mode: scores
correct/wrong/refused as practice metrics (wrong is tolerated — it is the
learning signal, not a lane failure), feeds per-class counts into the Phase 1
reliability ledger, diagnoses every refusal (§8 skill/knowledge/ambiguity), and
emits an elimination record for each wrong.

The seal (invariant #1): this lane writes only its own ``report.json``; no
serving path reads it and no serving module imports this runner. A wrong here
never becomes a served answer.

On the current refuse-preferring pipeline the engine still declines rather than
guesses, so the live practice ledger mirrors serving (3/47/0) and zero
eliminations fire — the attempt-generating grounded search is Phase 3. Phase 2
proves the *regime*: lane, ledger wiring, diagnosis, elimination schema, seal.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from core.reliability_gate import ClassTally
from evals.gsm8k_math.runner import _score_one_candidate_graph
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _adapt, _load_cases

OPERATION_CLASSES: tuple[str, ...] = ("multiplicative", "divisive", "additive")
REFUSAL_DIAGNOSES: tuple[str, ...] = ("skill_gap", "knowledge_gap", "genuine_ambiguity")

_HERE = Path(__file__).resolve().parent
_REPORT_PATH = _HERE / "report.json"
_CALC_RE = re.compile(r"<<([^=>]+)=")


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


@dataclass(frozen=True, slots=True)
class EliminationRecord:
    """A wrong practice attempt that gold caught — the pruning signal (§9)."""

    case_id: str
    class_name: str
    attempted: float | None
    gold: float
    reason: str


@dataclass(frozen=True, slots=True)
class PracticeReport:
    counts: Mapping[str, int]
    ledger: Mapping[str, ClassTally]
    refusal_diagnoses: Mapping[str, str]
    elimination_records: tuple[EliminationRecord, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "adr": "0175",
            "regime": "practice",
            "counts": dict(self.counts),
            "per_class": {
                cls: {
                    "correct": t.correct,
                    "wrong": t.wrong,
                    "refused": t.refused,
                    "committed": t.committed,
                    "reliability": t.reliability,
                    "coverage": t.coverage,
                }
                for cls, t in sorted(self.ledger.items())
            },
            "refusal_diagnoses": dict(sorted(self.refusal_diagnoses.items())),
            "diagnosis_counts": _bucket_counts(self.refusal_diagnoses),
            "elimination_records": [
                {
                    "case_id": r.case_id,
                    "class_name": r.class_name,
                    "attempted": r.attempted,
                    "gold": r.gold,
                    "reason": r.reason,
                }
                for r in self.elimination_records
            ],
        }


def _bucket_counts(diagnoses: Mapping[str, str]) -> dict[str, int]:
    out = {d: 0 for d in REFUSAL_DIAGNOSES}
    for d in diagnoses.values():
        out[d] = out.get(d, 0) + 1
    return out


def run_practice(
    cases: list[dict[str, Any]],
    *,
    scorer: Callable[[dict[str, Any]], Any] | None = None,
) -> PracticeReport:
    """Run the cases in practice mode and build the report.

    ``scorer`` is injectable for testing; it defaults to the candidate-graph
    scorer :func:`evals.gsm8k_math.runner._score_one_candidate_graph`. The
    practice lane only *reads* the engine's outcome — it never alters the
    serving path.
    """
    score = scorer if scorer is not None else _score_one_candidate_graph
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    ledger: dict[str, ClassTally] = {}
    diagnoses: dict[str, str] = {}
    elims: list[EliminationRecord] = []

    for raw in cases:
        cls = classify_operation(raw.get("answer_expression", ""))
        outcome = score(_adapt(raw))
        verdict = outcome.outcome
        counts[verdict] = counts.get(verdict, 0) + 1
        tally = ledger.get(cls) or ClassTally(cls)

        if verdict == "correct":
            tally = tally.record(correct=1)
        elif verdict == "wrong":
            tally = tally.record(wrong=1)
            elims.append(
                EliminationRecord(
                    case_id=outcome.case_id,
                    class_name=cls,
                    attempted=getattr(outcome, "actual_answer", None),
                    gold=float(raw["answer_numeric"]),
                    reason=outcome.reason or "",
                )
            )
        else:  # refused
            tally = tally.record(refused=1)
            diagnoses[outcome.case_id] = diagnose_refusal(outcome.reason or "")

        ledger[cls] = tally

    return PracticeReport(
        counts=counts,
        ledger=ledger,
        refusal_diagnoses=diagnoses,
        elimination_records=tuple(elims),
    )


def build_report() -> PracticeReport:
    return run_practice(_load_cases(_CASES_PATH))


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
