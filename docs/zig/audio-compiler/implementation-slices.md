# Zig Audio Compiler — Implementation Slices

**Status:** doctrine / implementation plan  
**Depends on:** `docs/zig/audio-compiler/README.md`

This document breaks a future Zig audio compiler into small, reviewable slices.

Zig must not become the place where the audio ontology is invented. Python/spec/fixture work remains the reference first. Zig becomes valuable only after that reference is stable.

---

## ZA-0 — Reference lock

Purpose: lock the Python audio compiler behavior before native port.

Required reference surfaces:

- canonical signal formation;
- frame grid;
- acoustic lexer;
- typed AudioIR;
- operator registry;
- projection hash;
- `AudioCompilationUnit` merge key;
- trace hygiene;
- teacher isolation.

Exit gate:

```text
Python fixtures and expected hashes are green.
No Zig implementation starts by defining semantics.
```

---

## ZA-1 — Canonicalizer and frame grid

Purpose: port deterministic buffer mechanics first.

Candidate files:

```text
core-zig/src/audio/canonical.zig
core-zig/src/audio/frames.zig
core-zig/src/audio/checksum.zig
```

Required checks:

- same canonical hash as reference fixtures;
- same frame count;
- same padding behavior;
- same source/canonical hash semantics;
- no raw PCM exported beyond the compiler-local boundary.

---

## ZA-2 — Acoustic lexer

Purpose: port measured fact extraction.

Candidate file:

```text
core-zig/src/audio/lexer.zig
```

Required checks:

- same energy bins;
- same voiced/unvoiced classification;
- same pause/onset classification;
- same pitch candidate quantization where implemented;
- stable token stream hash.

The lexer measures facts. It must not infer semantic truth or call teacher models.

---

## ZA-3 — AudioIR serialization

Purpose: produce canonical typed IR from tokens.

Candidate file:

```text
core-zig/src/audio/ir.zig
```

Required checks:

- same event families as reference;
- same canonical event ordering;
- same serialized field order;
- same `ir_sha256`;
- content anchors remain evidence, not substrate.

---

## ZA-4 — Operators and projection

Purpose: lower AudioIR to one `(32,) float32` unit.

Candidate files:

```text
core-zig/src/audio/operators.zig
core-zig/src/audio/project.zig
```

Required checks:

- same pack manifest interpretation;
- same operator lookup;
- same theta quantization;
- canonical event-order composition;
- same projection hash;
- `versor_condition < 1e-6`;
- negative test proves in-chunk event order matters.

The compiler must never parallelize the non-commutative in-chunk composition loop.

---

## ZA-5 — AudioCompilationUnit C ABI

Purpose: expose compiled units to Python/CRDT without Python object semantics.

Candidate files:

```text
core-zig/include/core_audio.h
core-zig/src/audio/ffi.zig
core_native/audio_zig.py
```

Required checks:

- unit exposes `[32]f32`;
- unit exposes canonical, IR, and projection hash legs;
- unit exposes pack/projection metadata needed for provenance;
- no raw PCM exported;
- Zig-owned unit has a matching free function;
- invalid input produces typed error.

---

## ZA-6 — CRDT handoff

Purpose: write compiled units into thread-local arenas behind explicit selector.

Depends on:

- audio compiler parity;
- CRDT backend parity, or the current reference CRDT path.

Required checks:

- one compiled unit writes to one local arena;
- duplicate unit dedups by merge key;
- arena flush order does not change final Vault contribution;
- sequential vs concurrent proof passes;
- pending-delta count is observable.

---

## ZA-7 — Streaming phase

Purpose: preserve continuity across chunk seams.

Deferred until offline/whole-buffer v1 is locked.

Streaming must add:

- explicit stream state object;
- deterministic carry-over buffers;
- stable chunk IDs;
- seam tests;
- clear reset behavior;
- no hidden global state.

Exit gate:

```text
streamed chunks produce the same result as whole-buffer mode where equivalence is claimed.
```

---

## Stop conditions

Stop or revert the Zig lane if:

- parity fails and requires semantic changes;
- teacher outputs begin changing substrate projection;
- trace hygiene is weakened;
- raw PCM leaks into Vault/TurnEvent records;
- closure thresholds are weakened;
- backend selection becomes automatic by library presence.
