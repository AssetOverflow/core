"""ADR-0119.3 — GSM8K math eval lane runner.

Composes the Phases 1-4 pipeline (parser → solver → verifier → realizer)
into a per-case scoring decision: ``correct`` / ``wrong`` / ``refused`` /
``decoded_unarticulated``.

Outcome categorization (ADR-0114a Obligation #4 — the load-bearing
"refusal is first-class; misparse rate zero" discipline):

| Stage that raised | Outcome | Reason recorded |
|---|---|---|
| ``parse_problem(text)`` raised ``ParseError`` | refused | typed parser error |
| ``solve(graph)`` raised ``SolveError`` | refused | typed solver error |
| ``verify(graph, trace)`` returned ``passed=False`` | wrong | verifier reason |
| ``realize(graph.initial_state, trace)`` raised ``RealizerError`` after verifier pass | decoded_unarticulated | typed realizer error |
| Everything succeeds AND ``trace.answer_value == expected_answer`` AND ``trace.answer_unit == expected_unit`` | correct | empty |
| Everything succeeds BUT answer or unit differs | wrong | "answer/unit mismatch" |

**`wrong == 0` is the gate** — ADR-0114a Obligation #4 requires CORE
to refuse rather than confabulate. A nonzero ``wrong`` count
invalidates the lane regardless of ``correct`` rate. A verified trace
whose surface realization fails is not a wrong answer; it is counted as
``decoded_unarticulated``.

The runner is pure / deterministic: same case set → same
:class:`LaneReport.canonical_bytes()`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from generate.math_candidate_graph import parse_and_solve
from generate.math_parser import ParseError, parse_problem
from generate.math_problem_graph import MathProblemGraph
from generate.math_realizer import RealizerError, realize
from generate.math_solver import SolveError, solve
from generate.math_verifier import verify

DECODED_UNARTICULATED_OUTCOME = "decoded_unarticulated"


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    """Per-case scoring decision with full audit trail."""

    case_id: str
    outcome: str  # "correct" | "wrong" | "refused" | "decoded_unarticulated"
    reason: str
    expected_answer: float
    expected_unit: str
    actual_answer: float | None
    actual_unit: str | None
    trace_hash: str | None
    realized_prose: str | None

    def as_json(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "outcome": self.outcome,
            "reason": self.reason,
            "expected_answer": self.expected_answer,
            "expected_unit": self.expected_unit,
            "actual_answer": self.actual_answer,
            "actual_unit": self.actual_unit,
            "trace_hash": self.trace_hash,
            "realized_prose": self.realized_prose,
        }


@dataclass(slots=True)
class LaneReport:
    """Aggregate lane scoring report.

    Conforms to the framework runner interface (``metrics`` dict +
    ``case_details`` list).
    """

    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)

    def canonical_bytes(self) -> bytes:
        """Deterministic JSON for hashing/byte-equality comparison."""
        payload = {"metrics": self.metrics, "case_details": self.case_details}
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _decoded_unarticulated_outcome(
    *,
    case_id: str,
    reason: str,
    expected_answer: float,
    expected_unit: str,
    actual_answer: float,
    actual_unit: str,
    trace_hash: str,
) -> CaseOutcome:
    return CaseOutcome(
        case_id=case_id,
        outcome=DECODED_UNARTICULATED_OUTCOME,
        reason=reason,
        expected_answer=expected_answer,
        expected_unit=expected_unit,
        actual_answer=actual_answer,
        actual_unit=actual_unit,
        trace_hash=trace_hash,
        realized_prose=None,
    )


def _score_one(case: dict[str, Any]) -> CaseOutcome:
    """Run the full pipeline against one case and classify the outcome."""
    case_id = case["id"]
    expected_answer = case["expected_answer"]
    expected_unit = case["expected_unit"]

    # Stage 1 — parse
    try:
        graph: MathProblemGraph = parse_problem(case["problem"])
    except ParseError as exc:
        return CaseOutcome(
            case_id=case_id,
            outcome="refused",
            reason=f"parser: {exc}",
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=None,
            actual_unit=None,
            trace_hash=None,
            realized_prose=None,
        )

    # Stage 2 — solve
    try:
        trace = solve(graph)
    except SolveError as exc:
        return CaseOutcome(
            case_id=case_id,
            outcome="refused",
            reason=f"solver: {exc}",
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=None,
            actual_unit=None,
            trace_hash=None,
            realized_prose=None,
        )

    # Stage 3 — verify (independent re-derivation)
    verdict = verify(graph, trace)
    trace_hash = hashlib.sha256(trace.canonical_bytes()).hexdigest()

    if not verdict.passed:
        return CaseOutcome(
            case_id=case_id,
            outcome="wrong",
            reason=f"verifier: {verdict.reason}",
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=trace.answer_value,
            actual_unit=trace.answer_unit,
            trace_hash=trace_hash,
            realized_prose=None,
        )

    # Stage 4 — realize. A failure here happens after replay verification,
    # so the answer remains DECODED; only the articulation surface failed.
    try:
        realized = realize(graph.initial_state, trace)
        prose = realized.as_prose()
    except RealizerError as exc:
        return _decoded_unarticulated_outcome(
            case_id=case_id,
            reason=f"realizer: {exc}",
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=trace.answer_value,
            actual_unit=trace.answer_unit,
            trace_hash=trace_hash,
        )

    # Stage 5 — compare against expected.
    # An empty expected_unit ("") means the case carries no unit-level
    # expectation (e.g. the sealed GSM8K test set under ADR-0119.7
    # records pure-number answers without a parsed unit). In that case
    # the runner skips the unit comparison and grades on answer value
    # alone. Cases that DO specify expected_unit get the strict check.
    if expected_unit != "" and trace.answer_unit != expected_unit:
        return CaseOutcome(
            case_id=case_id,
            outcome="wrong",
            reason=(
                f"unit mismatch: got {trace.answer_unit!r}, "
                f"expected {expected_unit!r}"
            ),
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=trace.answer_value,
            actual_unit=trace.answer_unit,
            trace_hash=trace_hash,
            realized_prose=prose,
        )
    if trace.answer_value != expected_answer:
        return CaseOutcome(
            case_id=case_id,
            outcome="wrong",
            reason=(
                f"answer mismatch: got {trace.answer_value!r}, "
                f"expected {expected_answer!r}"
            ),
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=trace.answer_value,
            actual_unit=trace.answer_unit,
            trace_hash=trace_hash,
            realized_prose=prose,
        )

    return CaseOutcome(
        case_id=case_id,
        outcome="correct",
        reason="",
        expected_answer=expected_answer,
        expected_unit=expected_unit,
        actual_answer=trace.answer_value,
        actual_unit=trace.answer_unit,
        trace_hash=trace_hash,
        realized_prose=prose,
    )


# TODO(ADR-future): report.json metrics may not credit candidate-graph admissions
# routed through this branch. Aggregation in calling code needs an audit before
# the canonical run.honest_runner.json artifact can be trusted for cross-phase comparison.
def _score_one_candidate_graph(case: dict[str, Any]) -> CaseOutcome:
    """ADR-0126 P4 — score one case via the candidate-graph pipeline.

    Mirrors :func:`_score_one` end-to-end (parser → solver → verifier →
    realizer → expected-answer check) but the parse stage uses
    :func:`generate.math_candidate_graph.parse_and_solve` instead of
    the first-match-wins :func:`generate.math_parser.parse_problem`.

    Preserves wrong == 0: any deviation in the new pipeline still
    routes through the same verifier-replay + answer/unit equality
    checks. Refusals are first-class — branches with no admissible
    parse, branches that disagree on the answer, and branches that
    exceed MAX_TOTAL_BRANCHES all classify as ``refused``.

    Callers that want to evaluate the candidate-graph topology
    (e.g. ``evals/gsm8k_math/train_sample/v1/runner.py`` from PR
    #160) substitute this function for ``_score_one``; the
    ``CaseOutcome`` shape is identical.
    """
    case_id = case["id"]
    expected_answer = case["expected_answer"]
    expected_unit = case["expected_unit"]

    # Stage 1 — candidate-graph parse + internal solve + decision rule.
    cg_result = parse_and_solve(case["problem"])
    if not cg_result.is_admitted:
        return CaseOutcome(
            case_id=case_id,
            outcome="refused",
            reason=f"candidate_graph: {cg_result.refusal_reason}",
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=None,
            actual_unit=None,
            trace_hash=None,
            realized_prose=None,
        )
    graph = cg_result.selected_graph
    assert graph is not None  # is_admitted implies non-None graph

    # Stage 2 — canonical solve for the full SolutionTrace (verifier
    # needs the trace; parse_and_solve only kept the numeric answer).
    try:
        trace = solve(graph)
    except SolveError as exc:
        return CaseOutcome(
            case_id=case_id,
            outcome="refused",
            reason=f"solver: {exc}",
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=None,
            actual_unit=None,
            trace_hash=None,
            realized_prose=None,
        )

    # Stage 3 — verify (independent re-derivation, ADR-0117).
    verdict = verify(graph, trace)
    trace_hash = hashlib.sha256(trace.canonical_bytes()).hexdigest()
    if not verdict.passed:
        return CaseOutcome(
            case_id=case_id,
            outcome="wrong",
            reason=f"verifier: {verdict.reason}",
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=trace.answer_value,
            actual_unit=trace.answer_unit,
            trace_hash=trace_hash,
            realized_prose=None,
        )

    # Stage 4 — realize. A failure here happens after replay verification,
    # so the answer remains DECODED; only the articulation surface failed.
    try:
        realized = realize(graph.initial_state, trace)
        prose = realized.as_prose()
    except RealizerError as exc:
        return _decoded_unarticulated_outcome(
            case_id=case_id,
            reason=f"realizer: {exc}",
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=trace.answer_value,
            actual_unit=trace.answer_unit,
            trace_hash=trace_hash,
        )

    # Stage 5 — expected-answer comparison (same logic as _score_one).
    if expected_unit != "" and trace.answer_unit != expected_unit:
        return CaseOutcome(
            case_id=case_id,
            outcome="wrong",
            reason=(
                f"unit mismatch: got {trace.answer_unit!r}, "
                f"expected {expected_unit!r}"
            ),
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=trace.answer_value,
            actual_unit=trace.answer_unit,
            trace_hash=trace_hash,
            realized_prose=prose,
        )
    if trace.answer_value != expected_answer:
        return CaseOutcome(
            case_id=case_id,
            outcome="wrong",
            reason=(
                f"answer mismatch: got {trace.answer_value!r}, "
                f"expected {expected_answer!r}"
            ),
            expected_answer=expected_answer,
            expected_unit=expected_unit,
            actual_answer=trace.answer_value,
            actual_unit=trace.answer_unit,
            trace_hash=trace_hash,
            realized_prose=prose,
        )

    return CaseOutcome(
        case_id=case_id,
        outcome="correct",
        reason="",
        expected_answer=expected_answer,
        expected_unit=expected_unit,
        actual_answer=trace.answer_value,
        actual_unit=trace.answer_unit,
        trace_hash=trace_hash,
        realized_prose=prose,
    )


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: Any = None,  # noqa: ARG001 — framework interface compat
) -> LaneReport:
    """Score every case and emit aggregate metrics + per-case details.

    The runner is pure: no globals, no I/O. Returns a
    :class:`LaneReport` whose ``canonical_bytes()`` is byte-equal across
    two calls with the same input list.

    Aggregate metrics:
        cases_total             int
        correct                 int
        wrong                   int     (gate: must == 0)
        refused                 int
        decoded_unarticulated   int
        correct_rate            float   = correct / total
        wrong_rate              float   = wrong / total
        refused_rate            float   = refused / total
        decoded_unarticulated_rate float = decoded_unarticulated / total
        wrong_count_is_zero     bool    = wrong == 0
        overall_pass            bool    = wrong == 0 AND correct + refused + decoded_unarticulated == total
    """
    outcomes = [_score_one(c) for c in cases]

    total = len(outcomes)
    correct = sum(1 for o in outcomes if o.outcome == "correct")
    wrong = sum(1 for o in outcomes if o.outcome == "wrong")
    refused = sum(1 for o in outcomes if o.outcome == "refused")
    decoded_unarticulated = sum(
        1 for o in outcomes if o.outcome == DECODED_UNARTICULATED_OUTCOME
    )

    wrong_count_is_zero = wrong == 0
    overall_pass = wrong_count_is_zero and (
        correct + refused + decoded_unarticulated == total
    )

    metrics = {
        "cases_total": total,
        "correct": correct,
        "wrong": wrong,
        "refused": refused,
        "decoded_unarticulated": decoded_unarticulated,
        "correct_rate": (correct / total) if total else 0.0,
        "wrong_rate": (wrong / total) if total else 0.0,
        "refused_rate": (refused / total) if total else 0.0,
        "decoded_unarticulated_rate": (
            decoded_unarticulated / total
        ) if total else 0.0,
        "wrong_count_is_zero": wrong_count_is_zero,
        "overall_pass": overall_pass,
    }

    report = LaneReport()
    report.metrics = metrics
    report.case_details = [o.as_json() for o in outcomes]
    return report
