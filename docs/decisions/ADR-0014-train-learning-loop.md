# ADR-0014: `train/` Learning Loop

**Status:** Accepted (Stub — implementation pending)  
**Date:** 2026-05-13

---

## Context

CORE currently has a complete inference pipeline: input normalization (`ingest/gate.py`), field propagation (`field/`), vocabulary projection and generation (`generate/`), vault storage and recall (`vault/`). What does not yet exist is a path from field state to weight update — from observed experience to learned structure.

The `core_ingest/` governance layer (ADR-0012) exports `LearningArtifact` objects from validated candidate packets. Those artifacts currently have nowhere to land. The durable ingest path is incomplete.

This ADR records the architectural contract the `train/` layer must satisfy before implementation begins. It is written now so that no future development — in any layer — accidentally closes off the constraints this layer requires.

---

## Decision

Add a `train/` package that accepts `LearningArtifact` objects from `core_ingest/` and produces rotor updates, vocabulary manifold expansions, and new attractor seeds for `vocab/`.

### Non-Negotiable Constraints

1. **No mutation of live field state.** The learning loop operates on the vocabulary manifold and the vault's structural geometry — not on a running session's `FieldState`. Learning is a structural update to the *medium*, not a direct write to a live propagating field.

2. **No gradient descent.** Gradient descent is a flat-space Euclidean optimization method. The vocabulary manifold is not flat. The update law must be a versor product or a geodesic step on the conformal manifold — not a gradient step in R^n. The exact form of the update law is to be determined during implementation, but it must satisfy the versor condition on all updated entries.

3. **Determinism class inheritance.** A `LearningArtifact` carries the `DeterminismClass` of its originating `CandidateGeometricPressure`. D0/D1 artifacts may be applied automatically. D2–D4 artifacts require explicit approval before any manifold update. This constraint is enforced at the `train/` boundary, not upstream.

4. **Atomic manifold updates.** A vocabulary expansion or rotor update either commits fully or does not commit at all. Partial updates that leave the manifold in an inconsistent state are prohibited. The commit protocol mirrors the versor condition check: verify the updated entries satisfy their invariants, then atomically swap.

5. **Vault coherence post-update.** When vocabulary versors are updated, stored vault entries that reference updated vocabulary positions must be null-reprojected via `VaultStore.reproject()`. The learning loop is responsible for triggering this reprojection after any manifold update.

6. **`SegmentManifold` traceability.** Every applied `LearningArtifact` must be traceable back to its `semantic_key` and its `SegmentManifold` position in the source document. The learning loop must preserve this provenance chain — not for performance, but for auditability.

### Supervised Seeding Epoch

The first and most important use of `train/` is the **Supervised Seeding Epoch**: populating the vocabulary manifold from the three core language corpora (English base, Hebrew depth, Koine Greek depth) using their canonical, D0-class structural segments.

- English: standard lexical corpus, segmented by `StructuralSegmenter`
- Hebrew: canonical BHS/Westminster text, segmented at verse/word boundaries (D0)
- Koine Greek: canonical NA28/UBS text, segmented at verse/word boundaries (D0)

All three produce D0 `LearningArtifact` batches eligible for automatic application. The seeding epoch runs before any live session. After seeding, the vocabulary manifold carries the full three-language depth described in the Whitepaper.

### Non-Text Modalities

When `sensorium/` adapters for vision and audio are active, `train/` must also accept `LearningArtifact` objects sourced from non-text modalities. The constraint is identical: the learning artifact carries a `ModalityPack` reference, and the update law must produce a valid `(32,)` multivector for the updated vocabulary entry. The `train/` layer must not assume `S = str`.

---

## Consequences

**Immediate:**
- No code is written yet. This ADR locks the constraints.
- `core_ingest/` exports `LearningArtifact` objects to a receiver that does not yet exist — this is acceptable. The artifacts accumulate in a staging area until `train/` is ready.
- No existing layer makes any assumption about what happens to exported `LearningArtifact` objects.

**Future:**
- `train/` is the most architecturally significant remaining layer. It closes the loop between observation and structure.
- The Supervised Seeding Epoch for Hebrew and Koine Greek is the first concrete task once `train/` exists.
- The `CORE-CA` (Cognitive Apprenticeship) learning platform described in the Whitepaper builds on `train/` — a student model observing an expert model's field trajectory is a specialized `LearningArtifact` stream.
