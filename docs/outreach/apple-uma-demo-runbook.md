# Apple UMA demo runbook

This runbook turns the Apple UMA benchmark, Workbench report card, and claim-safe package builder into a repeatable recording/share workflow.

## Goal

Produce a shareable package for Apple Silicon engineering review that shows:

- exact CGA recall benchmark evidence;
- Rust/native boundary status;
- MLX exact score-vector parity;
- explicit copy-in/copy-out boundaries;
- Workbench read-only report-card surface;
- explicit non-claims.

The demo must not imply:

- serving-path MLX integration;
- CoreML acceleration;
- ANE acceleration;
- Metal custom kernels;
- approximate recall or ANN search;
- zero-copy everywhere;
- generalized token-generation performance.

## Local preparation

Run from repo root on the Apple Silicon machine used for recording.

```bash
cd /Users/kaizenpro/Projects/core
git switch main
git fetch origin --prune
git pull --ff-only origin main
```

Build the Rust extension if needed:

```bash
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 uv run python -m maturin develop --release --manifest-path core-rs/Cargo.toml
```

Confirm MLX is available:

```bash
uv run python - <<'PY'
import mlx.core as mx
print(mx.default_device())
PY
```

## Generate and package the report

Preferred one-shot command:

```bash
uv run python scripts/package_apple_uma_demo.py --refresh-report
```

This command:

1. refreshes `evals/reports/apple_uma_mechanical_sympathy_latest.{json,md}` with `CORE_BACKEND=rust`;
2. reads the Workbench Apple UMA projection;
3. refuses to package stale/no-MLX or parity-failing evidence by default;
4. creates a package under `dist/apple-uma-demo/<timestamp>/`.

If you intentionally need to inspect stale state, use:

```bash
uv run python scripts/package_apple_uma_demo.py --allow-stale
```

Do not use `--allow-stale` for the Apple-facing package.

## Validate before recording

Run focused backend and UI checks:

```bash
uv run python -m pytest -q tests/test_apple_uma_demo_package.py tests/test_workbench_apple_uma_report.py tests/test_workbench_api.py
cd workbench-ui
pnpm vitest run src/app/apple-uma/AppleUmaReportRoute.test.tsx src/app/routeConformance.test.tsx
pnpm exec tsc -b
```

## Workbench recording flow

Start the API server using the repository's normal Workbench launcher.

Open the Workbench UI and navigate to:

```text
/apple-uma
```

Record these beats:

1. **Header / identity** — show benchmark name, version, source digest, read-only status.
2. **Backend status** — show Rust/native status and current backend truthfully.
3. **Track inventory** — show all required tracks present.
4. **MLX exact CGA recall** — show track present, executed, parity true, case count, timing rows.
5. **Copy boundaries** — show NumPy to MLX copy-in and MLX to NumPy copy-out.
6. **Non-claims** — show that the surface explicitly does not claim CoreML, ANE, ANN, serving integration, or zero-copy everywhere.

Do not narrate beyond what the report proves.

## Package contents

The package directory contains:

- `apple_uma_mechanical_sympathy_latest.json`
- `apple_uma_mechanical_sympathy_latest.md`
- `package_manifest.json`
- `README.md`
- `APPLE_SHARING_NOTE.md`

Before sharing, inspect `package_manifest.json` and confirm:

```text
allow_stale: false
mlx_summary.present: true
mlx_summary.skipped: false
mlx_summary.all_cases_parity_pass: true
mlx_summary.serving_authorized: false
```

## Suggested Apple-facing phrasing

Use restrained language:

> This is a deterministic CORE benchmark package for Apple Silicon UMA review. It isolates exact CGA recall, MLX score-vector parity, Rust/native boundary behavior, and copy-boundary truth tables. It is benchmark-only evidence: no CoreML, ANE, Metal, ANN, or serving-path acceleration claim is made.

## Stop conditions

Do not record/share the package if any of these are true:

- MLX import fails;
- MLX exact CGA recall is absent or skipped;
- MLX parity is false;
- Workbench shows a stale-report warning;
- the package was generated with `--allow-stale`;
- the report claims serving authorization;
- copy boundaries are missing or vague.
