"""Monotonic-learning eval lane runner.

Drives a longitudinal teaching protocol through one shared
``CognitiveTurnPipeline`` and records per-cycle, per-domain probe scores
so we can detect regressions in previously taught domains as new ones
accumulate.

Conforms to the framework interface: ``run_lane(cases, config=None) -> report``
where report has ``.metrics`` (dict) and ``.case_details`` (list[dict]).

Sub-metrics:
  M1. max_regression — largest drop in any domain's score relative to its
      first-taught cycle. Must be ≤ 0.05.
  M2. floor_score   — lowest final-cycle score across all taught domains.
                      Must be ≥ 0.80.
  M3. cycle_count   — number of teaching cycles. Must be ≥ 10.

The case JSONL is a flat sequence of ``op`` entries (``probe`` or
``teach``) keyed by ``cycle``; the runner sorts them and replays the
protocol on a single session.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _score_probe(surface: str, expected_terms: list[str]) -> bool:
    lower = surface.lower()
    return all(term.lower() in lower for term in expected_terms)


def _is_teach(op: dict[str, Any]) -> bool:
    return op.get("op") == "teach"


def _is_probe(op: dict[str, Any]) -> bool:
    return op.get("op") == "probe"


def _stable_sort_ops(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order by cycle, then teach-before-probe within a cycle.

    Within a cycle the teach step (if present) must run before that cycle's
    probes so the probe scores reflect post-teach state.
    """
    def key(c: dict[str, Any]) -> tuple[int, int, str]:
        cycle = int(c.get("cycle", 0))
        op_priority = 0 if _is_teach(c) else 1
        # Stable secondary key: id for probes, prompt for teach
        secondary = str(c.get("id") or c.get("prompt") or "")
        return (cycle, op_priority, secondary)

    return sorted(cases, key=key)


def _run_teach(pipeline: CognitiveTurnPipeline, op: dict[str, Any]) -> None:
    for prime_prompt in op.get("prime", []):
        pipeline.run(prime_prompt, max_tokens=8)
    pipeline.run(op["prompt"], max_tokens=8)


def _run_probe(pipeline: CognitiveTurnPipeline, op: dict[str, Any]) -> bool:
    result = pipeline.run(op["prompt"], max_tokens=8)
    return _score_probe(result.surface, op.get("expected_terms", []))


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
) -> LaneReport:
    ops = _stable_sort_ops(cases)
    if not ops:
        return LaneReport(metrics={}, case_details=[])

    runtime = ChatRuntime(config=config) if config else ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)

    # Score table:
    #   scores[cycle][domain] = (correct, total)
    scores: dict[int, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))

    # Track per-(cycle, probe_id) outcome for detailed reporting.
    probe_outcomes: list[dict[str, Any]] = []

    # Tracks which cycle each domain was first taught at (None until taught).
    first_taught: dict[str, int] = {}

    teach_cycles: set[int] = set()

    for op in ops:
        cycle = int(op.get("cycle", 0))
        domain = op.get("domain", "unknown")

        if _is_teach(op):
            teach_cycles.add(cycle)
            if domain not in first_taught:
                first_taught[domain] = cycle
            _run_teach(pipeline, op)
        elif _is_probe(op):
            passed = _run_probe(pipeline, op)
            entry = scores[cycle][domain]
            entry[1] += 1
            if passed:
                entry[0] += 1
            probe_outcomes.append({
                "cycle": cycle,
                "domain": domain,
                "probe_id": op.get("id"),
                "passed": passed,
            })

    cycle_count = len(teach_cycles)
    final_cycle = max(scores.keys()) if scores else 0

    # Compute per-(domain, cycle) accuracy
    def acc(c: int, d: str) -> float:
        e = scores.get(c, {}).get(d)
        if not e or e[1] == 0:
            return float("nan")
        return e[0] / e[1]

    domains = sorted({d for c in scores.values() for d in c.keys()})

    # M1. max_regression: largest drop from a domain's "first-taught" cycle
    # score to any later cycle's score (only for domains that were taught).
    regressions: list[float] = []
    for d in domains:
        if d not in first_taught:
            continue
        baseline = acc(first_taught[d], d)
        if baseline != baseline:  # NaN guard
            continue
        for c in sorted(scores.keys()):
            if c < first_taught[d]:
                continue
            current = acc(c, d)
            if current != current:
                continue
            drop = max(baseline - current, 0.0)
            regressions.append(drop)

    max_regression = max(regressions) if regressions else 0.0

    # M2. floor_score: min final-cycle score across all taught domains
    floor_score: float = 1.0
    for d in domains:
        if d not in first_taught:
            continue
        s = acc(final_cycle, d)
        if s != s:
            continue
        floor_score = min(floor_score, s)
    if not first_taught:
        floor_score = 0.0

    # M3. cycle_count
    cycle_pass = cycle_count >= 10

    overall_pass = (
        max_regression <= 0.05
        and floor_score >= 0.80
        and cycle_pass
    )

    per_cycle: list[dict[str, Any]] = []
    for c in sorted(scores.keys()):
        row: dict[str, Any] = {"cycle": c}
        for d in domains:
            a = acc(c, d)
            row[d] = None if a != a else round(a, 4)
        per_cycle.append(row)

    metrics: dict[str, Any] = {
        "cycle_count": cycle_count,
        "max_regression": round(max_regression, 4),
        "floor_score": round(floor_score, 4),
        "cycle_pass": cycle_pass,
        "overall_pass": overall_pass,
        "domains": domains,
        "first_taught": first_taught,
        "per_cycle_scores": per_cycle,
    }

    case_details = probe_outcomes

    return LaneReport(metrics=metrics, case_details=case_details)
