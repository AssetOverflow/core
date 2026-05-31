# Zig Guidance — Audio Compiler

**Status:** doctrine / prototype candidate  
**Component:** `audio_core_v1` deterministic compiler substrate  
**Primary governing ADR:** ADR-0181

The audio compiler is the second strongest Zig candidate after the CRDT substrate, and may become the best long-term fit once the Python reference spec is locked.

Audio in CORE must not enter as an opaque embedding. It must enter as a deterministic compiler product: canonical waveform bytes become typed AudioIR, then lawful operators, then a `(32,) float32` versor plus content-addressed provenance.

---

## Why this component is suitable for Zig

The audio compiler is streaming, buffer-heavy, deterministic, and edge-native. That maps well to Zig.

Zig is suitable for:

- canonical PCM handling;
- fixed sample-rate frame grids;
- deterministic quantization;
- acoustic lexer passes;
- typed event serialization;
- checksum chain construction;
- pack-local read-only operator tables;
- chunk-to-compilation-unit emission;
- C ABI handoff to CRDT arenas;
- future no-Python streaming compilation.

Zig is not suitable for replacing the teacher/shadow lanes. Whisper, NeMo, CLAP, EnCodec, and similar tools remain optional Python-side evidence lanes. They label or align; they never define the substrate.

---

## Existing contract to preserve

ADR-0181 requires:

```text
waveform / live stream
  -> canonicalizer
  -> frame grid
  -> acoustic lexer
  -> typed AudioIR
  -> operator registry
  -> rotor lowering
  -> versor composition
  -> (32,) float32 AudioCompilationUnit
```

The chunk boundary is the Delta-CRDT delta boundary:

```text
inside chunk: serial rotor composition, order-sensitive
across chunks: order-invariant CRDT deltas
```

The native compiler must never parallelize the non-commutative `compile_events` loop. It may parallelize independent chunks only after each chunk has its own serialization barrier.

---

## What should be in Zig

A Zig audio compiler lane should include:

```text
core-zig/src/audio/signal.zig
core-zig/src/audio/canonical.zig
core-zig/src/audio/resample.zig
core-zig/src/audio/frames.zig
core-zig/src/audio/lexer.zig
core-zig/src/audio/ir.zig
core-zig/src/audio/operators.zig
core-zig/src/audio/project.zig
core-zig/src/audio/checksum.zig
core-zig/src/audio/ffi.zig
include/core_audio.h
```

### Canonicalizer

Responsibilities:

- accept caller-owned PCM-like input;
- downmix to mono if policy allows;
- resample to the declared rate using frozen coefficients;
- emit source and canonical hashes;
- produce canonical sample buffer with declared dtype and sample rate.

Forbidden:

- relying on platform resampler defaults;
- hidden model inference;
- lossy semantic classification;
- leaking raw PCM past the trace boundary.

### Frame grid

Responsibilities:

- deterministic window length;
- deterministic hop length;
- deterministic zero padding;
- no wall-clock dependent chunking;
- explicit continuity state for streaming phase.

### Acoustic lexer

Responsibilities:

- measure facts, not guess semantics;
- quantize before semantic promotion;
- emit integer-like token payloads;
- avoid unstable float hashes;
- keep all thresholds pack-owned and versioned.

### AudioIR serialization

Responsibilities:

- canonical event order;
- stable field ordering;
- no map/dict iteration dependence;
- stable hash independent of allocation address;
- content anchors as evidence only.

### Operator lowering

Responsibilities:

- read pack-local, checksummed blade aliases;
- use declared elliptic rotor rules for v1;
- quantize theta before rotor construction;
- compose in canonical event order;
- call algebra-owned `unitize_versor` semantics or an approved native equivalent;
- verify `versor_condition < 1e-6` without weakening.

---

## AudioCompilationUnit contract

The Zig compiler should produce a C-compatible equivalent of:

```text
canonical_sha256
ir_sha256
pack_id
pack_manifest_sha256
projection_sha256
versor: [32]f32
versor_condition
merge_key = (canonical_sha256, ir_sha256, projection_sha256)
```

The unit is the only audio object that may enter a CRDT arena.

No raw PCM should appear in the Vault record or TurnEvent trace. Provenance is hash-based:

```text
{ merge_key, pack_id, pack_manifest_sha256 }
```

---

## Minimum C ABI sketch

```c
typedef struct CoreAudioCompiler CoreAudioCompiler;
typedef struct CoreAudioUnit CoreAudioUnit;

typedef struct CoreAudioCompileInput {
    const float* samples;
    unsigned long sample_count;
    unsigned int sample_rate;
    unsigned int channels;
    unsigned long start_ms;
    unsigned long end_ms;
} CoreAudioCompileInput;

CoreAudioCompiler* core_audio_compiler_open(
    const char* manifest_path,
    CoreAudioError* err
);

void core_audio_compiler_free(CoreAudioCompiler* compiler);

int core_audio_compile(
    const CoreAudioCompiler* compiler,
    const CoreAudioCompileInput* input,
    CoreAudioUnit** out_unit,
    CoreAudioError* err
);

void core_audio_unit_free(CoreAudioUnit* unit);

int core_audio_unit_get_versor(
    const CoreAudioUnit* unit,
    float out_versor[32],
    CoreAudioError* err
);

int core_audio_unit_get_merge_key(
    const CoreAudioUnit* unit,
    unsigned char out_canonical_sha256[32],
    unsigned char out_ir_sha256[32],
    unsigned char out_projection_sha256[32],
    CoreAudioError* err
);
```

The final ABI must be ratified before implementation is treated as supported.

---

## What should remain Python first

The Python implementation/spec should remain first for:

- IR schema design;
- fixture authoring;
- expected hash generation;
- pack manifest evolution;
- eval harness;
- teacher/shadow lanes;
- operator table experimentation;
- Workbench display.

Zig should not become the place where audio ontology is invented. It should become the place where a locked ontology is compiled with mechanical discipline.

---

## Required proof obligations

### A-Z1 — Canonical determinism

Same source bytes and same pack produce same canonical hash, frame tokens, IR hash, projection hash, and versor.

### A-Z2 — Serialization barrier

Swapping two order-sensitive in-chunk events must change the compiled versor. This negative test proves the compiler has not accidentally treated non-commutative composition as a CRDT merge.

### A-Z3 — Merge-key idempotence

Re-ingesting the same AudioCompilationUnit must be a no-op after CRDT merge.

### A-Z4 — Trace hygiene

No raw PCM bytes may appear past compiler-local buffers.

### A-Z5 — Teacher isolation

Teacher hints may affect content/evidence anchors, but must not mutate `projection_sha256` unless a separate ADR explicitly changes substrate policy.

### A-Z6 — Closure invariant

Every emitted unit must satisfy:

```text
versor_condition(v) < 1e-6
```

No threshold weakening is allowed.

---

## Migration sequence

1. Keep Python `sensorium/audio/**` as the reference implementation.
2. Freeze fixtures and expected hashes.
3. Build Zig canonicalizer + frame grid first.
4. Add lexer and IR serialization.
5. Add operator lowering after Python semantics are stable.
6. Emit `AudioCompilationUnit` through C ABI.
7. Wire to CRDT arena only behind explicit selector.
8. Promote only after parity, determinism, and sequential==concurrent proofs pass.

---

## Non-goals

Zig audio must not:

- make ASR the substrate;
- use CLAP/EnCodec embeddings as the projection;
- hide stochastic model calls inside compile;
- add normalization outside the allowed compiler boundary;
- bypass `ModalityPack` gate closure;
- write the global Vault directly;
- compile audio into any shape other than `(32,) float32` at the projection boundary;
- skip the CRDT merge-key discipline.

---

## Recommendation

Make Zig a first-class experimental lane for `audio_core_v1` after Python PR-2/PR-4 semantics and fixtures are locked.

Do not make Zig the first implementation of the audio ontology. Make it the mechanically superior implementation of a proven compiler contract.
