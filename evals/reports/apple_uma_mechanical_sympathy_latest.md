# CORE Apple Silicon UMA Mechanical Sympathy Benchmark

Version: 1.0.0

## 1. What this measures

Deterministic Cl(4,1) geometric workloads on Apple Silicon / UMA hardware:
exact CGA recall, scalar algebra hot paths, closed-world FrameVerdict proof
latency, deterministic array persistence replay, and honest Python/Rust
memory boundaries.  No token generation.  No approximate recall.

## 2. Machine/backend summary

- Platform: macOS-26.5.1-arm64-arm-64bit
- Processor: arm
- Python: 3.12.13
- CORE_BACKEND: `(default python)`
- core_rs import: False
- using_rust(): False

## 3. Exact CGA recall

- N=128: p50=0.070 ms, rows/sec=1776009.18, zero-copy eligible=False
- N=1024: p50=0.113 ms, rows/sec=8883489.435, zero-copy eligible=False
- N=8192: p50=0.545 ms, rows/sec=14772738.586, zero-copy eligible=False
- N=65536: p50=3.809 ms, rows/sec=17156750.778, zero-copy eligible=False

## 4. Cl(4,1) scalar algebra

- geometric_product: p50=1.366 ms, ops/sec=725.319
- versor_apply: p50=2.881 ms, ops/sec=240.936
- cga_inner: p50=2.716 ms, ops/sec=301.83
- versor_condition: p50=0.531 ms, ops/sec=1871.699

## 5. FrameVerdict TTFV

- Verdict: entailed_true, p50=0.153 ms, producer=proof_chain.entail

## 6. Deterministic replay/persistence

- encode p50=0.015 ms, decode p50=0.039 ms, bytes=10924

## 7. Copy / zero-copy truth table

| Path | Input | Output | Zero-copy input |
|---|---|---|---|
| algebra.backend.geometric_product (Rust) | copy via extract_f32_slice | new NumPy allocation | no |
| algebra.backend.versor_condition (Rust) | copy via extract_f32_slice | scalar | no |
| algebra.backend.cga_inner (Rust) | copy via extract_f32_slice | scalar | no |
| algebra.backend.versor_apply (Rust f64 closure) | ascontiguousarray copy | new NumPy allocation | no |
| algebra.backend.diffusion_step | n/a | skipped — Rust unavailable | n/a |
| algebra.backend.vault_recall (Python) | NumPy view / vectorised scan | index list | n/a (Python canonical) |
| core.array_codec encode/decode | byte copy + base64 | writable ndarray copy | no |
| generate.frame_verdict.evaluate_frame_verdict | closed frame struct | FrameVerdict | n/a (proof surface) |

## 8. Why this matters for Apple Silicon

CORE's deterministic workloads are contiguous-memory geometric operations
and exact recall scans — structurally aligned with unified memory when
native bindings avoid Python marshalling tax on hot paths.

## 9. What larger Apple Silicon hardware would unlock

Larger unified memory enables higher-N exact recall validation, larger
diffusion graphs, and expanded replay persistence lanes without swapping
or fragmenting evidence buffers.

## 10. Explicit non-claims

- No CoreML acceleration claim.
- No Neural Engine acceleration claim.
- No MLX semantic-backend claim.
- No "zero-copy everywhere" claim.
- No fixed sponsorship speedup multiplier.
- No token-generation benchmark.
- No ANN/approximate-search benchmark.
