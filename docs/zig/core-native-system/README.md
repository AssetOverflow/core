# Zig Guidance — CORE Native System

**Status:** doctrine  
**Component:** native substrate boundary across CORE

This document defines what "CORE native" means if Zig is introduced.

It does not mean rewriting the cognitive runtime in Zig. It means establishing a disciplined native substrate layer below the Python semantic runtime and beside the existing Rust backend.

---

## Ring architecture

CORE should be understood as rings:

```text
Ring 3 — Operator / Workbench / Review
  Python + TypeScript
  CLI, Workbench, evals, review queues, demos

Ring 2 — Semantic cognition runtime
  Python
  chat runtime, teaching, packs, proposition/realizer logic, trace policy

Ring 1 — Native substrate services
  Rust incumbent + Zig candidates
  exact recall, algebra kernels, CRDT merge, modality compilers, FFI

Ring 0 — Hardware / memory substrate
  CPU, UMA, future MLX/Metal integration, filesystem artifacts
```

Zig belongs in Ring 1 where its properties matter. It does not belong in Ring 2 merely because the project is getting large.

---

## What CORE-native should mean

A component is CORE-native if it:

- accepts or emits lawful `(32,)` substrate values;
- preserves exact replay semantics;
- owns a deterministic buffer-level transform;
- has a stable ABI or runtime boundary;
- has a precise error contract;
- can be evaluated independently;
- does not invent semantic truth outside packs/review.

Examples:

```text
CRDT merge kernel
Audio compiler substrate
Batch recall kernel
Native projection compiler
Native edge ingestion runner
```

Non-examples:

```text
Teaching review policy
Identity pack doctrine
Surface realizer wording
Workbench UX state
Domain curriculum planning
```

---

## Language placement

| Layer | Preferred material | Why |
|---|---|---|
| Pack/review/evals | Python | semantic iteration, proof harness, fixtures, operator workflows |
| Current algebra hot path | Rust incumbent | already parity-gated, PyO3/NumPy integrated, Rayon parallelism |
| CRDT substrate | Zig candidate | explicit allocator, C ABI, content-addressed memory law |
| Audio compiler | Zig candidate after Python spec | streaming deterministic compiler, edge-native C ABI |
| Workbench UI | TypeScript/React | browser-native UI |
| Standalone edge runner | Zig candidate later | no-Python deployment and explicit runtime ownership |

---

## Native substrate package shape

If Zig lands, it should be grouped as a native substrate package, not scattered across semantics:

```text
core-zig/
  build.zig
  include/
    core_native.h
    core_crdt.h
    core_audio.h
    core_recall.h
  src/
    crdt/
    audio/
    recall/
    ffi/
    version.zig
  tests/
```

No Zig code should live under `chat/`, `teaching/`, `generate/`, `packs/`, or `workbench/` unless a later ADR narrows a specific native subcomponent.

---

## Backend selection doctrine

The native system must be explicitly selected.

Recommended selectors:

```text
CORE_NATIVE_BACKEND=python
CORE_NATIVE_BACKEND=rust
CORE_NATIVE_BACKEND=zig
CORE_CRDT_BACKEND=rust|zig|python
CORE_AUDIO_COMPILER_BACKEND=python|zig
```

The active backend should be trace-visible for any runtime path where it can affect performance or replay evidence.

Forbidden:

```text
load Zig because the library exists
switch backend mid-turn
use native backend without recording backend identity
silently fall back after partial mutation
```

Fallback is good. Silent semantic fallback is not.

---

## What should be native first

Priority order:

1. CRDT arena/delta/merge.
2. Audio canonicalizer/frame/lexer/IR hash.
3. AudioCompilationUnit C ABI and CRDT handoff.
4. `vault_recall_batch` challenge implementation.
5. Standalone edge ingestion runner.

This order follows the actual pressure points: continuous modalities, exact concurrent ingestion, and deterministic native compilation.

---

## What should not be native now

Do not port:

- `chat.runtime`;
- teaching proposals/review;
- pack ratification;
- eval framework;
- Workbench API;
- identity/safety/ethics policy;
- natural language realizer logic.

These are not slow buffer kernels. They are semantic/governance layers where Python remains the right material.

---

## Native runtime invariants

Every native CORE component must preserve:

```text
versor_condition(F) < 1e-6 where it emits field state
no approximate recall
no hidden normalization
no hidden global mutation
no substrate embeddings
no raw sensory payload in trace/Vault records unless explicitly allowed by ADR
content-addressed ordering where concurrency can reorder arrival
```

---

## Edge-native horizon

A future edge runner may be Zig-native if it has a narrow, frozen contract:

```text
load signed/checksummed packs
mount selected compiler(s)
accept local signal chunks
compile to AudioCompilationUnit / VisionCompilationUnit / MotorUnit
push into local arena
explicitly merge_tick
publish replay evidence
serve health/status
```

That runner should not own teaching review, pack mutation, cloud sync, or semantic expansion.

---

## Decision posture

Zig should be treated as a **native substrate material**, not a general project language.

The masterpiece standard is not one-language purity. It is boundary purity: every layer made from the correct material, with no confusion about what it is allowed to know or mutate.
