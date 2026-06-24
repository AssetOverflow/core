# Apple UMA Rust Baseline Report

Engineering guide for generating a **Rust-enabled** Apple Silicon UMA mechanical
sympathy benchmark report.  Python remains the semantic source of truth; Rust is
the incumbent native algebra backend activated only when explicitly requested.

See also:

- `benchmarks/apple_uma_mechanical_sympathy.py` — benchmark harness
- `docs/outreach/apple-silicon-support-brief.md` — claim-safe outreach framing
- `docs/adr/ADR-0235-apple-silicon-uma-acceleration-lanes.md` — staged acceleration roadmap

## Prerequisites

- macOS arm64 (Apple Silicon) recommended; benchmark runs on any platform
- Python environment with repo dependencies (`uv sync`)
- Rust toolchain (`cargo`, `rustc`) for building `core_rs`
- `maturin` (installed automatically by `core rust build`)

## Install / build `core_rs`

From the repository root:

```bash
# Verify Rust toolchain
cargo --version

# Build and install core_rs into the active Python environment
core rust build

# Confirm activation (optional; exits nonzero if inactive)
core rust status
core rust status --require-active
```

Manual equivalent:

```bash
uv pip install maturin
python -m maturin develop --release --manifest-path core-rs/Cargo.toml
```

The crate lives at `core-rs/` (`module-name = "core_rs"` in `core-rs/pyproject.toml`).

## Activate the Rust backend

Rust is **opt-in**.  Importing `core_rs` alone does not activate native dispatch.
Set:

```bash
export CORE_BACKEND=rust
```

Accepted aliases: `rust`, `core_rs`, `rs` (case-insensitive).

Verify in Python:

```python
from algebra.backend import using_rust
assert using_rust() is True
```

Or:

```bash
CORE_BACKEND=rust core rust status --require-active
```

## Run the benchmark

```bash
CORE_BACKEND=rust uv run python -m benchmarks.apple_uma_mechanical_sympathy --json
CORE_BACKEND=rust uv run python -m benchmarks.apple_uma_mechanical_sympathy --write-report

CORE_BACKEND=rust uv run python -m core.cli bench --suite apple-uma --json
CORE_BACKEND=rust uv run python -m core.cli bench --suite apple-uma --write-report
```

Reports are written to:

- `evals/reports/apple_uma_mechanical_sympathy_latest.json`
- `evals/reports/apple_uma_mechanical_sympathy_latest.md`

## What changes when Rust is active

When `CORE_BACKEND=rust`, `core_rs` is installed, and `using_rust()` is true,
the report should show:

| Field | Rust-active expectation |
|---|---|
| `machine.using_rust` | `true` |
| `machine.core_rs.import_succeeded` | `true` |
| `backend_status.native_status` | `rust_active` |
| `backend_status.diffusion_step_eligible` | `true` |
| `backend_status.vault_recall_rust_zero_copy_eligible` | `true` |
| `tracks.diffusion_step.skipped` | `false` |
| `tracks.exact_cga_recall.cases[].rust_zero_copy_input_eligible` | `true` (contiguous f32) |
| `claim_safety_audit.rust_backend_notes` | Notes native active + scalar copy paths remain |
| `copy_zero_copy_truth_table` | Includes Rust `vault_recall` and `diffusion_step` zero-copy input rows |

Scalar Cl(4,1) ops (`geometric_product`, `cga_inner`, `versor_condition`,
`versor_apply`) **still report copy paths** via `extract_f32_slice` until PR C
(scalar zero-copy boundary cleanup).  This is intentional and honest.

## Python fallback (Rust unavailable)

When `core_rs` is not installed or `CORE_BACKEND` is unset:

| Field | Python-fallback expectation |
|---|---|
| `machine.using_rust` | `false` |
| `backend_status.native_status` | `python_fallback` or `rust_requested_unavailable` |
| `tracks.diffusion_step.skipped` | `true` with explicit `reason` |
| `claim_safety_audit.rust_backend_notes` | Documents Python fallback / activation hint |
| `copy_zero_copy_truth_table` | `diffusion_step` row shows skipped — Rust unavailable |

Do **not** publish a Rust-active report without actually running the commands above
on hardware where `using_rust()` is true.

## Explicit non-claims

This benchmark and report do **not** claim:

- MLX as semantic backend or acceleration (future ADR lane)
- CoreML or Neural Engine acceleration
- "Zero-copy everywhere"
- Token-generation throughput
- ANN / approximate recall
- A fixed hardware speedup multiplier
- Apple endorsement, partnership, or product integration

## Validation

After generating a report:

```bash
uv run python -m pytest -q tests/test_apple_uma_mechanical_sympathy_benchmark.py
```

When Rust is available:

```bash
CORE_BACKEND=rust cargo test --manifest-path core-rs/Cargo.toml
CORE_BACKEND=rust uv run python -m pytest -q tests/test_cga_inner_rust_parity.py
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `using_rust(): false` with `CORE_BACKEND=rust` | `core_rs` not built | `core rust build` |
| `using_rust(): false`, `core_rs` importable | `CORE_BACKEND` unset | `export CORE_BACKEND=rust` |
| `diffusion_step.skipped: true` | Rust not active | Follow activation steps above |
| `native_status: rust_requested_unavailable` | Import failed | Rebuild `core_rs`; check `cargo` toolchain |

## Next lane (PR C)

Scalar Rust zero-copy boundary cleanup (`feat/rust-scalar-cl41-zero-copy-boundary`)
targets `extract_f32_slice` copy tax on scalar hot paths.  That work is separate
from this baseline report lane and requires parity gates before any copy-boundary
claims change.