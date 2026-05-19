"""Warmed-session consistency eval lane runner.

Asymmetric counterpart to ``cold_start_grounding``.  Constructs ONE
runtime + pipeline per case and plays a turn sequence through them,
asserting that pipeline overrides do not corrupt a runtime-grounded
answer and that telemetry-emitted surfaces match the pipeline's
final returned surface.

Framework contract: ``run_lane(cases, config=None) -> LaneReport``
where ``LaneReport.metrics`` is a dict and ``LaneReport.case_details``
is a list of per-case dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline


_PLACEHOLDER_MARKERS = (
    "...",
    "<pending>",
    "<prior>",
    " placeholder ",
)


def _has_placeholder(surface: str) -> bool:
    if not isinstance(surface, str):
        return False
    return any(m in surface for m in _PLACEHOLDER_MARKERS)


@dataclass(frozen=True, slots=True)
class TurnResult:
    turn_index: int
    prompt: str
    surface: str
    grounding_source: str
    expected_grounding_source: str
    grounding_match: bool
    no_placeholder: bool
    telemetry_match: bool


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    invariants: tuple[str, ...]
    turn_results: tuple[TurnResult, ...]
    warm_grounding_stable: bool


@dataclass
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_case(case: dict[str, Any]) -> CaseResult:
    """Run one case's full turn sequence through a single warmed
    runtime + pipeline pair."""
    turns_spec = case.get("turns", [])
    invariants = tuple(case.get("warm_invariants", (
        "no_placeholder", "telemetry_match", "warm_grounding_stability"
    )))

    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime=runtime)

    turn_results: list[TurnResult] = []
    grounding_by_prompt: dict[str, list[str]] = {}

    for idx, turn in enumerate(turns_spec):
        prompt = turn["prompt"]
        expected_grounding = turn["expected_grounding_source"]

        result = pipeline.run(prompt, max_tokens=8)
        actual_surface = result.surface

        # Telemetry match: the most recent entry in runtime.turn_log
        # must carry the same surface that the pipeline returned.
        # Pipeline overrides that happen AFTER turn_log emission would
        # produce a mismatch here.
        last_event = (
            runtime.turn_log[-1] if runtime.turn_log else None
        )
        telemetry_surface = (
            last_event.surface if last_event is not None else ""
        )
        actual_grounding = (
            getattr(last_event, "grounding_source", None) or "none"
            if last_event is not None
            else "none"
        )
        telemetry_match = actual_surface == telemetry_surface

        no_ph = not _has_placeholder(actual_surface)
        grounding_match = actual_grounding == expected_grounding

        turn_results.append(TurnResult(
            turn_index=idx,
            prompt=prompt,
            surface=actual_surface,
            grounding_source=actual_grounding,
            expected_grounding_source=expected_grounding,
            grounding_match=grounding_match,
            no_placeholder=no_ph,
            telemetry_match=telemetry_match,
        ))
        grounding_by_prompt.setdefault(prompt, []).append(actual_grounding)

    # Warm-grounding stability: for any prompt that appears more than
    # once in this case, every replay must produce the same grounding.
    stable = all(
        len(set(srcs)) == 1
        for srcs in grounding_by_prompt.values()
        if len(srcs) > 1
    )

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "uncategorised"),
        invariants=invariants,
        turn_results=tuple(turn_results),
        warm_grounding_stable=stable,
    )


def run_lane(cases: list[dict[str, Any]], config: Any = None) -> LaneReport:  # noqa: ARG001
    if not cases:
        return LaneReport(metrics={}, case_details=[])

    results = [_run_case(c) for c in cases]

    total_turns = sum(len(r.turn_results) for r in results)
    no_ph = sum(
        1 for r in results for t in r.turn_results if t.no_placeholder
    )
    telem_match = sum(
        1 for r in results for t in r.turn_results if t.telemetry_match
    )
    grounding_match = sum(
        1 for r in results for t in r.turn_results if t.grounding_match
    )

    replayable_cases = [
        r for r in results
        if any(
            sum(1 for t in r.turn_results if t.prompt == tp) > 1
            for tp in {t.prompt for t in r.turn_results}
        )
    ]
    stable = sum(1 for r in replayable_cases if r.warm_grounding_stable)

    metrics: dict[str, Any] = {
        "cases": len(results),
        "total_turns": total_turns,
        "no_placeholder_rate": round(no_ph / total_turns, 4) if total_turns else 1.0,
        "telemetry_consistency_rate": round(telem_match / total_turns, 4) if total_turns else 1.0,
        "grounding_match_rate": round(grounding_match / total_turns, 4) if total_turns else 1.0,
        "warm_grounding_stability": (
            round(stable / len(replayable_cases), 4)
            if replayable_cases else 1.0
        ),
    }

    case_details = [
        {
            "case_id": r.case_id,
            "category": r.category,
            "invariants": list(r.invariants),
            "warm_grounding_stable": r.warm_grounding_stable,
            "turns": [
                {
                    "turn_index": t.turn_index,
                    "prompt": t.prompt,
                    "surface": t.surface,
                    "grounding_source": t.grounding_source,
                    "expected_grounding_source": t.expected_grounding_source,
                    "grounding_match": t.grounding_match,
                    "no_placeholder": t.no_placeholder,
                    "telemetry_match": t.telemetry_match,
                }
                for t in r.turn_results
            ],
        }
        for r in results
    ]

    return LaneReport(metrics=metrics, case_details=case_details)


__all__ = ["run_lane", "LaneReport", "CaseResult", "TurnResult"]
