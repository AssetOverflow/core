"""contradiction-detection lane runner.

Delivers a pair of corrections against the same prior and inspects
the second event for a CONTESTED transition (ADR-0021).

The v1 versor-spike heuristic was retired 2026-05-17 when the
coherence checker in ``TeachingStore.add`` landed: same-subject
proposals with opposing polarity are now transitioned to
``EpistemicStatus.CONTESTED`` at write time, and the lane reads that
directly.  ``versor_delta`` is still reported for telemetry but no
longer drives the flag.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals.parallel import run_cases_parallel
from teaching.epistemic import EpistemicStatus


VERSOR_SPIKE_THRESHOLD = 1e-7


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)

    prior = case.get("prior", "")
    if prior:
        try:
            pipeline.run(prior, max_tokens=8)
        except ValueError:
            pass

    kind = case.get("kind", "")
    first_text = case["first"]
    second_text = case["second"]

    try:
        first_result = pipeline.run(first_text, max_tokens=8)
    except ValueError:
        return _failure_record(case, kind, "value_error_on_first")

    try:
        second_result = pipeline.run(second_text, max_tokens=8)
    except ValueError:
        return _failure_record(case, kind, "value_error_on_second")

    second_proposal = second_result.pack_mutation_proposal
    second_status = (
        second_proposal.epistemic_status if second_proposal is not None else None
    )
    contested = (
        second_status is EpistemicStatus.CONTESTED
        or second_status is EpistemicStatus.FALSIFIED
    )

    versor_delta = abs(
        second_result.versor_condition - first_result.versor_condition
    )
    versor_spike = versor_delta > VERSOR_SPIKE_THRESHOLD

    # Real signal: CONTESTED transition from TeachingStore.add.
    # versor_spike retained in the record for telemetry/debugging only.
    flagged = contested

    if kind == "paired_contradiction":
        passed = flagged
    elif kind == "paired_consistent":
        passed = not flagged
    else:
        passed = False

    return {
        "id": case.get("id", ""),
        "kind": kind,
        "first_versor_condition": round(first_result.versor_condition, 12),
        "second_versor_condition": round(second_result.versor_condition, 12),
        "versor_delta": round(versor_delta, 12),
        "versor_spike": versor_spike,
        "second_epistemic_status": (
            second_status.value if second_status is not None else ""
        ),
        "contested": contested,
        "flagged": flagged,
        "passed": passed,
    }


def _failure_record(case: dict[str, Any], kind: str, why: str) -> dict[str, Any]:
    return {
        "id": case.get("id", ""),
        "kind": kind,
        "first_versor_condition": 0.0,
        "second_versor_condition": 0.0,
        "versor_delta": 0.0,
        "versor_spike": False,
        "second_epistemic_status": why,
        "contested": False,
        "flagged": False,
        "passed": False,
    }


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> LaneReport:
    if not cases:
        return LaneReport(metrics={}, case_details=[])
    _ = config

    case_details = run_cases_parallel(cases, _run_case, workers=workers)

    contradictions = [d for d in case_details if d["kind"] == "paired_contradiction"]
    consistents = [d for d in case_details if d["kind"] == "paired_consistent"]

    flag_rate = (
        sum(1 for d in contradictions if d["flagged"]) / len(contradictions)
        if contradictions else 0.0
    )
    false_flag_rate = (
        sum(1 for d in consistents if d["flagged"]) / len(consistents)
        if consistents else 0.0
    )

    overall_pass = flag_rate >= 0.90 and false_flag_rate == 0.0

    metrics: dict[str, Any] = {
        "contradiction_flag_rate": round(flag_rate, 4),
        "false_flag_rate": round(false_flag_rate, 4),
        "paired_contradiction_count": len(contradictions),
        "paired_consistent_count": len(consistents),
        "overall_pass": overall_pass,
    }
    return LaneReport(metrics=metrics, case_details=case_details)
