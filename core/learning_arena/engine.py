"""ADR-0199 §2.2 — the domain-agnostic practice engine.

This is the extraction of the GSM8K ``run_practice`` fold into a subject-neutral
core. It is the **only** new per-domain code path a subject needs to reach: a
subject supplies a :class:`DomainSolver` + :class:`GoldTether` and gets a
:class:`PracticeReport` whose ``.ledger`` is the ``dict[str, ClassTally]`` the
reliability gate (``propose_from_ledger``) consumes unchanged.

Invariants (the load-bearing ADR-0199 mandates, enforced structurally here):

- **L-1 (one floor).** Reliability is computed only via :class:`ClassTally`
  (which calls the single pinned ``conservative_floor``). This module defines
  no pessimism constant of its own.
- **L-3 (seal).** ``run_practice`` returns a report and mutates nothing. It
  never touches a serving path or the active teaching corpus. Promotion is the
  caller's separate ``propose_from_ledger`` step into the reviewed corridor.
- **L-4 (determinism).** Pure fold over the input order; identical
  (problems, solver, tether, diagnose) -> identical report.
"""

from __future__ import annotations

from typing import Callable, Sequence

from core.learning_arena.protocols import Attempt, DomainProblem, DomainSolver, GoldTether
from core.learning_arena.report import EliminationRecord, PracticeReport
from core.reliability_gate import ClassTally


def _default_diagnose(_reason: str) -> str:
    """Conservative default: assume a missing piece (ADR-0175 §8).

    A domain supplies its own router (e.g. a refusal-reason vocabulary) via the
    ``diagnose`` parameter; absent one, refusals are attributed to a knowledge
    gap rather than silently dropped.
    """
    return "knowledge_gap"


def run_practice(
    problems: Sequence[DomainProblem],
    solver: DomainSolver,
    tether: GoldTether,
    *,
    diagnose: Callable[[str], str] = _default_diagnose,
) -> PracticeReport:
    """Sealed practice: attempt -> gold-tether score -> per-class ledger.

    For each problem, in input order: the solver attempts it; the verdict is
    ``refused`` when the attempt is uncommitted, else ``correct``/``wrong`` per
    the tether's independent gold check. Counts and per-class :class:`ClassTally`
    accumulate; each wrong yields an :class:`EliminationRecord`; each refusal is
    routed by ``diagnose``.
    """
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    ledger: dict[str, ClassTally] = {}
    diagnoses: dict[str, str] = {}
    elims: list[EliminationRecord] = []

    for problem in problems:
        cls = problem.class_name
        attempt: Attempt = solver.attempt(problem)

        if not attempt.committed:
            verdict = "refused"
        elif tether.is_correct(attempt, problem):
            verdict = "correct"
        else:
            verdict = "wrong"

        counts[verdict] = counts.get(verdict, 0) + 1
        tally = ledger.get(cls) or ClassTally(cls)

        if verdict == "correct":
            tally = tally.record(correct=1)
        elif verdict == "wrong":
            tally = tally.record(wrong=1)
            elims.append(
                EliminationRecord(
                    case_id=attempt.case_id,
                    class_name=cls,
                    attempted=attempt.answer,
                    gold=tether.gold_answer(problem),
                    reason=attempt.reason or "",
                )
            )
        else:  # refused
            tally = tally.record(refused=1)
            diagnoses[attempt.case_id] = diagnose(attempt.reason or "")

        ledger[cls] = tally

    return PracticeReport(
        counts=counts,
        ledger=ledger,
        refusal_diagnoses=diagnoses,
        elimination_records=tuple(elims),
    )
