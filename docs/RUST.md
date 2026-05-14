# Rust Extension (core-rs)

## Why Rust

Three operations dominate CORE-AI's runtime:

1. `geometric_product` — O(32^2) = 1024 multiply-adds per call, called 2-3x per `versor_apply`
2. `vault_recall` scan — O(N) CGA inner product calls, N = all stored versors, called during generation recall
3. `cga_inner` — called by vocabulary/proposition nearest selection and vault recall

None of the Python fallback paths release the Python GIL. Rayon gives `vault_recall` true multithreaded parallelism across CPU cores. The geometric product loop is cache-friendly and compiler-optimized in release mode.

## What is in Rust

| Module | Rust file | Why |
|---|---|---|
| Cl(4,1) product | `cl41.rs` | Hot inner loop, 1024 MADs |
| Versor ops | `versor.rs` | 3x geometric product per field step |
| CGA inner product | `cga.rs` | Called by nearest search and recall |
| Vault top-k scan | `vault.rs` | Rayon parallel scan |

## What stays in Python

| Layer | Why |
|---|---|
| `VocabManifold` | Word/morphology/language metadata and exact candidate filtering |
| `SessionContext` | Orchestration, not arithmetic |
| `FieldState` | Plain dataclass |
| `PersonaMotor` | Motor construction is infrequent |

## Zero-Copy Semantics

The runtime contract is numpy `float32` arrays of length 32. Rust reads them into stack `[f32; 32]` values, executes the hot loop, and returns a new numpy array. The Python fallback remains behaviorally available when `core_rs` is not installed.

## Build / Activate

Requires a Rust toolchain and maturin. Prefer the uv-native flow so the repo does not depend on `pip` being installed inside `.venv`:

```bash
core rust status
core rust test
core rust build
core rust status --require-active
```

Equivalent explicit maturin command:

```bash
uv run --with maturin maturin develop --release --manifest-path core-rs/Cargo.toml
```

Verify Rust backend is active from Python:

```bash
uv run python -c "from algebra.backend import using_rust; print(using_rust())"
```

Expected:

```text
True
```

## Running Rust Tests

```bash
core rust test
# or
cargo test --release --manifest-path core-rs/Cargo.toml
```

## Type Safety Contract

All multivectors entering the Rust layer must be numpy-compatible `float32` arrays of length 32. Type errors surface as Python `ValueError` rather than silent memory corruption.

## Failure Mode

If `core_rs` is absent or fails to import, `algebra.backend` silently falls back to Python. This keeps the engine correct but not mechanically optimal. Use:

```bash
core doctor --rust --require-rust
```

to fail fast when benchmarking or profiling requires the Rust backend.
