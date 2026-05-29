# ADR-0181: CORE-native Audio Compiler over the Delta-CRDT Substrate

**Status:** Proposed
**Date:** 2026-05-29
**Authors:** Joshua M. Shay, Core R&D Engine
**Domains:** `sensorium/audio/`, `sensorium/adapters/audio.py`, `packs/audio/`, `core-rs/src/vault.rs` (read-only contract), `evals/audio_sensorium/`
**Depends on:** ADR-0013 (Sensorium Multimodal Protocol), ADR-0180 (Delta-CRDT Sharded Substrate)
**Companion docs:** [audio-compiler-spec.md](../plans/audio-compiler-spec.md), [audio-compiler-eval-plan.md](../plans/audio-compiler-eval-plan.md)

---

## 1. Context & Problem Statement

CORE's sensory boundary is already lawful and text-only-in-practice. `sensorium/protocol.py`
fixes the contract:

- `ProjectionHead.project(S) -> (32,) float32` is the **Logos-recovery boundary**
  (`CL41_DIM = 32`).
- `Modality.AUDIO` already exists in the enum but has no adapter
  (`sensorium/adapters/` ships `text.py` only).
- `ModalityPack` enforces gate/checksum invariants at construction; `ModalityRegistry.mount()`
  runs the unitarity check and `project()` refuses a closed gate.

ADR-0013 (Accepted) requires every new modality to cross this boundary *before* it reaches
`ingest/gate.py`, and forbids touching `ingest/`, `field/`, `generate/`, `vault/`, `vocab/`
to add one. Audio must therefore **arrive already compiled** into a `(32,)` Cl(4,1) multivector.

ADR-0180 (Proposed) introduces the **Delta-CRDT sharded substrate** precisely to absorb the
continuous, high-density streams that audio and vision produce — naming AUDIO explicitly — and
flags one hard constraint we must satisfy (§1.5.2):

> The semilattice claim holds **only** at the `vault/store` layer — not at `versor_apply`
> and not at `compute_trace_hash`. … Any operation upstream of `vault/store` that the
> substrate parallelizes must either (a) be proven order-invariant on its inputs, or
> (b) carry an explicit serialization barrier.

The problem this ADR solves: **how does audio enter CORE as a lawful, deterministic,
replayable modality that is also a well-behaved Delta-CRDT delta producer** — without
violating the no-core-mutation rule, the exact-recall rule, or ADR-0180's order-invariance
obligation?

The wrong answer is an embedding bridge (CLAP/EnCodec/Whisper as substrate). It produces an
opaque latent that cannot be checksummed, cannot be replayed bit-for-bit, and cannot supply
the content-addressed merge key ADR-0180 §1.5.3 demands. The right answer is a **compiler**.

## 2. Decision

We will build `audio_core_v1` as a **deterministic auditory compiler** under `sensorium/audio/`,
lowering canonical waveform input through a typed `AudioIR` into a `(32,)` float32 Cl(4,1)
versor, and we will make its **chunk boundary the Delta-CRDT delta boundary**. Learned models
(Whisper, NeMo, CLAP, EnCodec) are admitted only as subordinate teacher/shadow lanes, never as
the substrate.

The compilation pipeline (detailed in the spec) is:

```text
waveform / live stream
  → canonicalizer    (mono, fixed sample rate, source+canonical sha256)
  → frame grid       (20 ms window / 10 ms hop)
  → acoustic lexer   (energy, voicing, onset, pitch candidates, spectral bands, pauses)
  → typed AudioIR    (speech/pause spans, prosody arcs, turn/overlap events, non-speech atoms)
  → operator registry (pack-local blade aliases + quantized theta rules)
  → rotor lowering   (elliptic bivector rotors only in v1)
  → versor composition (geometric_product → unitize_versor → versor_condition < 1e-6)
  → (32,) float32    == one AudioCompilationUnit
```

Normalization sites stay inside CLAUDE.md's allowlist: quantization and FIR resampling live in
the audio pack/compiler construction boundary, `unitize_versor` is algebra-owned, and **no
hot-path drift repair is added**. CGA null vectors are preserved as null vectors.

### 2.1 The optimal mapping to Delta-CRDT (the load-bearing decision)

ADR-0180 §1.5.2 gives audio a binary choice for everything the substrate parallelizes:
**prove order-invariance, or carry a serialization barrier.** The audio compiler answers
*both*, at two different granularities:

| Granularity | Operation | CRDT treatment | Why |
|---|---|---|---|
| **Within a chunk** | `compile_events` (rotor chaining via `geometric_product`) | **Serialization barrier** | The sandwich product is non-commutative (ADR-0180 §1.5.2 row 3). In-chunk composition runs serially, single-threaded, in canonical event order, inside one thread-local arena. |
| **Across chunks / streams** | merge of `AudioCompilationUnit`s into the Vault | **Order-invariant delta** | Each unit is `(versor, provenance)` written at the `vault/store` layer — the *only* semilattice-eligible layer (ADR-0180 §1.5.2 row 5). Merge is commutative, associative, idempotent. |

This is the synthesis ADR-0180 was waiting for: **the audio chunk boundary is the natural
delta boundary** named in ADR-0180 §2.2 ("at semantic chunk boundaries"). The compiler does the
order-sensitive work behind the barrier and emits only order-invariant deltas across it. The
substrate never parallelizes a non-commutative operation.

### 2.2 Content-addressed merge key from the checksum chain

ADR-0180 §1.5.3 requires the trace-hash reduction to consume vault state in a
**content-addressed order**, not wall-clock arrival order, or `hash(Sequential_Ingest) ==
hash(Concurrent_CRDT_Ingest)` cannot hold. The audio compiler already produces exactly this key
as a byproduct of its layered checksum chain:

```text
source_sha256 → canonical_sha256 → token_stream_sha256 → ir_sha256
              → pack_manifest_sha256 → projection_sha256
```

The **merge key for an audio delta is `(canonical_sha256, ir_sha256, projection_sha256)`**.
Consequences:

- **Idempotence is structural, not asserted.** Identical canonical bytes under an identical
  pack produce an identical key; the CRDT join deduplicates them. This satisfies the
  idempotence leg of the join semilattice (ADR-0180 §2.2) by construction.
- **The content-addressed sort is free.** The merge kernel orders pending audio deltas by this
  key. No re-sort pass is needed at hash time for the audio portion of the path.
- **`projection_sha256` is computed behind the serialization barrier** (§2.1), i.e. on the
  serialized in-chunk composition — satisfying ADR-0180 §1.5.3 point 3 (upstream-of-Vault
  hashes must be computed on the serialized portion).

### 2.3 Physical sharding mirrors the audio domain's natural concurrency

ADR-0180 §2.1 assigns each active modality adapter a thread-local arena and forbids
`sensorium/adapters/*` from writing the global `epistemic_state` directly. For audio this is not
just a mechanical convenience — it is **semantically aligned**: overlapping speakers,
interruptions, and turn boundaries (the `B_OVERLAP`, `B_TURN` atoms in the operator table) are
*literally* concurrent auditory streams. Each concurrent stream gets its own arena; the
`AuditoryEvent` timing (`start_hop`/`end_hop`) is preserved inside each unit so the merge can
reconstruct overlap relationships without a global lock during ingestion. The substrate's
physical sharding is therefore a faithful image of the audio source's structure, not an
impedance mismatch.

### 2.4 Eventual-consistency window is safe for audio

ADR-0180 §3.2 documents a sub-50ms window where a delta sits in the local arena before merge.
Audio is robust to this because:

- `ProjectionHead.project` is **pure on the signal** (ADR-0180 T-4) — the audio compiler never
  reads cross-modal or global state during compilation, so a delayed merge cannot change what it
  produces.
- Each unit retains its own intra-stream event timing, so cross-modal resonance re-anchors on
  merged state after the window closes; recall remains **exact byte-for-byte once merged**
  (ADR-0180 §1.5.5), never approximate.

### 2.5 Gate-closed by default

`audio_core_v1` mounts with `gate_engaged = false` until the eval gates in the companion plan
pass. A closed gate makes `ModalityRegistry.project("audio_core_v1", …)` raise — audio cannot
contribute deltas to any arena until determinism, checksum, unitarity, and mount-validation
gates are green. This reuses the existing registry enforcement; no new gating machinery is
added.

## 3. Consequences

### 3.1 Positive

- **First concrete exerciser of ADR-0180.** Audio is the first continuous modality to land on
  the Delta-CRDT substrate, converting ADR-0180's proof obligation `hash(Sequential) ==
  hash(Concurrent)` from abstract to testable against real delta producers.
- **Order-invariance is proven, not hoped.** §2.1/§2.2 give a concrete serialization barrier and
  a content-addressed key, closing ADR-0180 §1.5.2's open constraint for the audio path.
- **No core mutation.** Everything new lives under `sensorium/audio/`, `packs/audio/`,
  `tests/`, `evals/`. `ingest/`, `field/`, `generate/`, `vault/`, `vocab/` are untouched
  (ADR-0013), and `anti_unifier`/`carrier` need no changes (ADR-0180 §3.1).
- **Trace hygiene composes.** Turn traces record `(canonical_sha256, ir_sha256,
  projection_sha256)` and pack IDs — never raw PCM (ADR-0180 §1.5.5).

### 3.2 Negative / Risks

- **Semantic underreach (v1).** The compiler captures prosody, turn dynamics, and salient
  non-speech events better than lexical content. Acceptable: transcript teachers backfill
  lexical evidence while the substrate stays native.
- **Pack ontology drift.** If blade aliases or operator gains change freely, projections become
  incomparable across versions. Mitigation: the pack is versioned, checksummed, and gate-closed;
  `basis_version` is part of the merge key's pack-manifest leg.
- **Over/under-quantization.** Too-coarse bins flatten meaning; too-fine bins make replay
  brittle. Mitigation: quantization regime is frozen in the manifest and covered by
  cross-platform stability gates.
- **Streaming seam artifacts.** Stateful resampling/pitch/overlap must preserve continuity
  across chunk boundaries. Deferred to the streaming phase; v1 is offline/whole-buffer.
- **Licensing contamination.** openSMILE's OSS build is non-commercial; it is a reference oracle
  only, never a runtime dependency.

## 4. Execution Plan & Proof Obligations

### 4.1 PR stack (additive, doctrine-first)

| PR | Scope | Gate |
|---|---|---|
| **PR-1 (this)** | ADR-0181 + compiler spec + eval plan (docs only) | review |
| **PR-2** | Deterministic substrate: `sensorium/audio/{types,canonical,checksum,resample,frames,lexer,parser,operators,compiler,trace}.py` | determinism + versor unit tests |
| **PR-3** | Pack artifacts `packs/audio/audio_core_v1/*` + `AudioProjectionHead` adapter + mount tests | mount/gate/checksum gates |
| **PR-4** | `evals/audio_sensorium/` fixtures, expected IR, expected projection hashes | full eval-gate table |
| **PR-5** | Delta-CRDT wiring: `AudioCompilationUnit` → thread-local arena → merge key, behind ADR-0180's substrate | sequential==concurrent trace-hash proof |
| **PR-6** | Teacher/shadow lanes (Whisper/NeMo/CLAP/EnCodec) behind optional extras | teachers admitted only as typed hints |

PR-5 must not start until ADR-0180's own §1.5.4 obligations (T-1…T-4) are green on `main` —
the audio delta path rides on them.

### 4.2 Audio-specific proof obligations (extend ADR-0180 §1.5.4)

Per CLAUDE.md §Schema-Defined Proof Obligations, each must be able to **fail loudly** under the
violation it names:

- **A-1 (determinism / ADR-0180 T-4 analog).** Same canonical bytes + same pack ⇒ byte-identical
  `(32,)`, across repeated calls, threads, and processes. Fails if any non-determinism (dict
  ordering, unpinned FIR, float reduction order) leaks in.
- **A-2 (set-equality of merges / ADR-0180 T-1 analog).** A set of `AudioCompilationUnit`s folds
  to the same Vault state regardless of arena flush order (permutation invariance). Fails if a
  delta's contribution is order-sensitive at the merge layer.
- **A-3 (content-addressed key / ADR-0180 T-2 analog).** Trace-hash over audio deltas is
  invariant under set-equal Vault states when keyed by `(canonical_sha256, ir_sha256,
  projection_sha256)`. Fails if the reduction consumes deltas in arrival order.
- **A-4 (serialization barrier).** In-chunk `compile_events` is asserted order-sensitive
  (negative test): swapping two events in canonical order changes the versor. This guards the
  barrier in §2.1 from silently becoming commutative and masking a real ordering bug.
- **A-5 (versor condition).** Every emitted unit satisfies `versor_condition(v) < 1e-6`; the
  threshold is never weakened to pass.
- **A-6 (trace hygiene).** No raw waveform bytes appear in any `TurnEvent`/Vault record; only
  the three hashes + pack IDs + optional teacher provenance.

### 4.3 The strict compilation invariant

```text
same canonical audio bytes
  + same compiler version
  + same pack manifest (incl. basis_version)
  + same operator registry
= same AudioIR
= same versor
= same projection hash
= same CRDT merge key
= identical post-merge Vault contribution (idempotent under re-ingest)
```

The final clause is the ADR-0181 addition to the PDF's original invariant: determinism is not
only replayability, it is **CRDT idempotence** — the property that makes audio safe to shard.

## 5. Alternatives Considered

- **Transcript-first cascade (Whisper as substrate).** Chunked, text-intermediate; discards the
  auditory structure (the "No." vs "No?" vs whispered "no" distinction) and produces no
  checksummable, content-addressed key. Rejected as substrate; retained as teacher.
- **Embedding-first projector (CLAP).** Fast but opaque; cannot be replayed bit-for-bit and
  cannot supply ADR-0180 §1.5.3's content-addressed merge key. Rejected as substrate.
- **Codec-token front end (EnCodec / Moshi-like).** Strategically interesting for future
  full-duplex output; poor first substrate for an epistemically explicit engine. Deferred to a
  shadow/output lane.
- **Audio as a downstream cognition mutation.** Violates ADR-0013's no-core-mutation rule and
  ADR-0180's "adapters never write global state directly" rule. Rejected.

## 6. Cross-References

- ADR-0013 — projection boundary; no-core-mutation constraint.
- ADR-0180 — Delta-CRDT substrate; §1.5.2 order-invariance constraint (closed here for audio),
  §1.5.3 content-addressed merge key, §1.5.4 T-1…T-4 (audio analogs in §4.2), §1.5.5 trace
  hygiene & no hidden background execution.
- ADR-0054 — Vault recall indexing/batching; the read-side contract the merged audio deltas must
  preserve (exact CGA recall).
- CLAUDE.md §Normalization Rules — quantization/FIR confined to pack/compiler construction;
  `unitize_versor` algebra-owned; no hot-path repair.
- `sensorium/protocol.py`, `sensorium/registry.py` — the `ProjectionHead`/`ModalityPack`/
  `ModalityRegistry` contracts this ADR implements an audio instance of.
