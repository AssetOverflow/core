# Zig Native Substrate Decision Package

**Status:** Decision package / doctrine draft  
**Scope:** `docs/zig/**` only  
**Purpose:** Decide where Zig belongs in CORE before the system becomes harder to re-materialize around the correct native substrate.

This directory does **not** authorize a wholesale rewrite of CORE in Zig.

It establishes a component-by-component doctrine for when Zig is the right material, when Rust remains the right material, and when Python must remain the semantic source of truth. The goal is consistency without premature ossification: use the right tool where the physics of the component demands it, and refuse novelty where it would fragment the architecture.

---

## Governing conclusion

Zig is not the language for the whole CORE runtime.

Zig is a strong candidate for the **native substrate layer**:

```text
Native substrate:
  - Delta-CRDT arena / delta / merge kernel
  - modality compilers, starting with audio_core_v1
  - C ABI surfaces for edge/local/native runtime integration
  - selected exact recall / batch recall kernels, if parity and benchmark gates prove advantage
  - future no-Python edge ingestion components

Python semantic runtime:
  - pack authoring and ratification
  - teaching / review / proposal workflows
  - eval lanes and proof obligations
  - Workbench API and operator tooling
  - fast-changing cognition semantics

Rust native backend:
  - existing proven algebra hot paths
  - PyO3/NumPy acceleration surfaces already parity-gated
  - current `core-rs` kernels until Zig wins by evidence
```

The correct architectural question is therefore not:

```text
Should CORE be rewritten in Zig?
```

It is:

```text
Which substrate components require Zig's explicit allocation, C ABI clarity,
edge-native build story, and deterministic buffer ownership strongly enough to
justify a new native lane?
```

---

## Directory map

| Directory | Component | Decision posture |
|---|---|---|
| [`crdt-substrate/`](crdt-substrate/) | Delta-CRDT arenas, deltas, merge kernel, content ordering | Zig is a first-class candidate. Prototype before replacing Rust. |
| [`audio-compiler/`](audio-compiler/) | Deterministic audio compiler, chunk units, checksums, native audio lexer | Zig is strongly preferred for long-term native substrate if Python spec is locked first. |
| [`core-native-system/`](core-native-system/) | Native CORE boundary and what belongs outside Python | Define a ring architecture; no full runtime rewrite. |
| [`runtime-ffi/`](runtime-ffi/) | C ABI, backend selection, memory ownership, error surfaces | Zig must enter through stable FFI, not through ad-hoc bindings. |
| [`algebra-kernels/`](algebra-kernels/) | Cl(4,1), recall, diffusion, batch recall | Rust remains incumbent; Zig may challenge only through parity and benchmark gates. |
| [`adoption-gates.md`](adoption-gates.md) | Cross-cutting proof gates | No Zig component is promoted without deterministic, semantic, and operational proof. |

---

## Decision rules

### Rule 1 — Python semantics lock first

Any Zig implementation must trail a locked semantic contract. If Python currently defines the reference behavior, Zig may accelerate or package that behavior but may not reinterpret it.

Zig work is invalid if it starts by asking the runtime to trust a new behavior because it is native.

### Rule 2 — no approximate substrate

Zig must not introduce approximate recall, embedding fallback, lossy indexing, or hidden normalization. Any native component must preserve CORE's exactness doctrine.

Permitted:

```text
same semantics, better mechanical substrate
same inputs, same outputs, lower latency
same deltas, stable content-addressed order
same compiler IR, stable projection hash
```

Forbidden:

```text
approximate nearest neighbor
cosine fallback
opaque embedding substrate
hot-path repair
arrival-order dependent merge
runtime mutation hidden behind native worker threads
```

### Rule 3 — explicit ownership or no adoption

Zig is only worth adding where explicit ownership matters. Every proposed Zig component must name:

1. input buffers,
2. output buffers,
3. allocator ownership,
4. failure ownership,
5. lifecycle / free semantics,
6. determinism contract,
7. Python/Rust fallback behavior.

### Rule 4 — no hidden background work

Native workers may exist only as explicitly mounted runtime components with observable state. The merge kernel, audio compiler, and future native ingestion services must surface pending counts, errors, and replay evidence. There must be no invisible daemon that mutates truth-bearing state.

### Rule 5 — component migration, not language migration

CORE may become multi-native:

```text
Python: source of semantic truth and proof workflows
Rust: incumbent acceleration backend
Zig: substrate candidate for CRDT/modality/edge-native surfaces
TypeScript/React: Workbench UI
```

This is acceptable only if each boundary is crisp. Language count is not the enemy; boundary ambiguity is.

---

## Promotion statuses

Use these statuses in future Zig docs and PRs:

| Status | Meaning |
|---|---|
| `doctrine` | Decision only. No implementation authorized. |
| `prototype` | Experimental implementation allowed behind an explicit flag. |
| `parity-candidate` | Has reference parity tests; not default. |
| `bench-candidate` | Has parity and benchmark evidence; still explicit opt-in. |
| `supported-backend` | Supported but not necessarily default. |
| `default-backend` | May become default only after an ADR accepts replay, parity, fallback, ops, and CI evidence. |

No document in `docs/zig/**` should silently jump a component beyond these statuses.

---

## Current recommendation

Priority order:

1. **CRDT substrate Zig prototype** — arena, delta, join, merge, content hash.
2. **Audio compiler Zig substrate prototype** — canonical PCM, frame grid, deterministic lexer, AudioIR hash, projection hash boundary.
3. **Runtime FFI contract** — caller-owned buffers, typed errors, no hidden allocation surprises.
4. **Batch recall challenge** — optional Zig/Rust comparison for `vault_recall_batch` only after parity tests exist.
5. **Standalone edge-native ingestion runner** — future, after the above contracts stabilize.

Non-priority:

```text
chat/runtime.py rewrite
teaching/review rewrite
Workbench rewrite
eval harness rewrite
pack authoring rewrite
```

Those are semantic and governance-heavy surfaces; Zig would make them harder, not truer.
