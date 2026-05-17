"""Stage 6 — Run.  Drive a ``FormationPlan`` through the cognitive pipeline.

The Runner is **a thin shim**.  It does not invent operators or pack-mutation
paths; it only invokes a caller-supplied ``pipeline_callable`` per step and
collects the per-step outcomes.  This keeps the Runner testable without a
runtime dependency on ``CognitiveTurnPipeline`` (which would pull in the
entire engine).

Hard halt: any turn whose ``versor_condition`` is reported as ``>= 1e-6``
stops the run.  The runner never repairs or normalizes the field — per
CLAUDE.md, repair belongs in the algebra/operator layer, not the runtime
shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from formation.course import FormationPlan, PlanStep
from formation.ratify import StepResult


# Threshold copied from CLAUDE.md "Non-Negotiable Field Invariant" so the
# Runner halt boundary mirrors the project's global invariant rather than
# embedding a divergent value.
VERSOR_HALT_THRESHOLD: float = 1.0e-6


@dataclass(frozen=True, slots=True)
class TurnObservation:
    """Minimum observation surface required by the Runner.

    The caller's pipeline_callable returns one of these per step.  This
    indirection lets the Runner stay decoupled from
    ``CognitiveTurnResult`` and avoid pulling in the cognitive pipeline at
    import time.
    """

    trace_hash: str
    versor_condition: float
    accepted: bool        # for adversarial probes: True = runtime accepted
                          # the probe (= a *failure*); for legit steps: True
                          # = the runtime accepted the assertion.
    has_provenance: bool


class RunnerHalt(Exception):
    """Raised when a step exceeds the versor halt threshold."""


PipelineCallable = Callable[[PlanStep], TurnObservation]


@dataclass(frozen=True, slots=True)
class RunOutput:
    results: tuple[StepResult, ...]
    halted: bool = False
    halt_step_index: int = -1
    halt_reason: str = ""


def run_plan(
    plan: FormationPlan,
    pipeline: PipelineCallable,
) -> RunOutput:
    """Drive every step of ``plan`` through ``pipeline``; collect ``StepResult``s.

    Hard-halts on the first step whose ``versor_condition >= VERSOR_HALT_THRESHOLD``.
    Returns a ``RunOutput`` describing the partial run; the caller decides
    whether to surface the halt as a failure.
    """
    out: list[StepResult] = []
    for idx, step in enumerate(plan.steps):
        obs = pipeline(step)
        if obs.versor_condition >= VERSOR_HALT_THRESHOLD:
            return RunOutput(
                results=tuple(out),
                halted=True,
                halt_step_index=idx,
                halt_reason=(
                    f"versor_condition {obs.versor_condition!r} >= "
                    f"{VERSOR_HALT_THRESHOLD!r}"
                ),
            )
        out.append(_to_step_result(step, obs))
    return RunOutput(results=tuple(out), halted=False)


def _to_step_result(step: PlanStep, obs: TurnObservation) -> StepResult:
    return StepResult(
        step_type=step.step_type,
        payload=dict(step.payload),
        trace_hash=obs.trace_hash,
        versor_condition_repr=_versor_repr(obs.versor_condition),
        accepted=obs.accepted,
        has_provenance=obs.has_provenance,
    )


def _versor_repr(value: float) -> str:
    """Render a versor condition as a stable string.

    Avoid Python's float repr drift across platforms by formatting via
    ``f"{value:.3e}"`` (three-digit mantissa in scientific notation).  This
    is enough resolution to read in audit logs without leaking precision
    artifacts.
    """
    if value == 0.0:
        return "0.0e+00"
    return f"{value:.3e}"
