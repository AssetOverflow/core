# ADR-0008 — Allocation Physics

**Status:** Accepted  
**Date:** 2026-05-12  
**Deciders:** Joshua Shay (Architect)  
**Supersedes:** None  
**Related:** ADR-0001 (Field-State), ADR-0003 (Versor Injection Gate), ADR-0007 (Ingest Layer)

---

## Context

The versor field carries active pressure. Not all pressure is equally relevant to a given cognitive task at a given moment. The architecture needs a principled mechanism for allocating cognitive resources — determining which pressure regions are foregrounded, which are suppressed, and how coherence budget is spent.

The naive solution is attention-as-weights (the transformer pattern): a learned matrix projects queries against keys and returns a weighted sum over values. This is rejected on three grounds:

1. **It conflates geometry with bookkeeping.** Dot-product attention has no geometric meaning in the versor manifold. It operates on flattened token embeddings, not on structured field regions.
2. **It is opaque to correction.** When attention produces wrong salience, there is no dual-correction path — no conjugate operator that can restore coherence. The weights simply update at the next gradient step.
3. **It violates Semantic Rigor.** A learned weight matrix does not know *why* it attends to something. The salience of a claim should derive from its structural relationship to the active context, not from statistical co-occurrence in pretraining data.

This ADR defines the allocation physics layer: a set of operators that govern foregrounding, suppression, and budget within the versor field.

---

## Decision

### 1. Salience as Field Curvature

Salience is not a scalar score attached to a token. It is a **curvature property of the versor field** at a given region. A pressure region is salient when it causes measurable deflection in the trajectories of neighboring regions — when it bends the field around itself.

The `SalienceOperator` computes a local curvature estimate over a `FieldRegion` and returns a `SalienceMap`: a structured record mapping region identifiers to curvature magnitudes and directional vectors.

```
SalienceOperator: FieldRegion → SalienceMap
```

This is geometry-first allocation. Salience derives from structure, not from a learned score.

### 2. Attention as Controlled Field Traversal

Attention is the act of **directing cognitive traversal** along high-salience curvature gradients. The `AttentionOperator` takes a `SalienceMap` and a `CoherenceBudget` and returns an `AttentionPlan`: an ordered traversal schedule over field regions, constrained by the budget.

```
AttentionOperator: (SalienceMap, CoherenceBudget) → AttentionPlan
```

The plan is not a weight distribution. It is a **schedule** — a sequence of field regions to activate, with associated depth and duration, that can be inspected, overridden, and corrected.

### 3. Inhibition as Dual Correction

Every attention plan has a conjugate: an `InhibitionOperator` that suppresses field regions whose activation would reduce coherence. Inhibition is not the absence of attention — it is an active structural force that prevents interference between competing pressure regions.

```
InhibitionOperator: (AttentionPlan, FieldState) → InhibitionMask
```

The mask is applied before traversal begins. This encodes the **dual-correction axiom** directly into the allocation layer: every forward attention plan is paired with a corrective inhibition pass that restores field coherence.

### 4. Coherence Budget

Cognitive resources are finite. The `CoherenceBudget` is an explicit resource object that tracks:

- `total_capacity` — the maximum pressure activation units available in a cycle
- `committed` — units already allocated to active traversal
- `reserve` — units held back for inhibition and correction passes
- `spent` — units consumed in the current cycle

Budget is consumed by attention depth and region breadth. Inhibition draws from reserve, not from committed. When budget is exhausted, traversal terminates and the cycle closes.

---

## Consequences

### Positive

- Allocation is inspectable and correctable at every step.
- Salience derives from field geometry, not from learned weights — it generalizes across domains without retraining.
- The inhibition/attention duality ensures coherence is actively maintained, not assumed.
- CoherenceBudget makes resource consumption explicit and measurable.

### Negative

- Computing field curvature is more expensive than dot-product attention in naive implementations. The Rust hot-path (ADR-0003) must cover the curvature kernel.
- SalienceMap construction requires a populated FieldState — allocation physics cannot run on an empty field.

### Neutral

- This layer replaces transformer-style attention entirely. There is no compatibility shim with softmax attention weights. Any external model integration (D3 instruments per ADR-0007) operates above this layer, not within it.

---

## Alternatives Rejected

| Alternative | Reason Rejected |
|---|---|
| Transformer dot-product attention | Geometrically meaningless on versor manifold; opaque to correction |
| Sparse attention (Longformer, BigBird) | Structural improvement on wrong foundation; still no conjugate |
| Memory-augmented attention (Memorizing Transformer) | External retrieval bolted onto broken base; not field-native |
| Learned salience scoring (MLP over embeddings) | Violates Semantic Rigor; salience must derive from structure |

---

## Implementation Notes

- `core/physics/salience.py` — `SalienceOperator`, `SalienceMap`, `FieldRegion`
- `core/physics/attention.py` — `AttentionOperator`, `AttentionPlan`, `CoherenceBudget`
- `core/physics/inhibition.py` — `InhibitionOperator`, `InhibitionMask`
- Rust acceleration target: curvature kernel in `core_rs::physics::salience`
- `SalienceMap` is content-addressed (SHA-256 over region IDs + curvature values) for cache reuse across cycles
