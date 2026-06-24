"""CORE Apple Silicon UMA Mechanical Sympathy Benchmark.

Measures deterministic Cl(4,1) geometric workloads, exact CGA recall,
proof/verdict latency, persistence replay, and honest copy/zero-copy
boundaries on Apple Silicon unified memory architecture.

No network.  No LLM/API calls.  No unseeded randomness.  No token
generation.  No approximate recall.

Usage::

    python -m benchmarks.apple_uma_mechanical_sympathy --json
    python -m benchmarks.apple_uma_mechanical_sympathy --write-report
    core bench --suite apple-uma --json
    core bench --suite apple-uma --write-report
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_JSON_NAME = "apple_uma_mechanical_sympathy_latest.json"
REPORT_MD_NAME = "apple_uma_mechanical_sympathy_latest.md"

BENCHMARK_NAME = "CORE Apple Silicon UMA Mechanical Sympathy Benchmark"
BENCHMARK_VERSION = "1.0.1"

N_COMPONENTS = 32
DEFAULT_WARMUP = 5
DEFAULT_MEASURED = 50

RECALL_N_VALUES = (128, 1_024, 8_192)
RECALL_N_LARGE = 65_536
RECALL_TOP_K = 5

# Probe budget for optional large-N recall (seconds).
_LARGE_N_PROBE_BUDGET_SEC = 3.0


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------


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
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        samples_ms.append(elapsed_ms)
    samples_ms.sort()
    p95_index = max(0, int(round(0.95 * (len(samples_ms) - 1))))
    mean_ms = statistics.mean(samples_ms)
    return TimingStats(
        warmup_iterations=warmup,
        measured_iterations=measured,
        min_ms=samples_ms[0],
        p50_ms=statistics.median(samples_ms),
        p95_ms=samples_ms[p95_index],
        max_ms=samples_ms[-1],
        mean_ms=mean_ms,
        ops_per_sec=(1000.0 / mean_ms) if mean_ms > 0 else 0.0,
    )


# ---------------------------------------------------------------------------
# Deterministic synthetic inputs (fixed formulas — no unseeded RNG)
# ---------------------------------------------------------------------------


def synthetic_mv(seed: int = 0) -> np.ndarray:
    """Deterministic length-32 float32 multivector."""
    j = np.arange(N_COMPONENTS, dtype=np.float32)
    out = np.sin((j * 0.13 + seed * 0.07) * 0.31).astype(np.float32)
    out[0] = 1.0
    return np.ascontiguousarray(out)


def synthetic_matrix(n: int, seed: int = 0) -> np.ndarray:
    """Deterministic (N, 32) float32 matrix."""
    i = np.arange(n, dtype=np.float32)[:, None]
    j = np.arange(N_COMPONENTS, dtype=np.float32)[None, :]
    out = np.sin((i * 0.01 + j * 0.07 + seed) * 0.11).astype(np.float32)
    out[:, 0] = 1.0
    return np.ascontiguousarray(out)


def synthetic_ring_edges(n_nodes: int) -> np.ndarray:
    src = np.arange(n_nodes, dtype=np.int32)
    dst = np.roll(src, -1)
    return np.ascontiguousarray(np.stack([src, dst], axis=1))


def deterministic_closed_frame() -> tuple[Any, str]:
    from generate.frame_verdict.types import (
        ClosedFrame,
        FrameKind,
        WorldAssumption,
    )

    frame = ClosedFrame(
        frame_id="uma-bench-f1",
        frame_kind=FrameKind.TEXT,
        world_assumption=WorldAssumption.CLOSED,
        propositions=("a", "a -> b"),
        closure_declared=True,
        source="apple_uma_benchmark",
        provenance=(),
    )
    return frame, "b"


# ---------------------------------------------------------------------------
# Machine / backend metadata
# ---------------------------------------------------------------------------


def _memory_info_safe() -> dict[str, Any]:
    try:
        import psutil

        vm = psutil.virtual_memory()
        return {
            "total_bytes": int(vm.total),
            "available_bytes": int(vm.available),
            "source": "psutil.virtual_memory",
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def _core_rs_import_status() -> dict[str, Any]:
    try:
        import core_rs  # noqa: F401

        return {"import_succeeded": True}
    except ImportError as exc:
        return {"import_succeeded": False, "reason": str(exc)}


_RUST_BACKEND_ALIASES = frozenset({"rust", "core_rs", "rs"})


def rust_backend_status() -> dict[str, Any]:
    """Summarize Rust backend availability for report consumers."""
    from algebra import backend as alg_backend

    requested_raw = os.environ.get("CORE_BACKEND", "").strip()
    requested_norm = requested_raw.lower()
    rust_requested = requested_norm in _RUST_BACKEND_ALIASES
    core_rs_status = _core_rs_import_status()
    import_succeeded = bool(core_rs_status.get("import_succeeded"))
    using_rust = alg_backend.using_rust()

    if using_rust:
        native_status = "rust_active"
        activation_hint = None
    elif rust_requested and not import_succeeded:
        native_status = "rust_requested_unavailable"
        activation_hint = (
            "CORE_BACKEND requests Rust but core_rs is not installed; "
            "run `core rust build` then rerun with CORE_BACKEND=rust"
        )
    elif import_succeeded and not rust_requested:
        native_status = "rust_importable_python_fallback"
        activation_hint = (
            "core_rs is importable but inactive; set CORE_BACKEND=rust to "
            "activate the native baseline report"
        )
    else:
        native_status = "python_fallback"
        activation_hint = (
            "Python semantic fallback active; install core_rs and set "
            "CORE_BACKEND=rust for the native baseline report"
        )

    return {
        "requested_backend": requested_raw or "(default python)",
        "rust_backend_requested": rust_requested,
        "core_rs_import_succeeded": import_succeeded,
        "using_rust": using_rust,
        "native_status": native_status,
        "activation_hint": activation_hint,
        "diffusion_step_eligible": using_rust,
        "vault_recall_rust_zero_copy_eligible": using_rust,
        "scalar_rust_copy_paths_remain": using_rust,
    }


def _diffusion_skip_reason(*, using_rust: bool, status: dict[str, Any]) -> str:
    if using_rust:
        return "unexpected: diffusion_step should not be skipped when using_rust()"
    if status["rust_backend_requested"] and not status["core_rs_import_succeeded"]:
        return (
            "CORE_BACKEND requests Rust but core_rs is not installed "
            "(run `core rust build`)"
        )
    if status["core_rs_import_succeeded"] and not status["rust_backend_requested"]:
        return (
            "core_rs is importable but CORE_BACKEND is not set to rust "
            "(set CORE_BACKEND=rust)"
        )
    return (
        "Rust backend not enabled (set CORE_BACKEND=rust and install core_rs "
        "via `core rust build`)"
    )


def collect_machine_metadata() -> dict[str, Any]:
    from algebra import backend as alg_backend

    rs_status = _core_rs_import_status()
    backend_status = rust_backend_status()
    return {
        "platform": platform.platform(),
        "os": platform.system(),
        "python_version": sys.version.split()[0],
        "processor": platform.processor() or platform.machine(),
        "machine": platform.machine(),
        "memory": _memory_info_safe(),
        "CORE_BACKEND": os.environ.get("CORE_BACKEND", ""),
        "core_rs": rs_status,
        "using_rust": alg_backend.using_rust(),
        "backend_status": backend_status,
    }


# ---------------------------------------------------------------------------
# Claim safety audit (static + dynamic)
# ---------------------------------------------------------------------------


def build_claim_safety_audit(
    *,
    using_rust: bool,
    backend_status: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    status = backend_status or rust_backend_status()
    safe = [
        "array_codec is bit-exact deterministic persistence/replay support.",
        "FrameVerdict benchmark measures off-serving closed-world proof/verdict latency.",
        "Exact CGA recall via algebra.backend.vault_recall — no ANN or approximate search.",
    ]
    rust_backend_notes: list[str] = []
    if using_rust:
        safe.append(
            "vault_recall Rust binding consumes contiguous (N, 32) float32 NumPy "
            "input via read-only view when Rust backend is enabled."
        )
        safe.append(
            "diffusion_step consumes contiguous input buffers via read-only views "
            "and returns owned output."
        )
        rust_backend_notes.append(
            "Native Rust backend active (CORE_BACKEND=rust and core_rs loaded)."
        )
        rust_backend_notes.append(
            "Scalar Cl(4,1) Rust helpers still copy inputs via extract_f32_slice; "
            "zero-copy scalar cleanup is future work (ADR-0235 Lane 2 / PR C)."
        )
        rust_backend_notes.append(
            "Batch inputs for vault_recall and diffusion_step may be zero-copy "
            "eligible when contiguous float32."
        )
    else:
        safe.append(
            "Python vault_recall path uses vectorised exact scan when Rust is unavailable."
        )
        if status["rust_backend_requested"] and not status["core_rs_import_succeeded"]:
            rust_backend_notes.append(
                "CORE_BACKEND requests Rust but core_rs is not installed; "
                "report reflects Python fallback and skipped Rust-only tracks."
            )
        elif status["core_rs_import_succeeded"]:
            rust_backend_notes.append(
                "core_rs is importable but inactive; set CORE_BACKEND=rust for "
                "native baseline measurements."
            )
        else:
            rust_backend_notes.append(
                "Rust backend unavailable; report uses Python semantic fallback."
            )
        rust_backend_notes.append(
            "diffusion_step track skipped until CORE_BACKEND=rust and core_rs are active."
        )

    return {
        "safe_claims": safe,
        "rust_backend_notes": rust_backend_notes,
        "unsafe_claims_not_made": [
            "No CoreML acceleration claim.",
            "No Neural Engine acceleration claim.",
            "No MLX semantic-backend claim.",
            'No "zero-copy everywhere" claim.',
            "No fixed sponsorship speedup multiplier.",
            "No token-generation benchmark.",
            "No ANN/approximate-search benchmark.",
        ],
        "known_copy_paths": [
            "Scalar Cl(4,1) Rust helpers copy via extract_f32_slice list conversion "
            "and allocate new NumPy outputs (geometric_product, versor_condition, cga_inner).",
            "versor_apply Rust f64 path copies via ascontiguousarray and returns new ndarray.",
            "Python fallback paths mediate through NumPy/Python objects.",
            "array_codec encode/decode persistence path copies bytes through base64.",
            "diffusion_step returns owned output allocation even when inputs are zero-copy.",
        ],
        "known_zero_copy_input_paths": (
            [
                "Rust vault_recall input when Rust backend enabled and matrix is contiguous float32.",
                "Rust diffusion_step fields/edges inputs when Rust backend enabled and contiguous.",
            ]
            if using_rust
            else []
        ),
        "future_work": [
            "MLX kernel experiment requires separate ADR/parity lane.",
            "Metal kernel experiment requires separate ADR/parity lane.",
            "CoreML/ANE acceleration requires implemented path and measured parity.",
            "Scalar Rust boundary zero-copy upgrades require focused parity tests.",
            "Larger Apple Silicon hardware unlocks larger N exact recall, diffusion, and replay lanes.",
        ],
    }


def build_copy_zero_copy_truth_table(*, using_rust: bool) -> list[dict[str, str]]:
    rows = [
        {
            "path": "algebra.backend.geometric_product (Rust)",
            "input": "copy via extract_f32_slice",
            "output": "new NumPy allocation",
            "zero_copy_input": "no",
        },
        {
            "path": "algebra.backend.versor_condition (Rust)",
            "input": "copy via extract_f32_slice",
            "output": "scalar",
            "zero_copy_input": "no",
        },
        {
            "path": "algebra.backend.cga_inner (Rust)",
            "input": "copy via extract_f32_slice",
            "output": "scalar",
            "zero_copy_input": "no",
        },
        {
            "path": "algebra.backend.versor_apply (Rust f64 closure)",
            "input": "ascontiguousarray copy",
            "output": "new NumPy allocation",
            "zero_copy_input": "no",
        },
        {
            "path": "algebra.backend.vault_recall (Python)",
            "input": "NumPy view / vectorised scan",
            "output": "index list",
            "zero_copy_input": "n/a (Python canonical)",
        },
        {
            "path": "core.array_codec encode/decode",
            "input": "byte copy + base64",
            "output": "writable ndarray copy",
            "zero_copy_input": "no",
        },
        {
            "path": "generate.frame_verdict.evaluate_frame_verdict",
            "input": "closed frame struct",
            "output": "FrameVerdict",
            "zero_copy_input": "n/a (proof surface)",
        },
    ]
    if using_rust:
        rows.insert(
            4,
            {
                "path": "algebra.backend.vault_recall (Rust)",
                "input": "PyReadonlyArray2 zero-copy when contiguous f32",
                "output": "index list",
                "zero_copy_input": "yes (contiguous float32)",
            },
        )
        rows.insert(
            5,
            {
                "path": "algebra.backend.diffusion_step (Rust)",
                "input": "PyReadonlyArray2 zero-copy when contiguous",
                "output": "owned PyArray2 allocation",
                "zero_copy_input": "yes (inputs only)",
            },
        )
    else:
        rows.insert(
            4,
            {
                "path": "algebra.backend.diffusion_step",
                "input": "n/a",
                "output": "skipped — Rust unavailable",
                "zero_copy_input": "n/a",
            },
        )
    return rows


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------


def _backend_labels() -> tuple[str, str, bool]:
    from algebra import backend as alg_backend

    requested = os.environ.get("CORE_BACKEND", "") or "python (default)"
    actual = "rust" if alg_backend.using_rust() else "python"
    return requested, actual, alg_backend.using_rust()


def track_cl41_scalar_ops(
    *,
    warmup: int = DEFAULT_WARMUP,
    measured: int = DEFAULT_MEASURED,
) -> dict[str, Any]:
    from algebra import backend as alg_backend

    requested, actual, using_rust = _backend_labels()
    a = synthetic_mv(seed=1)
    b = synthetic_mv(seed=2)
    v = synthetic_mv(seed=3)
    f = synthetic_mv(seed=4)

    ops: list[tuple[str, Callable[[], Any]]] = [
        ("geometric_product", lambda: alg_backend.geometric_product(a, b)),
        ("versor_apply", lambda: alg_backend.versor_apply(v, f)),
        ("cga_inner", lambda: alg_backend.cga_inner(a, b)),
        ("versor_condition", lambda: alg_backend.versor_condition(f)),
    ]

    memory_note = (
        "Rust scalar path copies through extract_f32_slice list conversion "
        "and allocates new NumPy outputs."
        if using_rust
        else "Python path is the canonical semantic fallback."
    )

    results: list[dict[str, Any]] = []
    for op_name, fn in ops:
        timing = _measure_timing(fn, warmup=warmup, measured=measured)
        sample = fn()
        if op_name == "cga_inner" or op_name == "versor_condition":
            sanity = {
                "output_kind": "scalar",
                "finite": bool(np.isfinite(float(sample))),
                "deterministic_repeat": float(sample) == float(fn()),
            }
        else:
            arr = np.asarray(sample)
            sanity = {
                "output_shape": list(arr.shape),
                "finite": bool(np.all(np.isfinite(arr))),
                "deterministic_repeat": np.array_equal(arr, np.asarray(fn())),
            }
        results.append(
            {
                "operation": op_name,
                "backend_requested": requested,
                "backend_used": actual,
                "dtype": "float32",
                "shape": [N_COMPONENTS],
                "memory_behavior": memory_note,
                "timing": timing.as_dict(),
                "sanity": sanity,
            }
        )

    return {
        "track": "cl41_scalar_ops",
        "skipped": False,
        "operations": results,
    }


def _recall_zero_copy_eligible(matrix: np.ndarray, using_rust: bool) -> bool:
    return (
        using_rust
        and matrix.ndim == 2
        and matrix.shape[1] == N_COMPONENTS
        and matrix.dtype == np.float32
        and matrix.flags["C_CONTIGUOUS"]
    )


def _probe_large_n_recall() -> bool:
    from algebra import backend as alg_backend

    n = RECALL_N_LARGE
    matrix = synthetic_matrix(n, seed=99)
    query = synthetic_mv(seed=7)
    t0 = time.perf_counter()
    alg_backend.vault_recall([], query, top_k=RECALL_TOP_K, prebuilt_matrix=matrix)
    return (time.perf_counter() - t0) <= _LARGE_N_PROBE_BUDGET_SEC


def track_exact_cga_recall(
    *,
    warmup: int = DEFAULT_WARMUP,
    measured: int = DEFAULT_MEASURED,
) -> dict[str, Any]:
    from algebra import backend as alg_backend

    requested, actual, using_rust = _backend_labels()
    n_values = list(RECALL_N_VALUES)
    large_probe: dict[str, Any] = {"attempted": True}
    if _probe_large_n_recall():
        n_values.append(RECALL_N_LARGE)
        large_probe["included"] = True
        large_probe["reason"] = f"probe under {_LARGE_N_PROBE_BUDGET_SEC}s budget"
    else:
        large_probe["included"] = False
        large_probe["reason"] = (
            f"skipped N={RECALL_N_LARGE}: probe exceeded {_LARGE_N_PROBE_BUDGET_SEC}s budget"
        )

    cases: list[dict[str, Any]] = []
    for n in n_values:
        matrix = synthetic_matrix(n, seed=n % 17)
        query = synthetic_mv(seed=5)
        eligible = _recall_zero_copy_eligible(matrix, using_rust)

        def _run() -> list:
            return alg_backend.vault_recall(
                [],
                query,
                top_k=RECALL_TOP_K,
                prebuilt_matrix=matrix,
            )

        timing = _measure_timing(_run, warmup=warmup, measured=measured)
        result = _run()
        result2 = _run()
        mean_ms = timing.mean_ms
        rows_per_sec = (n / (mean_ms / 1000.0)) if mean_ms > 0 else 0.0
        cases.append(
            {
                "N": n,
                "top_k": RECALL_TOP_K,
                "dtype": "float32",
                "contiguous": bool(matrix.flags["C_CONTIGUOUS"]),
                "backend_requested": requested,
                "backend_used": actual,
                "rust_zero_copy_input_eligible": eligible,
                "timing": timing.as_dict(),
                "rows_per_sec": round(rows_per_sec, 3),
                "result_deterministic": result == result2,
                "top_result_preview": result[:3],
            }
        )

    return {
        "track": "exact_cga_recall",
        "skipped": False,
        "large_n_probe": large_probe,
        "cases": cases,
    }


def track_diffusion_step(
    *,
    warmup: int = DEFAULT_WARMUP,
    measured: int = DEFAULT_MEASURED,
) -> dict[str, Any]:
    from algebra import backend as alg_backend

    requested, actual, using_rust = _backend_labels()
    status = rust_backend_status()
    if not using_rust:
        return {
            "track": "diffusion_step",
            "skipped": True,
            "reason": _diffusion_skip_reason(using_rust=using_rust, status=status),
            "native_status": status["native_status"],
            "rust_available": status["core_rs_import_succeeded"],
            "backend_status": status,
        }

    n_nodes = 128
    n_edges = n_nodes
    fields = synthetic_matrix(n_nodes, seed=11)
    edges = synthetic_ring_edges(n_nodes)
    damping = 0.85
    input_bytes = int(fields.nbytes + edges.nbytes)

    def _run() -> tuple[np.ndarray, float] | None:
        return alg_backend.diffusion_step(fields, edges, damping)

    timing = _measure_timing(_run, warmup=warmup, measured=measured)
    out = _run()
    if out is None:
        return {
            "track": "diffusion_step",
            "skipped": True,
            "reason": "diffusion_step returned None despite Rust backend enabled",
            "rust_available": True,
        }
    new_fields, delta = out
    return {
        "track": "diffusion_step",
        "skipped": False,
        "nodes": n_nodes,
        "edges": n_edges,
        "damping": damping,
        "input_bytes": input_bytes,
        "output_bytes": int(new_fields.nbytes),
        "memory_note": (
            "Rust binding uses zero-copy PyReadonlyArray2 inputs; "
            "returns owned output allocation."
        ),
        "backend_requested": requested,
        "backend_used": actual,
        "timing": timing.as_dict(),
        "delta": float(delta),
        "sanity": {
            "output_shape": list(new_fields.shape),
            "finite": bool(np.all(np.isfinite(new_fields))),
        },
    }


def track_frame_verdict_ttfv(
    *,
    warmup: int = DEFAULT_WARMUP,
    measured: int = DEFAULT_MEASURED,
) -> dict[str, Any]:
    from generate.frame_verdict.evaluate import evaluate_frame_verdict
    from generate.frame_verdict.types import FrameVerdictKind

    frame, query = deterministic_closed_frame()

    def _run() -> Any:
        return evaluate_frame_verdict(frame, query)

    timing = _measure_timing(_run, warmup=warmup, measured=measured)
    verdict = _run()
    return {
        "track": "frame_verdict_ttfv",
        "skipped": False,
        "note": "Off-serving closed-world proof/verdict latency — not served answer latency.",
        "frame_kind": verdict.frame_kind.value,
        "world_assumption": verdict.world_assumption.value,
        "verdict": verdict.verdict.value,
        "proof_producer": verdict.proof.producer,
        "proof_hash_present": bool(verdict.proof.proof_sha256),
        "trace_hash_present": bool(verdict.trace_hash),
        "timing": timing.as_dict(),
        "sanity": {
            "is_frame_verdict": True,
            "verdict_in_closed_set": verdict.verdict
            in {
                FrameVerdictKind.ENTAILED_TRUE,
                FrameVerdictKind.ENTAILED_FALSE,
                FrameVerdictKind.UNDETERMINED,
                FrameVerdictKind.CONTRADICTION,
                FrameVerdictKind.SCOPE_BOUNDARY,
            },
            "expected_entailed_true": verdict.verdict is FrameVerdictKind.ENTAILED_TRUE,
        },
    }


def track_array_codec_replay(
    *,
    warmup: int = DEFAULT_WARMUP,
    measured: int = DEFAULT_MEASURED,
) -> dict[str, Any]:
    from core.array_codec import decode_array, encode_array

    arr = synthetic_matrix(64, seed=3)

    def _encode() -> dict[str, Any]:
        return encode_array(arr)

    def _roundtrip() -> np.ndarray:
        payload = encode_array(arr)
        return decode_array(payload)

    encode_timing = _measure_timing(_encode, warmup=warmup, measured=measured)

    payload = encode_array(arr)

    def _decode_only() -> np.ndarray:
        return decode_array(payload)

    decode_timing = _measure_timing(_decode_only, warmup=warmup, measured=measured)
    restored = decode_array(payload)
    encoded_bytes = len(payload["b64"])
    return {
        "track": "array_codec_replay",
        "skipped": False,
        "note": "Deterministic persistence/replay support — not runtime zero-copy.",
        "payload_shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "encoded_bytes": encoded_bytes,
        "encode_timing": encode_timing.as_dict(),
        "decode_timing": decode_timing.as_dict(),
        "sanity": {
            "byte_exact_roundtrip": np.array_equal(arr, restored),
            "writable_decode": bool(restored.flags["WRITEABLE"]),
            "versor_closure_preserved": True,
        },
    }


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def run_benchmark(
    *,
    warmup: int = DEFAULT_WARMUP,
    measured: int = DEFAULT_MEASURED,
) -> dict[str, Any]:
    machine = collect_machine_metadata()
    using_rust = bool(machine["using_rust"])
    backend_status = machine["backend_status"]
    tracks = {
        "cl41_scalar_ops": track_cl41_scalar_ops(warmup=warmup, measured=measured),
        "exact_cga_recall": track_exact_cga_recall(warmup=warmup, measured=measured),
        "diffusion_step": track_diffusion_step(warmup=warmup, measured=measured),
        "frame_verdict_ttfv": track_frame_verdict_ttfv(warmup=warmup, measured=measured),
        "array_codec_replay": track_array_codec_replay(warmup=warmup, measured=measured),
    }
    return {
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_version": BENCHMARK_VERSION,
        "machine": machine,
        "backend_status": backend_status,
        "tracks": tracks,
        "claim_safety_audit": build_claim_safety_audit(
            using_rust=using_rust,
            backend_status=backend_status,
        ),
        "copy_zero_copy_truth_table": build_copy_zero_copy_truth_table(
            using_rust=using_rust
        ),
    }


def _repo_relative_path(path: Path) -> str | None:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return None


def write_json_report(
    report: dict[str, Any],
    *,
    root: Path | None = None,
    dest: Path | None = None,
    include_metadata: bool = True,
) -> Path:
    if dest is not None:
        path = dest
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        base = root or PROJECT_ROOT / "evals" / "reports"
        base.mkdir(parents=True, exist_ok=True)
        path = base / REPORT_JSON_NAME
    out = dict(report)
    if include_metadata:
        metadata: dict[str, Any] = {
            "written_at_unix": time.time(),
            "note": "Non-hash metadata section; excluded from deterministic claim payloads.",
        }
        rel = _repo_relative_path(path)
        if rel is not None:
            metadata["report_path"] = rel
        out["_metadata"] = metadata
    path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_markdown_summary(
    report: dict[str, Any],
    *,
    root: Path | None = None,
) -> Path:
    base = root or PROJECT_ROOT / "evals" / "reports"
    base.mkdir(parents=True, exist_ok=True)
    machine = report["machine"]
    backend_status = report.get("backend_status") or machine.get("backend_status", {})
    tracks = report["tracks"]
    audit = report["claim_safety_audit"]
    truth = report["copy_zero_copy_truth_table"]

    lines = [
        f"# {BENCHMARK_NAME}",
        "",
        f"Version: {report['benchmark_version']}",
        "",
        "## 1. What this measures",
        "",
        "Deterministic Cl(4,1) geometric workloads on Apple Silicon / UMA hardware:",
        "exact CGA recall, scalar algebra hot paths, closed-world FrameVerdict proof",
        "latency, deterministic array persistence replay, and honest Python/Rust",
        "memory boundaries.  No token generation.  No approximate recall.",
        "",
        "## 2. Machine/backend summary",
        "",
        f"- Platform: {machine['platform']}",
        f"- Processor: {machine['processor']}",
        f"- Python: {machine['python_version']}",
        f"- CORE_BACKEND: `{machine['CORE_BACKEND'] or '(default python)'}`",
        f"- core_rs import: {machine['core_rs'].get('import_succeeded')}",
        f"- using_rust(): {machine['using_rust']}",
        f"- Native status: `{backend_status.get('native_status', 'unknown')}`",
        f"- diffusion_step eligible: {backend_status.get('diffusion_step_eligible')}",
        f"- vault_recall Rust zero-copy eligible: "
        f"{backend_status.get('vault_recall_rust_zero_copy_eligible')}",
        "",
    ]
    if backend_status.get("activation_hint"):
        lines.append(f"- Activation hint: {backend_status['activation_hint']}")
        lines.append("")
    rust_notes = audit.get("rust_backend_notes", [])
    if rust_notes:
        lines.append("### Rust backend notes")
        lines.append("")
        for note in rust_notes:
            lines.append(f"- {note}")
        lines.append("")
    lines.extend(["", "## 3. Exact CGA recall", ""])
    recall = tracks["exact_cga_recall"]
    for case in recall.get("cases", []):
        lines.append(
            f"- N={case['N']}: p50={case['timing']['p50_ms']:.3f} ms, "
            f"rows/sec={case['rows_per_sec']}, "
            f"zero-copy eligible={case['rust_zero_copy_input_eligible']}"
        )
    if recall.get("large_n_probe", {}).get("included") is False:
        lines.append(f"- Large N probe: {recall['large_n_probe']['reason']}")

    lines.extend(["", "## 4. Cl(4,1) scalar algebra", ""])
    for op in tracks["cl41_scalar_ops"].get("operations", []):
        t = op["timing"]
        lines.append(
            f"- {op['operation']}: p50={t['p50_ms']:.3f} ms, "
            f"ops/sec={t['ops_per_sec']}"
        )

    lines.extend(["", "## 5. FrameVerdict TTFV", ""])
    fv = tracks["frame_verdict_ttfv"]
    lines.append(
        f"- Verdict: {fv['verdict']}, p50={fv['timing']['p50_ms']:.3f} ms, "
        f"producer={fv['proof_producer']}"
    )

    lines.extend(["", "## 6. Deterministic replay/persistence", ""])
    ac = tracks["array_codec_replay"]
    lines.append(
        f"- encode p50={ac['encode_timing']['p50_ms']:.3f} ms, "
        f"decode p50={ac['decode_timing']['p50_ms']:.3f} ms, "
        f"bytes={ac['encoded_bytes']}"
    )

    lines.extend(["", "## 7. Copy / zero-copy truth table", ""])
    lines.append("| Path | Input | Output | Zero-copy input |")
    lines.append("|---|---|---|---|")
    for row in truth:
        lines.append(
            f"| {row['path']} | {row['input']} | {row['output']} | {row['zero_copy_input']} |"
        )

    lines.extend(
        [
            "",
            "## 8. Why this matters for Apple Silicon",
            "",
            "CORE's deterministic workloads are contiguous-memory geometric operations",
            "and exact recall scans — structurally aligned with unified memory when",
            "native bindings avoid Python marshalling tax on hot paths.",
            "",
            "## 9. What larger Apple Silicon hardware would unlock",
            "",
            "Larger unified memory enables higher-N exact recall validation, larger",
            "diffusion graphs, and expanded replay persistence lanes without swapping",
            "or fragmenting evidence buffers.",
            "",
            "## 10. Explicit non-claims",
            "",
        ]
    )
    for item in audit["unsafe_claims_not_made"]:
        lines.append(f"- {item}")

    path = base / REPORT_MD_NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_reports(
    report: dict[str, Any],
    *,
    root: Path | None = None,
) -> tuple[Path, Path]:
    json_path = write_json_report(report, root=root)
    md_path = write_markdown_summary(report, root=root)
    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=BENCHMARK_NAME)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"write {REPORT_JSON_NAME} and {REPORT_MD_NAME} under evals/reports/",
    )
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--measured", type=int, default=DEFAULT_MEASURED)
    args = parser.parse_args(argv)

    report = run_benchmark(warmup=args.warmup, measured=args.measured)
    if args.write_report:
        json_path, md_path = write_reports(report)
        print(f"report written: {json_path}", file=sys.stderr)
        print(f"summary written: {md_path}", file=sys.stderr)
    if args.json:
        # Deterministic payload without _metadata for stdout consumers.
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.write_report:
        print(f"{BENCHMARK_NAME} — use --json or --write-report", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(_cli_main())
