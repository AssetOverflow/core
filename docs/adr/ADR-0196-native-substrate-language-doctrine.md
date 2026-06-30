# ADR-0196 — Native Substrate Language Doctrine (Python / Rust / Zig)

**Status:** Accepted.
**Date:** 2026-05-31.

## Decision

CORE is **not** moving toward a wholesale Zig rewrite. This ADR ratifies the
component-by-component native-substrate doctrine recorded in
[`docs/zig/`](../zig/README.md) as binding architectural direction.

The governing conclusion:

- **Python** remains the semantic source of truth — cognition runtime,
  teaching/review workflows, pack ratification, eval harnesses,
  Workbench/operator tooling, and all fast-changing cognition semantics.
- **Rust** (`core-rs`) remains the incumbent native algebra backend — Cl(4,1)
  geometric product, versor apply/closure, CGA inner product, exact recall, and
  diffusion — already parity-gated and opt-in via `CORE_BACKEND=rust`
  (`algebra/backend.py`).
- **Zig** is a *candidate* material for the Ring 1 native substrate layer only:
  Delta-CRDT arenas/deltas/merge kernels, deterministic modality compilers
  (e.g. `audio_core_v1`), stable C ABI surfaces, edge-native ingestion, and
  selected exact-recall challenge kernels — and only after parity and benchmark
  proof.

The architectural question is therefore not *"should CORE be rewritten in
Zig?"* (the answer is no) but *"which substrate components require Zig's
explicit allocation, C ABI clarity, edge-native build story, and deterministic
buffer ownership strongly enough to justify a new native lane?"*

## Ring architecture

| Ring | Layer | Material |
|---|---|---|
| Ring 3 | Operator / Workbench / Review | Python + TypeScript |
| Ring 2 | Semantic cognition runtime | **Python — source of truth** |
| Ring 1 | Native substrate services | **Rust incumbent + Zig candidate** |
| Ring 0 | Hardware / memory substrate | CPU, UMA, future MLX/Metal |

Zig belongs in Ring 1 where its properties matter. It does not belong in Ring 2
merely because the project is getting large.

## Adoption gates (binding)

No Zig component is promoted without passing the G0–G8 ladder defined in
[`docs/zig/adoption-gates.md`](../zig/adoption-gates.md):

```text
G0 doctrine
G1 reference contract locked
G2 prototype behind explicit selector
G3 parity proof
G4 determinism proof
G5 mechanical advantage proof
G6 operational proof
G7 supported backend
G8 default backend, only by later ADR
```

Default-by-availability is forbidden: a present Zig library must never change
runtime behavior. Backend selection is always explicit and trace-visible.

## Decision rules (binding)

1. **Python semantics lock first.** A Zig implementation must trail a locked
   reference contract; it may accelerate or package behavior, never reinterpret
   it.
2. **No approximate substrate.** No ANN/HNSW, cosine fallback, opaque
   embeddings, hot-path repair, or arrival-order-dependent merge.
3. **Explicit ownership or no adoption.** Every component names input/output
   buffers, allocator ownership, failure ownership, lifecycle, determinism
   contract, and fallback.
4. **No hidden background work.** Native workers exist only as explicitly
   mounted components with observable state.
5. **Component migration, not language migration.** Language count is not the
   enemy; boundary ambiguity is.

## Non-goals

This ADR does **not** authorize any Zig implementation. It does not authorize
porting `chat.runtime`, teaching/review, pack ratification, the eval framework,
the Workbench API, identity/safety/ethics policy, or the natural-language
realizer to any native language. Those are semantic/governance layers where
Python remains the right material.

## Consequences

- The doctrine package under `docs/zig/**` is now binding. Future Zig PRs must
  cite the gate they are clearing and the reference contract they trail.
- The first gate instantiation is the Delta-CRDT substrate's **G1
  reference-contract lock**, handled under **ADR-0180** (whose gate obligations
  this ADR governs). That lock corresponds to the **ZC-0** slice in
  [`docs/zig/crdt-substrate/implementation-slices.md`](../zig/crdt-substrate/implementation-slices.md).
- **ZC-1 and beyond (any Zig code) remain unauthorized** until ADR-0180's
  reference contract is Accepted and a separate ADR clears gate G2.

## Alternatives considered

- **Wholesale Zig rewrite** — rejected. It would make CORE's semantic and
  governance layers harder, not truer; it contradicts the *decoding, not
  generating* thesis and the explicit *"not an infrastructure playground"*
  stance.
- **Status quo (Rust-only, no doctrine)** — rejected. Leaving the
  native-substrate boundary undefined risks ad-hoc Zig adoption later, when the
  system is harder to re-materialize around the correct substrate.

## References

- [`docs/zig/README.md`](../zig/README.md) — decision package overview.
- [`docs/zig/adoption-gates.md`](../zig/adoption-gates.md) — G0–G8 proof ladder.
- [`docs/zig/core-native-system/README.md`](../zig/core-native-system/README.md) — ring architecture and native boundary.
- [`docs/zig/runtime-ffi/README.md`](../zig/runtime-ffi/README.md) — C ABI / backend selection / memory ownership.
- ADR-0180 (CRDT substrate · G1 lock), ADR-0181 (audio compiler), ADR-0019 / ADR-0020 / ADR-0054 (recall & algebra anchors).
