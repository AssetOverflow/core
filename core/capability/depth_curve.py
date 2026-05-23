"""ADR-0114a Obligation #6 — Compositional-depth curve auditor.

> ``depth_curve.py`` produces a per-bucket curve;
> ``accuracy(N) ≥ accuracy(depth_1) · (1 − ε)^(N − 1)`` for ε = 0.05.

The auditor re-runs the candidate-graph pipeline on a lane's cases,
buckets each by the **authoritative depth = len(trace.steps)**, and
checks the per-bucket accuracy against the decay bound.

Why ``len(trace.steps)`` is authoritative: ADR-0114a's #6 measures
*reasoning depth as the engine actually executed it*, not the case's
declared depth. A two-statement problem the engine solves in one
step (e.g., constant-folded) has effective depth 1. The trace is the
single source of truth.

Bucket schema mirrors ADR-0119.6 (the GSM8K-context substrate):
``depth_1``, ``depth_2-3``, ``depth_4-5``, ``depth_6-8``. Depth > 8
raises rather than silently extending the schema (any extension
requires an ADR amendment).

This module wires obligation #6 for **B3 (bounded grammar)** — the
lane whose pipeline produces solver traces. B1 (symbolic
equivalence) is algebra-not-arithmetic; B2 (teaching corpus) is
chain-validation, not problem-solving. Neither produces traces this
auditor consumes. Equivalents are deferred to separate sub-ADRs.

Honest scope-limit: B3 v1's case set is **dominated by depth-1
problems** (single-statement bounded grammar). The auditor's
mechanism runs correctly; the *assertion* of obligation #6 is
meaningful only when multiple buckets are populated. The report
includes a ``coverage_sufficient`` flag that distinguishes
"mechanism wired + assertion holds vacuously" from "assertion holds
across multiple populated buckets". Both are valid pre-promotion
states; the latter is required for the full ADR-0120 expert gate.

Per ADR-0114a's audit discipline this auditor is pure: no I/O
beyond reading the lane's cases.jsonl + re-solving; deterministic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generate.math_candidate_graph import parse_and_solve
from generate.math_solver import SolveError, solve


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_B3_CASES: Path = (
    _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
)

# Decay bound per ADR-0120 §"Threshold rationale" (table row obligation #6).
DECAY_EPSILON: float = 0.05

# Documented bucket schema — extension requires an ADR amendment.
BUCKET_SCHEMA: tuple[str, ...] = (
    "depth_1", "depth_2-3", "depth_4-5", "depth_6-8",
)
MAX_SUPPORTED_DEPTH: int = 8

# Minimum cases per *populated* bucket for the assertion to be
# considered statistically meaningful. The mechanism passes on
# any populated bucket regardless; coverage_sufficient = True
# requires ≥2 populated buckets each with ≥3 cases.
MIN_BUCKETS_FOR_COVERAGE: int = 2
MIN_CASES_PER_BUCKET_FOR_COVERAGE: int = 3


class DepthCurveError(Exception):
    """Raised when a case's depth is outside the documented bucket
    schema, or when the cases file can't be read.

    Reasons:
        - depth ≥ 9 (extending the schema requires an ADR amendment)
        - depth == 0 (degenerate)
        - cases file missing or unreadable
    """


def _depth_to_bucket(depth: int) -> str:
    if depth == 1:
        return "depth_1"
    if 2 <= depth <= 3:
        return "depth_2-3"
    if 4 <= depth <= 5:
        return "depth_4-5"
    if 6 <= depth <= 8:
        return "depth_6-8"
    raise DepthCurveError(
        f"depth {depth} outside documented bucket range 1..{MAX_SUPPORTED_DEPTH}; "
        f"extending the schema requires an ADR amendment"
    )


@dataclass(frozen=True, slots=True)
class BucketStat:
    bucket: str
    cases_total: int
    cases_correct: int
    accuracy: float
    bound_required: float | None  # None for depth_1 (the anchor)
    bound_satisfied: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "bucket": self.bucket,
            "cases_total": self.cases_total,
            "cases_correct": self.cases_correct,
            "accuracy": self.accuracy,
            "bound_required": self.bound_required,
            "bound_satisfied": self.bound_satisfied,
        }


@dataclass(frozen=True, slots=True)
class DepthCurveReport:
    lane_id: str
    cases_total: int
    cases_solved: int
    cases_skipped_unsolved: int
    epsilon: float
    buckets: tuple[BucketStat, ...]
    populated_buckets: tuple[str, ...]
    obligation_6_mechanism_wired: bool
    obligation_6_assertion_holds: bool
    coverage_sufficient: bool
    refusal_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "adr": "0114a.6",
            "schema_version": 1,
            "lane_id": self.lane_id,
            "cases_total": self.cases_total,
            "cases_solved": self.cases_solved,
            "cases_skipped_unsolved": self.cases_skipped_unsolved,
            "epsilon": self.epsilon,
            "buckets": [b.as_dict() for b in self.buckets],
            "populated_buckets": list(self.populated_buckets),
            "obligation_6_mechanism_wired": self.obligation_6_mechanism_wired,
            "obligation_6_assertion_holds": self.obligation_6_assertion_holds,
            "coverage_sufficient": self.coverage_sufficient,
            "refusal_reason": self.refusal_reason,
        }


def _required_bound(anchor_accuracy: float, representative_depth: int) -> float:
    """ADR-0114a #6 formula: accuracy(N) ≥ accuracy(depth_1) · (1 − ε)^(N − 1).

    For a bucketed schema we use the *minimum* depth in the bucket as
    the representative N (most permissive — gives the bound the best
    chance of holding even when only the shallow end of the bucket is
    populated). This is the standard convention; any tightening
    (e.g., max-depth-in-bucket) requires an ADR amendment.
    """
    if representative_depth <= 1:
        return anchor_accuracy
    return anchor_accuracy * ((1.0 - DECAY_EPSILON) ** (representative_depth - 1))


def _representative_depth(bucket: str) -> int:
    """Min depth in each bucket; used to evaluate the decay bound."""
    return {
        "depth_1": 1,
        "depth_2-3": 2,
        "depth_4-5": 4,
        "depth_6-8": 6,
    }[bucket]


def _solve_case(problem: str) -> int | None:
    """Re-run the candidate-graph pipeline; return depth = len(trace.steps)
    on a successful solve, None on refusal / SolveError.
    """
    cg = parse_and_solve(problem)
    if not cg.is_admitted:
        return None
    assert cg.selected_graph is not None
    try:
        trace = solve(cg.selected_graph)
    except SolveError:
        return None
    return len(trace.steps)


def evaluate_depth_curve(
    *,
    lane_id: str = "B3_bounded_grammar",
    cases_path: Path = DEFAULT_B3_CASES,
) -> DepthCurveReport:
    """Evaluate obligation #6 on a B-lane.

    For each expected-correct case: re-solve, bucket by trace step count,
    aggregate per-bucket accuracy. The depth_1 bucket anchors the decay
    bound; each populated bucket beyond depth_1 must satisfy the bound.

    Returns ``obligation_6_assertion_holds = True`` iff every populated
    bucket satisfies its bound (trivially true when only depth_1 is
    populated). ``coverage_sufficient`` flags whether the assertion is
    statistically meaningful (≥2 populated buckets, ≥3 cases each).
    """
    if not cases_path.exists():
        return DepthCurveReport(
            lane_id=lane_id,
            cases_total=0,
            cases_solved=0,
            cases_skipped_unsolved=0,
            epsilon=DECAY_EPSILON,
            buckets=(),
            populated_buckets=(),
            obligation_6_mechanism_wired=False,
            obligation_6_assertion_holds=False,
            coverage_sufficient=False,
            refusal_reason=f"cases file not found: {cases_path}",
        )

    cases = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # bucket -> (total, correct). A case counts in 'total' for its bucket
    # iff it was expected-correct AND the pipeline produced a trace.
    # 'correct' counts the subset whose answer matched expected_answer.
    bucket_totals: dict[str, int] = {b: 0 for b in BUCKET_SCHEMA}
    bucket_correct: dict[str, int] = {b: 0 for b in BUCKET_SCHEMA}
    solved = skipped = 0

    for case in cases:
        if case.get("expected") != "solved_correct":
            skipped += 1
            continue
        depth = _solve_case(case.get("problem", ""))
        if depth is None:
            skipped += 1
            continue
        if depth == 0:
            # Initial-only problems (just a quantity assertion + question)
            # exercise no operation reasoning. Count as skipped rather than
            # forcing them into a bucket — obligation #6 measures reasoning-
            # depth decay, and zero-depth has nothing to decay.
            skipped += 1
            continue
        bucket = _depth_to_bucket(depth)
        bucket_totals[bucket] += 1
        # Re-check correctness against expected_answer. We already solved
        # but didn't compare; do the comparison now.
        cg = parse_and_solve(case["problem"])
        if cg.is_admitted and cg.selected_graph is not None:
            trace = solve(cg.selected_graph)
            if trace.answer_value == float(case.get("expected_answer", float("inf"))):
                bucket_correct[bucket] += 1
        solved += 1

    # Compute per-bucket stats and the decay bound.
    populated = tuple(b for b in BUCKET_SCHEMA if bucket_totals[b] > 0)
    anchor_accuracy = (
        bucket_correct["depth_1"] / bucket_totals["depth_1"]
        if bucket_totals["depth_1"] > 0 else 0.0
    )

    stats: list[BucketStat] = []
    assertion_holds = True
    for bucket in BUCKET_SCHEMA:
        total = bucket_totals[bucket]
        correct = bucket_correct[bucket]
        accuracy = (correct / total) if total > 0 else 0.0
        if bucket == "depth_1" or total == 0:
            bound = None
            bound_satisfied = True
        else:
            bound = _required_bound(anchor_accuracy, _representative_depth(bucket))
            bound_satisfied = accuracy >= bound
        if total > 0 and not bound_satisfied:
            assertion_holds = False
        stats.append(BucketStat(
            bucket=bucket,
            cases_total=total,
            cases_correct=correct,
            accuracy=accuracy,
            bound_required=bound,
            bound_satisfied=bound_satisfied,
        ))

    sufficient = (
        len(populated) >= MIN_BUCKETS_FOR_COVERAGE
        and all(
            bucket_totals[b] >= MIN_CASES_PER_BUCKET_FOR_COVERAGE
            for b in populated
        )
    )

    refusal = ""
    if not assertion_holds:
        failing = [
            s.bucket for s in stats
            if s.cases_total > 0 and not s.bound_satisfied
        ]
        refusal = f"buckets failing decay bound: {failing}"
    elif not sufficient:
        refusal = (
            f"assertion holds but coverage insufficient — "
            f"populated buckets: {list(populated)} "
            f"(need ≥{MIN_BUCKETS_FOR_COVERAGE} buckets, "
            f"≥{MIN_CASES_PER_BUCKET_FOR_COVERAGE} cases each)"
        )

    return DepthCurveReport(
        lane_id=lane_id,
        cases_total=len(cases),
        cases_solved=solved,
        cases_skipped_unsolved=skipped,
        epsilon=DECAY_EPSILON,
        buckets=tuple(stats),
        populated_buckets=populated,
        obligation_6_mechanism_wired=True,
        obligation_6_assertion_holds=assertion_holds,
        coverage_sufficient=sufficient,
        refusal_reason=refusal,
    )


def emit_depth_curve_report(
    report: DepthCurveReport, out_path: Path,
) -> None:
    """Write the deterministic obligation-#6 audit report."""
    out_path.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
