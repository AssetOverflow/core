"""Phase 2 corpus-observation runner — ADR-0024 inner-loop admissibility.

Runs each FSC case through a four-condition matrix on the *same*
field state so any pass-rate delta is attributable to the inner-loop
mechanism alone (region/vocab/persona/prompt held constant):

    (A) boundary_only       — inner_loop_admissibility=False
    (B) null_control        — inner_loop_admissibility=True,
                              inner_loop_force_admit=True
    (C) inner_loop_t0       — inner_loop_admissibility=True,
                              admissibility_threshold=0.0
    (D) inner_loop_tpos     — inner_loop_admissibility=True,
                              admissibility_threshold=0.25

Reports per condition:
    pass_rate
    mean_rejection_count_per_turn
    non_empty_rejected_attempts_rate
    exhaustion_rate                  (gated: must be ≤ EXHAUSTION_CEILING)
    mean_admissibility_checks_per_turn
    mean_added_latency_ms
    p95_added_latency_ms
    trace_hash_stability_passes      (5 reruns ⇒ identical trace hash)

Causal attribution: delta(C - A) is the rejection effect *iff* delta(B - A) ≈ 0.
If null_control diverges from boundary_only, the inner-loop code path
itself is changing selection (call ordering, side effects); ADR-0024
proof is contaminated until that residual is explained.

Conforms to the framework interface (``run_lane``) so the standard
eval harness can call it.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from algebra.cga import outer_product
from chat.runtime import ChatRuntime
from core.cognition.trace import hash_admissibility_trace
from core.config import RuntimeConfig
from generate.admissibility import AdmissibilityRegion, RegionSource
from generate.result import GenerationResult
from generate.stream import generate as generate_walk

# Exhaustion ceiling on benign v1 corpus.  Above this, the configured
# threshold is producing honest refusals where it should produce
# answers — a capability regression disguised as a virtue.
EXHAUSTION_CEILING = 0.05

# Default tested-positive threshold for condition (D).  Phase 4 will
# characterise the threshold landscape; this is a probe-point only.
PROBE_THRESHOLD_POSITIVE = 0.25

# Reruns for hash-stability check.  5 is the same N used by the
# Phase 1 acceptance test in ``tests/test_inner_loop_admissibility.py``.
HASH_STABILITY_RERUNS = 5


@dataclass(slots=True)
class _ConditionMetrics:
    label: str
    pass_count: int = 0
    case_count: int = 0
    rejection_counts: list[int] = field(default_factory=list)
    non_empty_rejection_cases: int = 0
    exhaustions: int = 0
    admissibility_checks: list[int] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)
    trace_hash_stable_count: int = 0
    trace_hash_checked_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        n = max(self.case_count, 1)
        return {
            "label": self.label,
            "pass_rate": round(self.pass_count / n, 4),
            "mean_rejection_count_per_turn": round(
                statistics.mean(self.rejection_counts) if self.rejection_counts else 0.0,
                4,
            ),
            "non_empty_rejected_attempts_rate": round(
                self.non_empty_rejection_cases / n, 4
            ),
            "exhaustion_rate": round(self.exhaustions / n, 4),
            "mean_admissibility_checks_per_turn": round(
                statistics.mean(self.admissibility_checks)
                if self.admissibility_checks
                else 0.0,
                4,
            ),
            "mean_added_latency_ms": round(
                statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0, 4
            ),
            "p95_added_latency_ms": round(_p95(self.latencies_ms), 4),
            "trace_hash_stability_pass_rate": round(
                self.trace_hash_stable_count / max(self.trace_hash_checked_count, 1), 4
            ),
            "case_count": self.case_count,
        }


@dataclass(slots=True)
class InnerLoopReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = int(round(0.95 * (len(sorted_values) - 1)))
    return sorted_values[idx]


def _region_from_token_chain(
    vocab,
    tokens: tuple[str, ...],
    *,
    label: str,
) -> AdmissibilityRegion | None:
    indices: list[int] = []
    versors: list[np.ndarray] = []
    for raw in tokens:
        token = raw.lower().strip()
        if not token:
            continue
        try:
            idx = vocab.index_of(token)
        except (KeyError, AttributeError, IndexError):
            continue
        try:
            versor = np.asarray(vocab.get_versor(token), dtype=np.float32)
        except (KeyError, AttributeError):
            continue
        indices.append(int(idx))
        versors.append(versor)
    if not indices:
        return None
    blade = versors[0]
    for nxt in versors[1:]:
        blade = outer_product(blade, nxt)
    return AdmissibilityRegion(
        allowed_indices=np.asarray(indices, dtype=np.int64),
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=label,
    )


def _surfaces_endpoint(surface: str, expected_endpoint: str) -> bool:
    if not surface or not expected_endpoint:
        return False
    return expected_endpoint.lower().strip() in surface.lower()


def _run_walk(
    field_state,
    vocab,
    persona,
    region: AdmissibilityRegion | None,
    *,
    inner_loop: bool,
    threshold: float,
    force_admit: bool,
) -> tuple[GenerationResult | None, float, bool]:
    """Run one walk, return (result, latency_ms, exhaustion_occurred)."""
    start = time.perf_counter()
    try:
        result = generate_walk(
            field_state,
            vocab,
            persona,
            max_tokens=8,
            region=region,
            inner_loop_admissibility=inner_loop,
            admissibility_threshold=threshold,
            inner_loop_force_admit=force_admit,
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        return result, latency_ms, False
    except ValueError:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return None, latency_ms, True


def _rejection_count(result: GenerationResult | None) -> int:
    if result is None:
        return 0
    return sum(len(step.rejected_attempts) for step in result.admissibility_trace)


def _admissibility_check_count(result: GenerationResult | None) -> int:
    """One check per attempt — admissions + rejections."""
    if result is None:
        return 0
    return sum(len(step.rejected_attempts) + 1 for step in result.admissibility_trace)


def _surface_from(result: GenerationResult | None) -> str:
    if result is None or not result.tokens:
        return ""
    return " ".join(result.tokens)


def _hash_of(result: GenerationResult | None) -> str:
    if result is None:
        return "__exhausted__"
    return hash_admissibility_trace(result.admissibility_trace)


def _prime_runtime(case: dict[str, Any]) -> ChatRuntime:
    runtime = ChatRuntime()
    for prime in case.get("prime", []):
        try:
            runtime.chat(prime, max_tokens=8)
        except ValueError:
            pass
    try:
        runtime.chat(case["prompt"], max_tokens=8)
    except ValueError:
        pass
    return runtime


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected_endpoint", "")
    runtime = _prime_runtime(case)
    field_state = runtime.session.state
    if field_state is None:
        return {"id": case.get("id", ""), "skipped": True, "reason": "no_field_state"}

    vocab = runtime.session.vocab
    persona = runtime.session.persona

    chain_tokens = tuple(case.get("chain_tokens", ()))
    if not chain_tokens and expected:
        chain_tokens = (expected,)
    region = _region_from_token_chain(
        vocab, chain_tokens, label=f"phase2[{case.get('id', '')}]"
    )
    if region is None:
        return {"id": case.get("id", ""), "skipped": True, "reason": "no_grounded_chain"}

    # Boundary-only baseline latency — used so reported "added" latency
    # is the cost over the boundary-only path, not absolute.
    baseline_result, baseline_latency_ms, baseline_exh = _run_walk(
        field_state, vocab, persona, region,
        inner_loop=False, threshold=0.0, force_admit=False,
    )

    conditions: dict[str, dict[str, Any]] = {}
    hash_stability: dict[str, bool] = {}

    # (A) boundary-only — recorded above
    conditions["boundary_only"] = {
        "surface": _surface_from(baseline_result),
        "rejections": _rejection_count(baseline_result),
        "checks": _admissibility_check_count(baseline_result),
        "latency_ms": 0.0,  # baseline — no "added" latency
        "absolute_latency_ms": baseline_latency_ms,
        "exhausted": baseline_exh,
        "trace_hash": _hash_of(baseline_result),
    }

    # (B) null_control
    nc_result, nc_latency_ms, nc_exh = _run_walk(
        field_state, vocab, persona, region,
        inner_loop=True, threshold=0.0, force_admit=True,
    )
    conditions["null_control"] = {
        "surface": _surface_from(nc_result),
        "rejections": _rejection_count(nc_result),
        "checks": _admissibility_check_count(nc_result),
        "latency_ms": max(nc_latency_ms - baseline_latency_ms, 0.0),
        "absolute_latency_ms": nc_latency_ms,
        "exhausted": nc_exh,
        "trace_hash": _hash_of(nc_result),
    }

    # (C) inner_loop_t0
    c_result, c_latency_ms, c_exh = _run_walk(
        field_state, vocab, persona, region,
        inner_loop=True, threshold=0.0, force_admit=False,
    )
    conditions["inner_loop_t0"] = {
        "surface": _surface_from(c_result),
        "rejections": _rejection_count(c_result),
        "checks": _admissibility_check_count(c_result),
        "latency_ms": max(c_latency_ms - baseline_latency_ms, 0.0),
        "absolute_latency_ms": c_latency_ms,
        "exhausted": c_exh,
        "trace_hash": _hash_of(c_result),
    }

    # (D) inner_loop_tpos
    d_result, d_latency_ms, d_exh = _run_walk(
        field_state, vocab, persona, region,
        inner_loop=True, threshold=PROBE_THRESHOLD_POSITIVE, force_admit=False,
    )
    conditions["inner_loop_tpos"] = {
        "surface": _surface_from(d_result),
        "rejections": _rejection_count(d_result),
        "checks": _admissibility_check_count(d_result),
        "latency_ms": max(d_latency_ms - baseline_latency_ms, 0.0),
        "absolute_latency_ms": d_latency_ms,
        "exhausted": d_exh,
        "trace_hash": _hash_of(d_result),
    }

    # Hash stability: rerun condition (C) HASH_STABILITY_RERUNS-1 more
    # times on the *same* field state (re-priming each time to keep
    # vault state comparable).  All hashes must match.
    base_hash = conditions["inner_loop_t0"]["trace_hash"]
    stable = True
    for _ in range(HASH_STABILITY_RERUNS - 1):
        re_runtime = _prime_runtime(case)
        re_state = re_runtime.session.state
        if re_state is None:
            stable = False
            break
        re_vocab = re_runtime.session.vocab
        re_persona = re_runtime.session.persona
        re_region = _region_from_token_chain(
            re_vocab, chain_tokens, label=f"phase2[{case.get('id', '')}]"
        )
        if re_region is None:
            stable = False
            break
        re_result, _re_latency, _re_exh = _run_walk(
            re_state, re_vocab, re_persona, re_region,
            inner_loop=True, threshold=0.0, force_admit=False,
        )
        if _hash_of(re_result) != base_hash:
            stable = False
            break
    hash_stability["inner_loop_t0"] = stable

    detail: dict[str, Any] = {
        "id": case.get("id", ""),
        "kind": case.get("kind", ""),
        "expected_endpoint": expected,
        "conditions": conditions,
        "hash_stability": hash_stability,
        "passes": {
            label: _surfaces_endpoint(cond["surface"], expected)
            for label, cond in conditions.items()
        },
    }
    return detail


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> InnerLoopReport:
    _ = config
    _ = workers  # serial — Phase 2 is small and latency-sensitive

    if not cases:
        return InnerLoopReport(metrics={}, case_details=[])

    case_details: list[dict[str, Any]] = []
    by_condition: dict[str, _ConditionMetrics] = {
        "boundary_only": _ConditionMetrics(label="boundary_only"),
        "null_control": _ConditionMetrics(label="null_control"),
        "inner_loop_t0": _ConditionMetrics(label="inner_loop_t0"),
        "inner_loop_tpos": _ConditionMetrics(label="inner_loop_tpos"),
    }

    for case in cases:
        detail = _run_case(case)
        case_details.append(detail)
        if detail.get("skipped"):
            continue
        for label, metrics in by_condition.items():
            cond = detail["conditions"][label]
            metrics.case_count += 1
            if detail["passes"][label]:
                metrics.pass_count += 1
            metrics.rejection_counts.append(cond["rejections"])
            if cond["rejections"] > 0:
                metrics.non_empty_rejection_cases += 1
            if cond["exhausted"]:
                metrics.exhaustions += 1
            metrics.admissibility_checks.append(cond["checks"])
            metrics.latencies_ms.append(cond["latency_ms"])
            if label in detail["hash_stability"]:
                metrics.trace_hash_checked_count += 1
                if detail["hash_stability"][label]:
                    metrics.trace_hash_stable_count += 1

    per_condition = {label: m.as_dict() for label, m in by_condition.items()}

    # Causal attribution:
    #   rejection_effect = pass(inner_loop_t0) - pass(boundary_only)
    #   code_path_residual = pass(null_control) - pass(boundary_only)
    # If |code_path_residual| is non-zero, the rejection effect is
    # contaminated by code-path differences and the proof is invalid.
    rejection_effect = (
        per_condition["inner_loop_t0"]["pass_rate"]
        - per_condition["boundary_only"]["pass_rate"]
    )
    code_path_residual = (
        per_condition["null_control"]["pass_rate"]
        - per_condition["boundary_only"]["pass_rate"]
    )

    # Exhaustion gate — applies to inner-loop conditions only.
    exhaustion_gate_pass = all(
        per_condition[label]["exhaustion_rate"] <= EXHAUSTION_CEILING
        for label in ("inner_loop_t0", "inner_loop_tpos")
    )

    metrics: dict[str, Any] = {
        "per_condition": per_condition,
        "rejection_effect": round(rejection_effect, 4),
        "code_path_residual": round(code_path_residual, 4),
        "causal_attribution_valid": abs(code_path_residual) < 1e-9,
        "exhaustion_ceiling": EXHAUSTION_CEILING,
        "exhaustion_gate_pass": exhaustion_gate_pass,
        "probe_threshold_positive": PROBE_THRESHOLD_POSITIVE,
        "case_count": len(cases),
        "skipped_count": sum(1 for d in case_details if d.get("skipped")),
    }
    return InnerLoopReport(metrics=metrics, case_details=case_details)
