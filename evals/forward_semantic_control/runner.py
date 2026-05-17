"""forward-semantic-control lane runner.

The lane measures whether the proposition graph causally constrains
field propagation (ADR-0022).  Each case has a `prime` chain that
the constrained walk must follow to surface ``expected_endpoint``;
the *unconstrained* baseline is also recorded so the lane can
compute the ``causality_gap`` metric the contract requires.

v1 status: the constrained-walk path is not yet wired through the
runtime.  This runner exercises both legs against the *current*
runtime (i.e. both legs are unconstrained today), so the report
reads ``overall_pass=false`` and the metrics expose the size of the
gap that ADR-0022's implementation must close.

Conforms to the framework interface: ``run_lane(cases, config=None) -> report``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals.parallel import run_cases_parallel


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _surfaces_endpoint(surface: str, expected_endpoint: str) -> bool:
    if not surface or not expected_endpoint:
        return False
    needle = expected_endpoint.lower().strip()
    return needle in surface.lower()


def _surfaces_forbidden(surface: str, forbidden_token: str | None) -> bool:
    if not surface or not forbidden_token:
        return False
    return forbidden_token.lower().strip() in surface.lower()


def _run_leg(case: dict[str, Any], *, constrained: bool) -> str:
    """Run the case once.

    * ``constrained=True``  → full ``CognitiveTurnPipeline`` with
      ADR-0022 forward semantic control: intent is ratified against
      the field, the typed-operator (transitive_walk / compose)
      fold is bounded by the intent's admissible region, and
      empty-set conditions trigger honest refusal.
    * ``constrained=False`` → bare ``ChatRuntime.chat()`` baseline:
      no pipeline, no ratification, no typed-operator fold.  This
      is the "unconstrained walk" the ADR's causality_gap metric
      measures the bridge against.

    Both legs share the same prime / probe sequence so the only
    difference is whether forward semantic control is applied.
    """
    runtime = ChatRuntime()
    if constrained:
        pipeline = CognitiveTurnPipeline(runtime)
        for prime in case.get("prime", []):
            try:
                pipeline.run(prime, max_tokens=8)
            except ValueError:
                pass
        try:
            result = pipeline.run(case["prompt"], max_tokens=8)
            return result.surface or ""
        except ValueError:
            return ""
    # Unconstrained baseline — bare runtime, no graph, no ratifier,
    # no typed-operator fold.  Primes are fed through the same
    # `runtime.chat` entry so the vault state is comparable.
    for prime in case.get("prime", []):
        try:
            runtime.chat(prime, max_tokens=8)
        except ValueError:
            pass
    try:
        response = runtime.chat(case["prompt"], max_tokens=8)
        return response.surface or ""
    except ValueError:
        return ""


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected_endpoint", "")
    forbidden = case.get("forbidden_token")

    unconstrained_surface = _run_leg(case, constrained=False)
    constrained_surface = _run_leg(case, constrained=True)

    unconstrained_pass = _surfaces_endpoint(unconstrained_surface, expected)
    constrained_pass = _surfaces_endpoint(constrained_surface, expected)
    if forbidden:
        constrained_pass = constrained_pass and not _surfaces_forbidden(
            constrained_surface, forbidden
        )

    return {
        "id": case.get("id", ""),
        "kind": case.get("kind", ""),
        "prompt": case["prompt"],
        "expected_endpoint": expected,
        "unconstrained_surface": unconstrained_surface,
        "constrained_surface": constrained_surface,
        "unconstrained_pass": unconstrained_pass,
        "constrained_pass": constrained_pass,
        "baseline_must_fail": bool(case.get("baseline_must_fail", False)),
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

    chain_dependent = [d for d in case_details if d["baseline_must_fail"]]
    negative_controls = [d for d in case_details if not d["baseline_must_fail"]]

    constrained_pass_rate = (
        sum(1 for d in chain_dependent if d["constrained_pass"]) / len(chain_dependent)
        if chain_dependent
        else 0.0
    )
    unconstrained_pass_rate = (
        sum(1 for d in chain_dependent if d["unconstrained_pass"]) / len(chain_dependent)
        if chain_dependent
        else 0.0
    )
    coincidence_rate = (
        sum(1 for d in negative_controls if d["unconstrained_pass"])
        / len(negative_controls)
        if negative_controls
        else 0.0
    )
    causality_gap = constrained_pass_rate - unconstrained_pass_rate

    overall_pass = constrained_pass_rate >= 0.80 and causality_gap > 0.50

    metrics: dict[str, Any] = {
        "constrained_pass_rate": round(constrained_pass_rate, 4),
        "unconstrained_pass_rate": round(unconstrained_pass_rate, 4),
        "coincidence_rate": round(coincidence_rate, 4),
        "causality_gap": round(causality_gap, 4),
        "chain_dependent_count": len(chain_dependent),
        "negative_control_count": len(negative_controls),
        "overall_pass": overall_pass,
    }
    return LaneReport(metrics=metrics, case_details=case_details)
