# Apple UMA MLX Exact CGA Recall Experiment

ADR-0235 Lane 3 introduces an optional, benchmark-only MLX exact-recall experiment for CORE's Cl(4,1) CGA recall workload.

This is **not** a serving backend. It does not replace Python or Rust as the semantic source of truth. It does not use ANN, HNSW, approximate recall, sampling, CoreML, or Neural Engine acceleration.

## What it measures

`benchmarks/apple_uma_mlx_exact_recall.py` measures one narrow workload:

```text
Deterministic (N, 32) float32 fixture matrix
+ deterministic length-32 query
→ MLX exact diagonal CGA score vector
→ score vector copied back to NumPy
→ canonical stable top-k ordering
→ parity check against algebra.backend.vault_recall
```

The MLX path computes exact scores only. The final top-k ordering is intentionally kept in NumPy/Python so the experiment does not depend on MLX sorting/top-k API behavior and can reuse CORE's canonical descending-score / ascending-index tie break.

## Run

```bash
uv run python -m benchmarks.apple_uma_mlx_exact_recall --json
```

With MLX unavailable, the report must skip cleanly with an explicit reason.

With MLX available, the report emits cases for the standard Apple UMA recall sizes and includes:

- MLX import status and default device when observable
- `N`, `top_k`, dtype, and contiguity
- p50/p95/mean timing and rows/sec
- copy-in boundary: NumPy fixture to MLX array
- copy-out boundary: MLX score vector to NumPy
- parity against `algebra.backend.vault_recall`
- top result preview and canonical preview

## Non-claims

This experiment does **not** claim:

- MLX is a semantic backend
- MLX is serving-authorized
- CoreML or Neural Engine acceleration
- zero-copy everywhere
- ANN or approximate recall
- token-generation throughput
- Apple endorsement, sponsorship, or product integration

## Validation

```bash
uv run python -m pytest -q tests/test_apple_uma_mlx_exact_recall.py
uv run python -m benchmarks.apple_uma_mlx_exact_recall --json
```

When MLX is installed on Apple Silicon, also run:

```bash
CORE_BACKEND=rust uv run python -m benchmarks.apple_uma_mlx_exact_recall --json
```

The `parity.parity_pass` field must be true for every emitted case before using results in any Apple-facing material.
