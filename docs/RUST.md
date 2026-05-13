# Rust Extension (core-rs)

## Why Rust

Three operations dominate CORE-AI's runtime:

1. geometric_product — O(32^2) = 1024 multiply-adds per call, called 2-3x per versor_apply
2. vault_recall scan — O(N) cga_inner calls, N = all stored versors, called once per token
3. holonomy_encode — 2 * prompt_length geometric products in sequence

None of these release the Python GIL. Rayon gives vault_recall true multithreaded
parallelism across CPU cores. The geometric product loop is cache-friendly and
compiler-autovectorized when opt-level=3 + lto=true.

## What is in Rust

| Module | Rust file | Why |
|---|---|---|
| Cl(4,1) product | cl41.rs | Hot inner loop, 1024 MADs, autovectorizable |
| Versor ops | versor.rs | 3x geometric_product per step, allocation-free |
| CGA inner product | cga.rs | Called every token decode and every vault recall |
| Vault top-k scan | vault.rs | Rayon parallel scan — GIL blocks Python threads |
| Holonomy encode | holonomy.rs | 200+ products for long prompts |
| Batch propagation | propagate.rs | Beam search / speculative decode |

## What stays in Python

| Layer | Why |
|---|---|
| VocabManifold | Word lookup, edge rotor construction — called once per token, not per step |
| SessionContext | Orchestration, not arithmetic |
| FieldState | Plain dataclass |
| PersonaMotor | Motor construction is infrequent |

## Zero-Copy Semantics

All f32 arrays are passed as numpy arrays from Python.
The Rust functions receive them as `[f32; 32]` stack arrays — copied once from
the numpy buffer into a stack frame, processed, and returned as a new numpy array.
No heap allocation inside any hot-path function.

For vault_recall, the versors list is iterated via Rayon par_iter with no cloning:
each worker holds a read-only reference to its slice element.

## Build

Requires maturin and a Rust toolchain (stable 1.75+).

```bash
cd core-rs
pip install maturin
maturin develop --release   # installs core_rs into current venv
```

Or build a wheel:
```bash
maturin build --release
pip install target/wheels/*.whl
```

Verify Rust backend is active from Python:
```python
from algebra.backend import using_rust
print(using_rust())  # True if core_rs is installed
```

## Running Rust Tests

```bash
cd core-rs
cargo test
```

## Type Safety Contract

All multivectors entering the Rust layer are validated as f32 arrays of length 32
by extract_f32_slice() in lib.rs. Type errors surface immediately as Python
ValueError with a descriptive message rather than silent memory corruption.

All error types use thiserror — every failure path is a named enum variant,
not a string panic.
