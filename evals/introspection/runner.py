"""introspection eval lane runner.

For each case:
  1. Run the prompt on a fresh CognitiveTurnPipeline and capture
     (surface_A, trace_hash_A, turn_id_A).
  2. Attempt to call an `explain(turn_id)` function from
     `core.cognition`.  v1 expects this to raise ImportError; the
     runner catches it and scores M1 = False.
  3. When (2) succeeds, run a fresh pipeline on the produced account
     and capture (surface_B, trace_hash_B).
  4. Score round-trip overlap.

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


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


_TOKEN_BOUND = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_BOUND.findall((text or "").lower()))


def _try_import_explain():
    """Return the explain callable or None when the API is absent."""
    try:
        from core.cognition import explain  # type: ignore[attr-defined]
    except (ImportError, AttributeError):
        return None
    return explain


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    prompt: str = case["prompt"]

    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)
    try:
        result_a = pipeline.run(prompt, max_tokens=12)
    except ValueError:
        return {
            "id": case.get("id", ""),
            "explain_api_present": False,
            "account_nonempty": False,
            "round_trip_surface_match": False,
            "round_trip_trace_match": False,
            "passed": False,
        }

    surface_a = result_a.surface or ""
    trace_a = result_a.trace_hash

    explain = _try_import_explain()
    api_present = explain is not None
    account = ""
    surface_b = ""
    trace_b = ""
    if api_present:
        try:
            account = explain(result_a) or ""  # type: ignore[misc]
        except Exception:
            account = ""
        if account:
            rt2 = ChatRuntime()
            pipe2 = CognitiveTurnPipeline(rt2)
            try:
                result_b = pipe2.run(account, max_tokens=12)
                surface_b = result_b.surface or ""
                trace_b = result_b.trace_hash
            except ValueError:
                pass

    account_nonempty = len(_tokens(account)) >= 5
    a_tokens = _tokens(surface_a)
    b_tokens = _tokens(surface_b)
    if a_tokens:
        coverage = len(a_tokens & b_tokens) / len(a_tokens)
    else:
        coverage = 0.0
    surface_match = coverage >= 0.60
    trace_match = bool(trace_a) and trace_a == trace_b

    passed = api_present and account_nonempty and surface_match

    return {
        "id": case.get("id", ""),
        "explain_api_present": api_present,
        "account_nonempty": account_nonempty,
        "round_trip_surface_match": surface_match,
        "round_trip_trace_match": trace_match,
        "surface_token_coverage": round(coverage, 4),
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
    total = len(case_details)

    api = sum(1 for d in case_details if d["explain_api_present"]) / total
    nonempty = sum(1 for d in case_details if d["account_nonempty"]) / total
    surf = sum(1 for d in case_details if d["round_trip_surface_match"]) / total
    trace = sum(1 for d in case_details if d["round_trip_trace_match"]) / total
    overall = sum(1 for d in case_details if d["passed"]) / total

    overall_pass = api >= 0.95 and nonempty >= 0.95 and surf >= 0.50

    metrics: dict[str, Any] = {
        "explain_api_present_rate": round(api, 4),
        "account_nonempty_rate": round(nonempty, 4),
        "round_trip_surface_match_rate": round(surf, 4),
        "round_trip_trace_match_rate": round(trace, 4),
        "all_pass_rate": round(overall, 4),
        "case_count": total,
        "overall_pass": overall_pass,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
