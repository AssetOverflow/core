# ADR-0197: CORE-native Vision Compiler over the Delta-CRDT Substrate

**Status:** Accepted — implementation landed
**Date:** 2026-05-31
**Implementation:** `sensorium/vision/` + `sensorium/adapters/vision.py`, `packs/vision/vision_core_v1/` (PR #537). Proof obligations are covered by `tests/test_vision_compiler.py`, `tests/test_vision_crdt_merge.py`, `tests/test_vision_sensorium_mount.py`, and `tests/test_vision_eval_gates.py`.
**Authors:** Joshua M. Shay, Core R&D Engine
**Domains:** `sensorium/vision/`, `sensorium/adapters/vision.py`, `packs/vision/`, `core-rs/src/vault.rs` (read-only contract), `evals/vision_sensorium/`
**Depends on:** ADR-0013 (Sensorium Multimodal Protocol), ADR-0180 (Delta-CRDT Sharded Substrate), ADR-0181 (Audio Compiler — structural precedent)
**Companion docs:** [vision-compiler-spec.md](../plans/vision-compiler-spec.md), [vision-compiler-eval-plan.md](../plans/vision-compiler-eval-plan.md)

---

## 1. Context & Problem Statement

`sensorium/protocol.py` already fixes the contract vision must satisfy:

- `ProjectionHead.project(S) -> (32,) float32` is the **Logos-recovery boundary** (`CL41_DIM = 32`). A visual scene is recovered as words in the one manifold; once it crosses the boundary the field has no concept of "vision."
- `Modality.VISION` already exists in the enum but has **no adapter and no compiler** — `sensorium/adapters/` ships `text.py` and `audio.py` only.
- `ModalityPack` enforces gate/checksum invariants at construction; `ModalityRegistry.mount()` runs the unitarity check and `project()` refuses a closed gate.

ADR-0013 (Accepted) requires every new modality to cross this boundary *before* it reaches `ingest/gate.py`, and forbids touching `ingest/`, `field/`, `generate/`, `vault/`, `vocab/` to add one. Vision must therefore **arrive already compiled** into a `(32,)` Cl(4,1) versor.

ADR-0180 (Proposed) introduces the Delta-CRDT sharded substrate **explicitly to absorb the continuous, high-density streams that audio and vision produce** — vision is named, not incidental — and imposes the same hard constraint audio answered (§1.5.2): any operation upstream of `vault/store` that the substrate parallelizes must either be proven order-invariant on its inputs, or carry an explicit serialization barrier.

ADR-0181 (Proposed) is the structural precedent. This ADR deliberately inherits its skeleton — pipeline shape, checksum chain, merge-key triple, serialization-barrier discipline, PR ladder, gate-closed default, and the **"compiler, not embedding bridge"** doctrine. What it does **not** inherit is audio's canonical ordering or blade semantics: those are temporal and acoustic. Vision's manifest is **spatial and scale-structured**, and that single difference is the load-bearing redesign of §2.1 and §2.6.

The problem this ADR solves: **how does vision enter CORE as a lawful, deterministic, replayable modality that is also a well-behaved Delta-CRDT delta producer** — without violating the no-core-mutation rule, the exact-recall rule, or ADR-0180's order-invariance obligation.

The wrong answer is an embedding bridge (ViT / CLIP / DINOv2 / SAM as substrate). The temptation is far stronger here than for audio because pretrained vision encoders are excellent — and that is exactly why it must be resisted. An opaque latent cannot be checksummed, cannot be replayed bit-for-bit, and cannot supply the content-addressed merge key ADR-0180 §1.5.3 demands. The right answer is a **deterministic visual compiler**.

## 2. Decision

We will build `vision_core_v1` as a **deterministic visual compiler** under `sensorium/vision/`, lowering a canonical image (or single video frame) through a typed `VisionIR` into a `(32,)` float32 Cl(4,1) versor, and we will make its **spatial chunk boundary the Delta-CRDT delta boundary**. Learned models (ViT, CLIP, DINOv2, SAM, depth/flow estimators) are admitted only as subordinate teacher/shadow lanes, never as the substrate.

The compilation pipeline (detailed in the companion spec) mirrors audio's shape with spatial substitutions:

```text
image / single video frame
  → canonicalizer    (fixed colorspace + gamma, fixed resampling grid, source+canonical sha256)
  → spatial grid     (tile lattice × scale pyramid — the analog of audio's frame grid)
  → visual lexer     (orientation energy, spatial-frequency bands, luminance/chroma stats,
                      corner/blob onsets, region boundaries)
  → typed VisionIR   (regions/segments, contour arcs, salient-object events, texture atoms,
                      content anchors)
  → operator registry (pack-local blade aliases + quantized theta rules)
  → rotor lowering   (elliptic bivector rotors only in v1)
  → versor composition (geometric_product → unitize_versor → versor_condition < 1e-6)
  → (32,) float32    == one VisionCompilationUnit
```

Normalization sites stay inside CLAUDE.md's allowlist: quantization and resampling live in the vision pack/compiler construction boundary, `unitize_versor` is algebra-owned, and **no hot-path drift repair is added**.

### 2.1 The optimal mapping to Delta-CRDT (the load-bearing decision)

ADR-0180 §1.5.2 gives vision the same binary choice it gave audio: prove order-invariance, or carry a serialization barrier. We answer both, at two granularities — but the *within-chunk ordering is the part that differs from audio and must be designed, not copied*.

| Granularity | Operation | CRDT treatment | Why |
|---|---|---|---|
| **Within a chunk** (one tile, or one image at one scale) | `compile_events` (rotor chaining via `geometric_product`) | **Serialization barrier** | The sandwich product is non-commutative. In-chunk composition runs serially, single-threaded, in **canonical spatial order**, inside one thread-local arena. |
| **Across tiles / scales / frames** | merge of `VisionCompilationUnit`s into the Vault | **Order-invariant delta** | Each unit is `(versor, provenance)` written at the `vault/store` layer — the only semilattice-eligible layer. Merge is commutative, associative, idempotent. |

**The redesign vs ADR-0181.** Audio's canonical within-chunk order is the temporal hop index — total and obvious. Vision has no time axis inside a frame, so the canonical order must be an **explicit, deterministic, resolution-independent spatial total order over the IR events**. The v1 proposal: order by `(scale_level, morton_code(tile_row, tile_col), event_category_precedence, stable_event_id)`, where `morton_code` is a Z-order curve over the fixed tile lattice. This makes the in-chunk fold reproducible and gives proof obligation V-4 something concrete to assert against. **This ordering rule is the single most important thing to red-line in this ADR** (see §2.6).

### 2.2 Content-addressed merge key from the checksum chain

Identical to ADR-0181 §2.2 in structure; only the layer names change:

```text
source_sha256 → canonical_sha256 → tile_stream_sha256 → ir_sha256
              → pack_manifest_sha256 → projection_sha256
```

The **merge key for a vision delta is `(canonical_sha256, ir_sha256, projection_sha256)`** — the same triple `AudioCompilationUnit.merge_key` exposes, so the existing merge kernel and `core-rs` content-addressed sort apply unchanged. Consequences carry over verbatim: idempotence is structural (identical canonical pixels under an identical pack → identical key → CRDT join deduplicates), the content-addressed sort is free, and `projection_sha256` is computed behind the serialization barrier on the serialized in-chunk composition (ADR-0180 §1.5.3 point 3).

### 2.3 Physical sharding mirrors the visual domain's natural concurrency

ADR-0180 §2.1 assigns each active adapter a thread-local arena and forbids `sensorium/adapters/*` from writing global `epistemic_state` directly. For vision this is semantically aligned, not merely mechanical: **independent spatial regions, scale levels, and successive video frames are genuinely concurrent visual streams.** Each gets its own arena; each `VisualEvent` retains its tile/scale coordinates so the merge reconstructs spatial layout without a global lock during ingestion. The substrate's physical sharding is a faithful image of the visual source's structure — a tiled image is *already* a set of independent deltas.

### 2.4 Eventual-consistency window is safe for vision

Same argument as ADR-0181 §2.4. `ProjectionHead.project` is pure on the signal (ADR-0180 T-4): the vision compiler reads no cross-modal or global state during compilation, so a delayed merge cannot change what it produces. Each unit retains its own spatial coordinates, so cross-modal resonance re-anchors on merged state after the sub-50ms window closes; recall remains exact byte-for-byte once merged, never approximate.

### 2.5 Gate-closed by default

`vision_core_v1` mounts with `gate_engaged = false` until the eval gates in the companion plan pass. A closed gate makes `ModalityRegistry.project("vision_core_v1", …)` raise — vision contributes no deltas to any arena until determinism, checksum, unitarity, and mount-validation gates are green. This reuses existing registry enforcement; no new gating machinery is added.

### 2.6 Blade semantics for vision v1

The `(32,)` output shape and the unitarity check are **rigid contract**. The companion spec resolves the v1 blade semantics as pack-local, versioned, checksummed elliptic bivector aliases over measured visual facts. Audio used "elliptic bivector rotors only in v1" over an acoustic event vocabulary; vision keeps the elliptic law but assigns aliases to spatial/scale structure.

Cl(4,1) gives us (per `algebra/cl41.py`): grade-0 (scalar, idx 0), grade-1 (5 vectors, idx 1–5), grade-2 (10 bivectors, idx 6–15), grade-3 (10 trivectors, idx 16–25), grade-4 (5, idx 26–30), grade-5 (pseudoscalar, idx 31).

Resolved v1 assignment:
- **Projection signal `S`** → one `VisionTileSignal` at one scale; a whole image expands to tile units and never becomes a second projection artifact.
- **Position** → retained in `TileCoord`, canonical spatial order, and theta modulation; CGA translators are deferred.
- **Operators** → elliptic grade-2 rotors only; figure-ground is a saliency rotor, not a boost.
- **Ordering** → `(scale_level, morton_code(tile_row, tile_col), event_category_precedence, stable_event_id)` over a fixed canonical grid.

## 3. Consequences

### 3.1 Positive

- **Second concrete exerciser of ADR-0180**, and the first *spatial* one — it stresses the substrate's order-invariance proof against a non-temporal canonical order, which audio never exercised.
- **Order-invariance is proven, not hoped.** §2.1/§2.2 supply a concrete serialization barrier and the same content-addressed key, closing ADR-0180 §1.5.2 for the vision path.
- **No core mutation.** Everything new lives under `sensorium/vision/`, `packs/vision/`, `tests/`, `evals/`. `ingest/`, `field/`, `generate/`, `vault/`, `vocab/` are untouched (ADR-0013).
- **Substrate reuse is total.** The merge-key triple is byte-identical in shape to audio's, so `core-rs` merge/dedup, trace hygiene, and the Python arena mirror all apply without substrate changes.
- **Trace hygiene composes.** Turn traces record `(canonical_sha256, ir_sha256, projection_sha256)` and pack IDs — never raw pixels.

### 3.2 Negative / Risks

- **Embedding-bridge temptation (primary risk).** Pretrained vision encoders are so strong that reviewers will be tempted to admit one as substrate. The doctrine line must hold: substrate is the deterministic compiler; learned models are teacher/shadow lanes only.
- **Semantic underreach (v1).** The compiler captures layout, structure, orientation, and salient regions better than fine-grained object identity. Acceptable: caption/detector teachers backfill identity while the substrate stays native (mirrors audio's transcript-teacher posture).
- **Canonicalization brittleness.** Colorspace, gamma, and resampling kernel must be pinned; an unpinned resize is the vision analog of audio's unpinned FIR and will break A-1/V-1 determinism. Frozen in the pack manifest.
- **Spatial quantization regime.** Tile size, scale-pyramid depth, and orientation bins frozen in the manifest; `basis_version` is part of the merge key's pack-manifest leg, so projections stay comparable across versions or are explicitly incomparable.
- **Streaming seam artifacts (video).** Cross-frame continuity, optical-flow state, and temporal dedup are deferred to a streaming phase; **v1 is single-frame / whole-image, offline.**
- **Licensing contamination.** Any GPL/non-commercial reference detector is an oracle only, never a runtime dependency.

## 4. Execution Plan & Proof Obligations

### 4.1 PR stack (additive, doctrine-first)

| PR | Scope | Gate |
|---|---|---|
| **PR-1 (this)** | ADR-0197 + vision-compiler-spec + eval plan (docs only) | review + blade-semantics red-line (§2.6) resolved |
| **PR-2** | Deterministic substrate: `sensorium/vision/{types,canonical,checksum,resample,grid,lexer,parser,operators,compiler,trace}.py` | determinism + versor unit tests |
| **PR-3** | Pack artifacts `packs/vision/vision_core_v1/*` + `VisionProjectionHead` adapter + mount tests | mount/gate/checksum gates |
| **PR-4** | `evals/vision_sensorium/` fixtures, expected IR, expected projection hashes | full eval-gate table |
| **PR-5** | Delta-CRDT wiring: `VisionCompilationUnit` → thread-local arena → merge key, behind ADR-0180's substrate | sequential==concurrent trace-hash proof |
| **PR-6** | Teacher/shadow lanes (ViT/CLIP/DINOv2/SAM/depth) behind optional extras | teachers admitted only as typed hints |

PR-5 must not start until ADR-0180's §1.5.4 obligations (T-1…T-4) are green on `main`.

### 4.2 Vision-specific proof obligations (extend ADR-0180 §1.5.4; mirror ADR-0181 §4.2)

Each must **fail loudly** under the violation it names:

- **V-1 (determinism).** Same canonical pixels + same pack ⇒ byte-identical `(32,)`, across repeated calls, threads, and processes. Fails on any non-determinism (dict ordering, unpinned resize/colorspace, float reduction order).
- **V-2 (set-equality of merges).** A set of `VisionCompilationUnit`s folds to the same Vault state regardless of arena flush order (permutation invariance). Fails if a delta's contribution is order-sensitive at the merge layer.
- **V-3 (content-addressed key).** Trace-hash over vision deltas is invariant under set-equal Vault states when keyed by `(canonical_sha256, ir_sha256, projection_sha256)`. Fails if the reduction consumes deltas in arrival order.
- **V-4 (serialization barrier + canonical spatial order).** In-chunk `compile_events` is asserted order-sensitive (negative test): swapping two events in canonical spatial order changes the versor. **Plus the vision-specific clause:** the canonical spatial order (§2.1) is itself deterministic and stable under the pack's fixed grid — re-tiling the same canonical image yields the same event order.
- **V-5 (versor condition).** Every emitted unit satisfies `versor_condition(v) < 1e-6`; threshold never weakened to pass.
- **V-6 (trace hygiene).** No raw pixel bytes appear in any `TurnEvent`/Vault record; only the three hashes + pack IDs + optional teacher provenance.

### 4.3 The strict compilation invariant

```text
same canonical image bytes
  + same compiler version
  + same pack manifest (incl. basis_version, tile/scale/orientation regime)
  + same operator registry
  + same canonical spatial ordering rule
= same VisionIR
= same versor
= same projection hash
= same CRDT merge key
= identical post-merge Vault contribution (idempotent under re-ingest)
```

## 5. Alternatives Considered

- **Embedding-first projector (ViT / CLIP / DINOv2 as substrate).** Fast and semantically rich, but opaque; cannot be replayed bit-for-bit and cannot supply ADR-0180 §1.5.3's content-addressed key. Rejected as substrate; retained as teacher/shadow.
- **Segmentation-first (SAM as substrate).** Produces good region proposals but is non-deterministic across versions and gives no checksummable key. Rejected as substrate; useful as a teacher for region anchors.
- **Patch-token codec (VQ-GAN / image tokenizer).** Strategically interesting for a future *generation/output* lane (and a likely touch-point with the eventual MOTOR decoder work); poor first substrate for an epistemically explicit engine. Deferred to a shadow/output lane, mirroring ADR-0181's EnCodec deferral.
- **Vision as a downstream cognition mutation.** Violates ADR-0013's no-core-mutation rule and ADR-0180's "adapters never write global state directly" rule. Rejected.

## 6. Cross-References

- ADR-0013 — projection boundary; no-core-mutation constraint; Logos-recovery framing.
- ADR-0180 — Delta-CRDT substrate; §1.5.2 order-invariance (closed here for vision via §2.1), §1.5.3 content-addressed merge key, §1.5.4 T-1…T-4 (vision analogs in §4.2), §1.5.5 trace hygiene.
- ADR-0181 — Audio compiler; the structural precedent this ADR mirrors. Divergences are confined to canonical ordering (§2.1) and blade semantics (§2.6).
- ADR-0054 — Vault recall indexing/batching; the read-side contract merged vision deltas must preserve (exact CGA recall).
- CLAUDE.md §Normalization Rules — quantization/resampling confined to pack/compiler construction; `unitize_versor` algebra-owned; no hot-path repair.
- `sensorium/protocol.py`, `sensorium/registry.py` — the `ProjectionHead` / `ModalityPack` / `ModalityRegistry` contracts this ADR implements a vision instance of.

---

### Red-line resolutions

1. **§2.6 blade assignment** — v1 uses pack-local elliptic bivector aliases.
2. **§2.1 canonical spatial order** — fixed as `(scale_level, morton_code, precedence, stable_id)`.
3. **Unit granularity** — one tile-at-one-scale is the chunk and projection unit.
4. **Position encoding** — `TileCoord` + order + theta modulation in v1; CGA translators deferred.
5. **Companion specs** — `vision-compiler-spec.md` and `vision-compiler-eval-plan.md` are the implementation companions.
