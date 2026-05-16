"""long-context-cost eval lane runner — Phase 4 quantitative curve.

Times `VaultStore.recall` as a function of stored-entry count N.
Each case in the input list specifies (N, query_count, seed); the
runner generates a synthetic vault of N float32 versors of shape
(32,), runs `query_count` recall queries, and records latency
samples.

The lane aggregates per-N statistics across all cases sharing the
same N (multi-seed CI is v2 work) and publishes:

  - latency curve (median, p95, max, mean) per N
  - log-log linear fit (slope, intercept)
  - asymptotic class label (linear / super-linear)

Replay note: latency itself is not reproducible bit-for-bit, but
the curve shape is.  The lane's structural gate is that recall
returns without exception at every N.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from statistics import mean, median
from typing import Any

import numpy as np

from core.config import RuntimeConfig
from vault.store import VaultStore


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = max(0, min(len(sorted_vals) - 1, int(round((pct / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def _populate_vault(n: int, seed: int) -> VaultStore:
    rng = np.random.default_rng(seed)
    vault = VaultStore(reproject_interval=0)
    # Pre-generate the matrix in one allocation, then append rows. Faster than
    # generating each entry inside the loop.
    batch = rng.standard_normal(size=(n, 32), dtype=np.float32)
    for i in range(n):
        vault.store(batch[i], metadata={"i": i})
    return vault


def _time_recalls(vault: VaultStore, query_count: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed + 1)
    queries = rng.standard_normal(size=(query_count, 32), dtype=np.float32)
    samples: list[float] = []
    for q in queries:
        t0 = time.perf_counter()
        _ = vault.recall(q, top_k=5)
        t1 = time.perf_counter()
        samples.append((t1 - t0) * 1000.0)  # ms
    return samples


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    n = int(case["n"])
    query_count = int(case.get("query_count", 20))
    seed = int(case.get("seed", 0xC07E))

    vault = _populate_vault(n, seed)
    latencies = _time_recalls(vault, query_count, seed)

    return {
        "n": n,
        "query_count": query_count,
        "seed": seed,
        "latency_median_ms": round(median(latencies), 4),
        "latency_p95_ms": round(_percentile(latencies, 95), 4),
        "latency_max_ms": round(max(latencies), 4),
        "latency_mean_ms": round(mean(latencies), 4),
        "passed": True,  # no exception means structurally passing
    }


def _log_log_fit(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Least-squares slope and intercept for log(y) = slope * log(x) + b."""
    if len(points) < 2:
        return 0.0, 0.0
    xs = [math.log(x) for x, _ in points]
    ys = [math.log(y) for _, y in points if y > 0]
    if len(xs) != len(ys):
        return 0.0, 0.0
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((x - mean_x) ** 2 for x in xs) or 1.0
    slope = num / den
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _asymptotic_class(slope: float) -> str:
    if 0.85 <= slope <= 1.15:
        return "linear"
    if slope < 0.85:
        return "sub-linear"
    if 1.85 <= slope <= 2.15:
        return "quadratic"
    return f"super-linear (slope≈{slope:.2f})"


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> LaneReport:
    if not cases:
        return LaneReport(metrics={}, case_details=[])
    _ = config
    _ = workers  # populating 10^6 entries doesn't parallelise cleanly; run serially.

    case_details = [_run_case(c) for c in cases]

    by_n: dict[int, dict[str, float]] = {}
    for d in case_details:
        by_n.setdefault(d["n"], {
            "n": d["n"],
            "latency_median_ms": d["latency_median_ms"],
            "latency_p95_ms": d["latency_p95_ms"],
            "latency_max_ms": d["latency_max_ms"],
            "latency_mean_ms": d["latency_mean_ms"],
        })

    points = [(float(d["n"]), float(d["latency_median_ms"])) for d in by_n.values()]
    points.sort(key=lambda p: p[0])
    slope, intercept = _log_log_fit(points)
    asymptotic = _asymptotic_class(slope)

    metrics: dict[str, Any] = {
        "case_count": len(case_details),
        "n_values": [d["n"] for d in case_details],
        "log_log_slope": round(slope, 4),
        "log_log_intercept": round(intercept, 4),
        "asymptotic_class": asymptotic,
        "curve": [
            {
                "n": int(p[0]),
                "latency_median_ms": p[1],
            }
            for p in points
        ],
        "all_recalls_succeeded": all(d["passed"] for d in case_details),
        "overall_pass": all(d["passed"] for d in case_details),
    }

    return LaneReport(metrics=metrics, case_details=case_details)
