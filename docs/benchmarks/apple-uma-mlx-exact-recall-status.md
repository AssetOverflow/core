# Apple UMA MLX Exact Recall Status

This branch intentionally lands the MLX exact CGA recall lane as an isolated benchmark module first.

## Implemented

- `benchmarks/apple_uma_mlx_exact_recall.py`
- `tests/test_apple_uma_mlx_exact_recall.py`
- `docs/benchmarks/apple-uma-mlx-exact-recall.md`

## Not yet integrated

The main `benchmarks/apple_uma_mechanical_sympathy.py` report has not yet been modified on this branch.

Reason: the isolated module is the safest first landing surface for local Apple Silicon validation. After MLX is verified locally, the module can be integrated into the main Apple UMA report as the `mlx_exact_cga_recall` track.

## Local validation request

Run:

```bash
uv run python -m pytest -q tests/test_apple_uma_mlx_exact_recall.py
uv run python -m benchmarks.apple_uma_mlx_exact_recall --json
```

When MLX is installed:

```bash
CORE_BACKEND=rust uv run python -m benchmarks.apple_uma_mlx_exact_recall --json
```

All emitted cases must show `parity.parity_pass: true` before the results are used in Apple-facing material.
