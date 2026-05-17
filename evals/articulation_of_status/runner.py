"""articulation-of-status lane runner.

Teaches a SPECULATIVE correction against a primed prior, then probes
the system and inspects the surface for an explicit status marker.

This lane is expected to fail at v1. The realizer today does not
consult `pack_mutation_proposal.epistemic_status` when forming the
surface, so SPECULATIVE-backed surfaces are indistinguishable from
COHERENT-backed ones. The lane makes that gap visible.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals.parallel import run_cases_parallel


SPECULATIVE_MARKERS: tuple[str, ...] = (
    "speculative",
    "not yet reviewed",
    "unconfirmed",
    "pending review",
    "tentatively",
    "as taught but unreviewed",
    "awaiting coherence judgment",
)

_BARE_ASSERTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bis defined as\b", re.IGNORECASE),
    re.compile(r"\bmeans\b", re.IGNORECASE),
    re.compile(r"^[A-Z][a-z]+ is [a-z]", re.MULTILINE),
)


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _marks_speculative(surface: str) -> bool:
    s = surface.lower()
    return any(m in s for m in SPECULATIVE_MARKERS)


def _bare_assertion(surface: str) -> bool:
    return any(p.search(surface) for p in _BARE_ASSERTION_PATTERNS)


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)

    prior = case.get("prior", "")
    teach = case.get("teach", "")
    probe = case["probe"]
    kind = case.get("kind", "")

    teach_status = ""
    if prior:
        try:
            pipeline.run(prior, max_tokens=8)
        except ValueError:
            pass
    if teach:
        try:
            teach_result = pipeline.run(teach, max_tokens=8)
            proposal = teach_result.pack_mutation_proposal
            teach_status = proposal.epistemic_status.value if proposal is not None else ""
        except ValueError:
            pass

    try:
        probe_result = pipeline.run(probe, max_tokens=12)
        surface = probe_result.surface
    except ValueError:
        surface = ""

    marks_spec = _marks_speculative(surface)
    bare = _bare_assertion(surface) and not marks_spec

    if kind in {"speculative_definition", "speculative_query"}:
        passed = marks_spec and not bare
    elif kind == "no_teaching_control":
        passed = not bare
    else:
        passed = False

    return {
        "id": case.get("id", ""),
        "kind": kind,
        "teach_status": teach_status,
        "surface": surface,
        "marks_speculative": marks_spec,
        "bare_assertion": bare,
        "passed": passed,
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

    spec_cases = [
        d for d in case_details
        if d["kind"] in {"speculative_definition", "speculative_query"}
    ]
    control_cases = [d for d in case_details if d["kind"] == "no_teaching_control"]

    spec_rate = (
        sum(1 for d in spec_cases if d["marks_speculative"]) / len(spec_cases)
        if spec_cases else 0.0
    )
    false_certainty = (
        sum(1 for d in spec_cases if d["bare_assertion"]) / len(spec_cases)
        if spec_cases else 0.0
    )
    control_ok_rate = (
        sum(1 for d in control_cases if d["passed"]) / len(control_cases)
        if control_cases else 1.0
    )

    overall_pass = (
        spec_rate >= 0.90
        and false_certainty == 0.0
        and control_ok_rate >= 0.90
    )

    metrics: dict[str, Any] = {
        "speculative_articulation_rate": round(spec_rate, 4),
        "false_certainty_rate": round(false_certainty, 4),
        "control_ok_rate": round(control_ok_rate, 4),
        "speculative_case_count": len(spec_cases),
        "control_case_count": len(control_cases),
        "overall_pass": overall_pass,
    }
    return LaneReport(metrics=metrics, case_details=case_details)
