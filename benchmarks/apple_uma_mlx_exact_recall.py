"""Benchmark-only MLX exact CGA recall experiment.

ADR-0235 Lane 3: optional MLX score-vector experiment for CORE's exact
Cl(4,1) CGA recall workload.  This module does not serve answers, does not
replace Python/Rust as semantic source of truth, does not use ANN, and does not
claim MLX as a runtime backend.

The MLX path computes the exact diagonal CGA score vector over deterministic
(N, 32) float32 fixtures.  Scores are copied back to NumPy for the same stable
canonical top-k ordering used by the Python/Rust exact-recall oracle.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from benchmarks.apple_uma_mechanical_sympathy import (
    DEFAULT_MEASURED,
    DEFAULT_WARMUP,
    N_COMPONENTS,
    RECALL_N_VALUES,
    RECALL_TOP_K,
    synthetic_matrix,
    synthetic_mv,
)

BENCHMARK_NAME = "CORE Apple Silicon MLX Exact CGA Recall Experiment"
BENCHMARK_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class TimingStats:
    warmup_iterations: int
    measured_iterations: int
    min_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float
    mean_ms: float
    ops_per_sec: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "warmup_iterations": self.warmup_iterations,
            "measured_iterations": self.measured_iterations,
            "min_ms": round(self.min_ms, 6),
            "p50_ms": round(self.p50_ms, 6),
            "p95_ms": round(self.p95_ms, 6),
            "max_ms": round(self.max_ms, 6),
            "mean_ms": round(self.mean_ms, 6),
            "ops_per_sec": round(self.ops_per_sec, 3),
        }


def _measure_timing(
    fn: Callable[[], Any],
    *,
    warmup: int = DEFAULT_WARMUP,
    measured: int = DEFAULT_MEASURED,
) -> TimingStats:
    for _ in range(warmup):
        fn()
    samples_ms: list[float] = []
    for _ in range(measured):
        t0 = time.perf_counter()
        fn()
        samples_ms.append((time.perf_counter() - t0) * 1000.0)
    samples_ms.sort()
    p95_index = max(0, int(round(0.95 * (len(samples_ms) - 1))))
    mean_ms = float(np.mean(samples_ms))
    return TimingStats(
        warmup_iterations=warmup,
        measured_iterations=measured,
        min_ms=samples_ms[0],
        p50_ms=float(np.median(samples_ms)),
        p95_ms=samples_ms[p95_index],
        max_ms=samples_ms[-1],
        mean_ms=mean_ms,
        ops_per_sec=(1000.0 / mean_ms) if mean_ms > 0 else 0.0,
    )


def mlx_import_status() -> dict[str, Any]:
    """Return optional MLX availability without making it a dependency."""
    try:
        import mlx  # type: ignore[import-not-found]
        import mlx.core as mx  # type: ignore[import-not-found]
    except ImportError as exc:
        return {"import_succeeded": False, "reason": str(exc)}
    except Exception as exc:
        return {"import_succeeded": False, "reason": f"MLX import failed: {exc}"}

    status: dict[str, Any] = {
        "import_succeeded": True,
        "module": "mlx.core",
        "version": getattr(mlx, "__version__", None),
        "benchmark_only": True,
        "serving_authorized": False,
    }
    try:
        status["default_device"] = str(mx.default_device())
    except Exception as exc:
        status["default_device_error"] = str(exc)
    return status


def _stable_top_k_from_scores(scores: np.ndarray, top_k: int) -> list[tuple[int, float]]:
    scores = np.asarray(scores, dtype=np.float32)
    k = min(top_k, scores.shape[0])
    if k <= 0:
        return []
    if k < scores.shape[0]:
        cand = np.argpartition(-scores, k - 1)[:k]
    else:
        cand = np.arange(scores.shape[0])
    order = np.lexsort((cand, -scores[cand]))
    cand = cand[order]
    return [(int(i), float(scores[i])) for i in cand]


def _cga_inner_metric() -> np.ndarray:
    from algebra import backend as alg_backend

    metric = getattr(alg_backend, "_CGA_INNER_METRIC")
    return np.asarray(metric, dtype=np.float32)


def mlx_exact_score_vector(matrix: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Compute exact CGA recall scores with MLX, then copy scores to NumPy.

    This intentionally performs only the score-vector workload in MLX.  The
    stable top-k ordering remains canonical NumPy/Python to avoid depending on
    MLX top-k API details and to preserve CORE's deterministic ordering rule.
    """
    import mlx.core as mx  # type: ignore[import-not-found]

    matrix_f32 = np.ascontiguousarray(matrix, dtype=np.float32)
    query_f32 = np.ascontiguousarray(query, dtype=np.float32)
    metric_f32 = np.ascontiguousarray(_cga_inner_metric(), dtype=np.float32)

    mx_matrix = mx.array(matrix_f32)
    mx_query = mx.array(query_f32)
    mx_metric = mx.array(metric_f32)
    scores = mx.zeros((matrix_f32.shape[0],), dtype=mx.float32)
    for i in range(N_COMPONENTS):
        scores = scores + (mx_metric[i] * mx_matrix[:, i]) * mx_query[i]
    eval_fn = getattr(mx, "eval", None)
    if callable(eval_fn):
        eval_fn(scores)
    return np.asarray(scores, dtype=np.float32)


def _parity_report(
    *,
    canonical: list[tuple[int, float]],
    candidate: list[tuple[int, float]],
) -> dict[str, Any]:
    canonical_indices = [i for i, _ in canonical]
    candidate_indices = [i for i, _ in candidate]
    deltas = [abs(float(a[1]) - float(b[1])) for a, b in zip(canonical, candidate)]
    max_abs_score_delta = max(deltas) if deltas else 0.0
    return {
        "top_k_indices_match": canonical_indices == candidate_indices,
        "max_abs_score_delta": round(float(max_abs_score_delta), 8),
        "scores_close": bool(max_abs_score_delta <= 1e-4),
        "parity_pass": canonical_indices == candidate_indices and max_abs_score_delta <= 1e-4,
    }


def run_mlx_exact_recall_experiment(
    *,
    warmup: int = DEFAULT_WARMUP,
    measured: int = DEFAULT_MEASURED,
    mlx_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from algebra import backend as alg_backend

    status = mlx_status or mlx_import_status()
    if not status.get("import_succeeded"):
        return {
            "benchmark_name": BENCHMARK_NAME,
            "benchmark_version": BENCHMARK_VERSION,
            "track": "mlx_exact_cga_recall",
            "skipped": True,
            "reason": f"MLX unavailable: {status.get('reason', 'mlx.core import failed')}",
            "mlx_status": status,
            "benchmark_only": True,
            "serving_authorized": False,
            "semantic_backend": "python/rust canonical exact recall",
            "non_claims": [
                "No MLX semantic-backend claim.",
                "No serving integration.",
                "No ANN or approximate recall.",
                "No CoreML or Neural Engine claim.",
            ],
        }

    cases: list[dict[str, Any]] = []
    for n in RECALL_N_VALUES:
        matrix = synthetic_matrix(n, seed=n % 17)
        query = synthetic_mv(seed=5)
        canonical = alg_backend.vault_recall(
            [],
            query,
            top_k=RECALL_TOP_K,
            prebuilt_matrix=matrix,
        )

        def _run_scores() -> np.ndarray:
            return mlx_exact_score_vector(matrix, query)

        timing = _measure_timing(_run_scores, warmup=warmup, measured=measured)
        scores = _run_scores()
        candidate = _stable_top_k_from_scores(scores, RECALL_TOP_K)
        parity = _parity_report(canonical=canonical, candidate=candidate)
        rows_per_sec = (n / (timing.mean_ms / 1000.0)) if timing.mean_ms > 0 else 0.0
        cases.append(
            {
                "N": n,
                "top_k": RECALL_TOP_K,
                "dtype": "float32",
                "contiguous": bool(matrix.flags["C_CONTIGUOUS"]),
                "backend_used": "mlx",
                "semantic_backend": "canonical exact recall via algebra.backend.vault_recall",
                "copy_in_boundary": "NumPy contiguous float32 matrix/query copied into MLX arrays",
                "copy_out_boundary": "MLX score vector copied to NumPy for canonical stable top-k ordering",
                "timing": timing.as_dict(),
                "rows_per_sec": round(rows_per_sec, 3),
                "parity": parity,
                "top_result_preview": candidate[:3],
                "canonical_preview": canonical[:3],
            }
        )

    return {
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_version": BENCHMARK_VERSION,
        "track": "mlx_exact_cga_recall",
        "skipped": False,
        "mlx_status": status,
        "benchmark_only": True,
        "serving_authorized": False,
        "semantic_backend": "python/rust canonical exact recall",
        "score_computation": "MLX exact diagonal CGA score vector; no ANN or approximate search",
        "top_k_ordering": "canonical NumPy stable ordering after score copy-out",
        "copy_boundary": {
            "input": "NumPy -> MLX array copy at benchmark boundary",
            "output": "MLX score vector -> NumPy copy for stable top-k",
            "zero_copy_input": "no",
        },
        "non_claims": [
            "No MLX semantic-backend claim.",
            "No serving integration.",
            "No ANN or approximate recall.",
            "No CoreML or Neural Engine claim.",
        ],
        "cases": cases,
    }


def _cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=BENCHMARK_NAME)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--measured", type=int, default=DEFAULT_MEASURED)
    args = parser.parse_args(argv)
    report = run_mlx_exact_recall_experiment(warmup=args.warmup, measured=args.measured)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{BENCHMARK_NAME} — use --json")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
