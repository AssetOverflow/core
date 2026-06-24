# Gemini Local Validation Handoff — MLX Exact Recall

Branch: `feat/apple-mlx-exact-cga-recall-experiment`

This branch is deliberately narrow. It adds the MLX exact CGA recall experiment as an isolated benchmark module before wiring it into the main Apple UMA report.

## Commands

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin --prune
git switch feat/apple-mlx-exact-cga-recall-experiment
git pull --ff-only origin feat/apple-mlx-exact-cga-recall-experiment

uv run python -m pytest -q tests/test_apple_uma_mlx_exact_recall.py
uv run python -m benchmarks.apple_uma_mlx_exact_recall --json
```

If MLX is available or installable locally:

```bash
CORE_BACKEND=rust uv run python -m benchmarks.apple_uma_mlx_exact_recall --json
```

## Touch-up limits

Only patch:

- MLX import/API mismatches
- formatting or lint issues
- test failure fixes directly tied to this module

Do not add serving integration.
Do not add Metal.
Do not add CoreML/ANE.
Do not change semantic source of truth.
Do not use ANN or approximate recall.

## Success criteria

- Skip path passes when MLX is unavailable.
- MLX-present path emits cases.
- Every emitted case has `parity.parity_pass: true`.
- Copy-in/copy-out fields remain explicit.
- Non-claims remain visible.
