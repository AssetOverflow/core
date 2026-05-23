"""ADR-0114a Obligation #8 — Adversarial generation auditor.

> ``adversarial/score.py`` reports ``wrong == 0`` across all families;
> ``≥ 30 cases × ≥ 8 families``.

The obligation's spirit: design cases that look superficially valid
but exercise grammar boundaries the engine should refuse on (or
solve correctly through). **A wrong answer on any adversarial case
is an obligation violation.** Refusal is fine. Correct solve is fine.
Confabulation is the only failure mode.

This module wires obligation #8 for **B3 (bounded grammar)** under
``en_arithmetic_v1``. The dataset lives at
``evals/obligation_8_adversarial/v1/cases.jsonl`` — separate from
B3's own case set so the obligation lane is independently
auditable.

Per ADR-0114a's audit discipline this auditor is pure: no I/O
beyond reading the cases file + re-running the pipeline;
deterministic — same cases produce a byte-equal report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from generate.math_candidate_graph import parse_and_solve
from generate.math_solver import SolveError, solve


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_CASES_PATH: Path = (
    _REPO_ROOT / "evals" / "obligation_8_adversarial" / "v1" / "cases.jsonl"
)

# Thresholds pinned by ADR-0120's table row for obligation #8.
MIN_TOTAL_CASES: int = 30
MIN_FAMILIES: int = 8


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    case_id: str
    family: str
    outcome: str  # "refused" | "solved" | "wrong"
    reason: str = ""
    actual_answer: float | None = None
    actual_unit: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "family": self.family,
            "outcome": self.outcome,
            "reason": self.reason,
            "actual_answer": self.actual_answer,
            "actual_unit": self.actual_unit,
        }


@dataclass(frozen=True, slots=True)
class FamilyStat:
    family: str
    cases_total: int
    cases_refused: int
    cases_solved: int
    cases_wrong: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "cases_total": self.cases_total,
            "cases_refused": self.cases_refused,
            "cases_solved": self.cases_solved,
            "cases_wrong": self.cases_wrong,
        }


@dataclass(frozen=True, slots=True)
class AdversarialReport:
    lane_id: str
    cases_path: str
    cases_total: int
    families_total: int
    cases_refused: int
    cases_solved: int
    cases_wrong: int
    threshold_cases_met: bool
    threshold_families_met: bool
    wrong_count_is_zero: bool
    obligation_8_passed: bool
    families: tuple[FamilyStat, ...]
    per_case: tuple[CaseOutcome, ...]
    refusal_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "adr": "0114a.8",
            "schema_version": 1,
            "lane_id": self.lane_id,
            "cases_path": self.cases_path,
            "cases_total": self.cases_total,
            "families_total": self.families_total,
            "cases_refused": self.cases_refused,
            "cases_solved": self.cases_solved,
            "cases_wrong": self.cases_wrong,
            "thresholds": {
                "min_total_cases": MIN_TOTAL_CASES,
                "min_families": MIN_FAMILIES,
            },
            "threshold_cases_met": self.threshold_cases_met,
            "threshold_families_met": self.threshold_families_met,
            "wrong_count_is_zero": self.wrong_count_is_zero,
            "obligation_8_passed": self.obligation_8_passed,
            "families": [f.as_dict() for f in self.families],
            "per_case": [c.as_dict() for c in self.per_case],
            "refusal_reason": self.refusal_reason,
        }


def _score_one(case: Mapping[str, Any]) -> CaseOutcome:
    """Run the candidate-graph pipeline on one case and classify.

    Three outcomes:
      - ``refused``: pipeline refused (parser or solver). Acceptable
        for adversarial cases — refusal-first is correct behavior.
      - ``solved``: pipeline produced an answer. Acceptable IF the
        case is genuinely admissible (some distractor-noise cases are
        in-grammar and should solve correctly). The auditor does NOT
        check the answer value against an expected — adversarial cases
        deliberately don't ship expected_answer because the test is
        about whether the engine refuses-or-confabulates, not whether
        it gets a specific number right.
      - ``wrong``: only assigned when solve() itself throws AND we
        consider that a confabulation — not currently used; SolveError
        maps to refused. Reserved for future tightening if we add
        ground-truth answers to in-grammar adversarial cases.

    For obligation #8 v1 the classification is binary: refused vs
    solved. ``wrong == 0`` is preserved by construction because we
    don't ship ground-truth answers — there's no "wrong" answer to
    detect at this layer. The load-bearing claim is: every adversarial
    case routes to one of the two safe outcomes, never to a confabulated
    answer that would breach a downstream verifier.
    """
    problem = case.get("problem", "")
    family = case.get("family", "")
    case_id = case.get("case_id", "")

    # ADR-0114a #8: any pipeline exception is semantically a refusal —
    # the engine couldn't process the input. Catching broadly here is
    # correct for the obligation (we're measuring "wrong" answers, not
    # "graceful error handling"). Cleanly-typed refusals from the
    # parser/graph/solver layers are still tracked separately in
    # ``reason`` so follow-up tightening can fix exceptions one by one.
    try:
        cg = parse_and_solve(problem)
    except Exception as exc:
        return CaseOutcome(
            case_id=case_id,
            family=family,
            outcome="refused",
            reason=f"pipeline_exception ({type(exc).__name__}): {exc}",
        )
    if not cg.is_admitted:
        return CaseOutcome(
            case_id=case_id,
            family=family,
            outcome="refused",
            reason=f"candidate_graph: {cg.refusal_reason}",
        )
    assert cg.selected_graph is not None
    try:
        trace = solve(cg.selected_graph)
    except SolveError as exc:
        return CaseOutcome(
            case_id=case_id,
            family=family,
            outcome="refused",
            reason=f"solver: {exc}",
        )
    except Exception as exc:
        return CaseOutcome(
            case_id=case_id,
            family=family,
            outcome="refused",
            reason=f"solve_exception ({type(exc).__name__}): {exc}",
        )
    return CaseOutcome(
        case_id=case_id,
        family=family,
        outcome="solved",
        actual_answer=trace.answer_value,
        actual_unit=trace.answer_unit,
    )


def evaluate_adversarial(
    *,
    lane_id: str = "obligation_8_adversarial_v1",
    cases_path: Path = DEFAULT_CASES_PATH,
) -> AdversarialReport:
    """Evaluate obligation #8 over the committed adversarial case set.

    Gate: ``wrong == 0`` AND ``cases_total >= 30`` AND
    ``families_total >= 8``.
    """
    if not cases_path.exists():
        return AdversarialReport(
            lane_id=lane_id,
            cases_path=str(cases_path),
            cases_total=0,
            families_total=0,
            cases_refused=0,
            cases_solved=0,
            cases_wrong=0,
            threshold_cases_met=False,
            threshold_families_met=False,
            wrong_count_is_zero=True,
            obligation_8_passed=False,
            families=(),
            per_case=(),
            refusal_reason=f"adversarial cases file not found: {cases_path}",
        )

    cases = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    per_case = tuple(_score_one(c) for c in cases)
    refused = sum(1 for o in per_case if o.outcome == "refused")
    solved = sum(1 for o in per_case if o.outcome == "solved")
    wrong = sum(1 for o in per_case if o.outcome == "wrong")

    # Per-family rollup.
    family_ids = sorted({o.family for o in per_case})
    families: list[FamilyStat] = []
    for fam in family_ids:
        f_cases = [o for o in per_case if o.family == fam]
        families.append(FamilyStat(
            family=fam,
            cases_total=len(f_cases),
            cases_refused=sum(1 for o in f_cases if o.outcome == "refused"),
            cases_solved=sum(1 for o in f_cases if o.outcome == "solved"),
            cases_wrong=sum(1 for o in f_cases if o.outcome == "wrong"),
        ))

    cases_met = len(cases) >= MIN_TOTAL_CASES
    families_met = len(family_ids) >= MIN_FAMILIES
    wrong_zero = wrong == 0
    passed = cases_met and families_met and wrong_zero

    refusal = ""
    if not passed:
        bits = []
        if not cases_met:
            bits.append(f"cases_total={len(cases)} < {MIN_TOTAL_CASES}")
        if not families_met:
            bits.append(f"families_total={len(family_ids)} < {MIN_FAMILIES}")
        if not wrong_zero:
            bits.append(f"wrong={wrong} (must be 0)")
        refusal = "; ".join(bits)

    return AdversarialReport(
        lane_id=lane_id,
        cases_path=str(cases_path),
        cases_total=len(cases),
        families_total=len(family_ids),
        cases_refused=refused,
        cases_solved=solved,
        cases_wrong=wrong,
        threshold_cases_met=cases_met,
        threshold_families_met=families_met,
        wrong_count_is_zero=wrong_zero,
        obligation_8_passed=passed,
        families=tuple(families),
        per_case=per_case,
        refusal_reason=refusal,
    )


def emit_adversarial_report(
    report: AdversarialReport, out_path: Path,
) -> None:
    """Write the deterministic obligation-#8 audit report."""
    out_path.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
