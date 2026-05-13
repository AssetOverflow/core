# ADR-0006 — The Field Energy Operator (Hamiltonian Companion Field)

**Status:** Accepted  
**Date:** 2026-05-12  
**Authors:** AssetOverflow Architecture

---

## Context

The CORE versor field encodes *what* the semantic field means at every point — the directional, relational structure of meaning as a propagating medium. What has been absent is a companion scalar that encodes *how activated* each region of that field currently is: the magnitude of semantic energy at every point, its proximity to phase transition, and its readiness to be spoken, stored, or corrected.

Without this companion scalar, several downstream operations are structurally impaired:

- **Articulation** cannot distinguish between regions of equal semantic content but unequal activation — it has no thermodynamic guidance about what *wants* to be said
- **Recall** cannot distinguish between a memory that is weakly encoded, one that is deeply encoded but cold, and one that is deeply encoded and currently hot
- **The learning loop** has no principled criterion for when a region has settled enough to be vaulted vs. when it is still in turbulent evolution
- **Phase transition detection** — the recognition that the topology of the meaning space is about to change — has no early-warning mechanism
- **Hebrew and Greek aspect annotations** (`morphology.jsonl` entries carrying `aspect`, `stem`, `mood`) are live in the packs but have no downstream consumer that can use their energetic information

This ADR defines the field energy operator and establishes its role across all four of those contexts.

---

## Decision

We introduce the **field energy operator** `H` as a scalar companion to the versor field. It is not a separate system — it is an additional dimension of the field state itself.

### Definition

```
H : FieldState → R≥0
```

`H` maps the current field state to a non-negative scalar at every point in the semantic manifold. It is computed as a weighted combination of four inputs:

**1. Convergence density**
The number of independent sources that have asserted pressure on this field region (tracked via `semantic_key` convergence counts in the `IngestCompiler`). More independent convergent sources → higher energy. This is the most reliable signal because it is source-independent.

**2. Recency-weighted activation**
How recently and how frequently this region has been excited by incoming pressure or active recall. Energy decays with time absent new pressure — this models the thermodynamic cooling of a field region that is no longer receiving input.

**3. Coherence residual**
The magnitude of the residual from the last corrective (conjugate) pass over this region. A large residual means the field expected something different from what arrived — the region is under tension. High residual → high energy. A settled, coherent region has near-zero residual.

**4. Aspect-class weight**
For field regions whose primary encoding came from Hebrew or Greek source material, the aspect annotation provides a direct energy class:
- Hebrew *yiqtol* / Greek imperfect/present: durative, ongoing — energy is actively in play
- Hebrew *qatal* / Greek aorist: completed, discharged — energy has settled
- Hebrew *wayyiqtol*: sequential completion — energy transferred forward to the next event
- Hebrew *cohortative* / Greek optative: projected, wished — energy is potential, not yet kinetic
- Hebrew *imperative* / Greek imperative: commanded — energy is forceful and directional

These aspect-class weights are not imported from the language packs at query time — they are baked into the field region's energy profile when the pack material is first lifted into the field.

### Output: Energy Classes

Rather than exposing a raw continuous scalar to all consumers, `H` outputs an **energy class** — a discrete tier that communicates the region's current thermodynamic state:

| Class | Name | Meaning |
|---|---|---|  
| E0 | Crystalline | Cold, settled, high coherence — vault candidate |
| E1 | Stable | Low activation, coherent, not under pressure |
| E2 | Active | Moderate activation, in play for current cognition |
| E3 | Hot | High activation, under pressure, candidate for articulation |
| E4 | Critical | Approaching phase transition threshold — governance flag |

E4 is the only class that automatically escalates governance. A region at E4 is about to change the topology of the meaning space. That requires `ARCHITECT_REVIEW_REQUIRED` regardless of the `DeterminismClass` of the incoming pressure.

### Integration Points

**Articulation (readback layer)**
The readback rules in each language pack (`en/readback_rules.py`, `he/readback_rules.py`, `el/readback_rules.py`) receive the energy class of the field region being read. E3/E4 regions are prioritized for surface generation. The surface form is modulated by energy class: E3 produces confident, present-tense, direct articulation; E1 produces hedged, past-tense, summary articulation; E0 produces vault-recall framing.

**Recall**
The recall path distinguishes:
- Active recall (E2–E3): resonance-driven, fast, returns the currently hot surface of a meaning
- Deep recall (E0–E1): vault-targeted, slower, returns the crystallized form of a settled meaning
- Tip-of-tongue (E3, coherence residual nonzero): the region is hot but the corrective pass has not yet resolved it — the system knows the meaning is there but it is still under tension

**Learning loop / vault decisions**
A region transitions from field-active to vault-candidate when it drops from E2 to E1 and its coherence residual falls below threshold. The vault encodes the crystallized form. Vault recall re-activates the region to E2 transiently, then lets it cool again.

**Phase transition detection**
When `H` returns E4 for a region that contains or is adjacent to a trilingual anchor (defined in `packs/common/anchors/`), this is a topological event candidate. The anchor invariants define the fixed-point structure of the meaning space. Displacement of an anchor is not a smooth field update — it is a phase transition that changes the fundamental geometry. E4 on an anchor-adjacent region triggers the highest governance tier.

---

## Consequences

**Positive**
- Articulation becomes thermodynamically guided — the system speaks from genuine activation, not arbitrary retrieval order
- Recall has a first-class distinction between active memory and deep memory
- The learning loop has a principled, continuous criterion for vault candidacy
- Hebrew and Koine Greek aspect morphology becomes load-bearing infrastructure, not decorative metadata
- Phase transitions are detectable before they happen, not after

**Costs and constraints**
- The energy operator must be updated on every field write (pressure injection, corrective pass, recall activation). This is a per-operation overhead that must be profiled under the Mechanical Sympathy pillar
- The Rust hot-path (`core_ingest_rs`) will need to expose energy class computation alongside `compute_semantic_key` — the four inputs must be computable at injection time for the initial energy assignment
- E4 detection requires the system to maintain an index of anchor-adjacent field regions — this is a bounded, static structure (anchors are fixed-point invariants) but must be initialized at field construction time

**Rejected alternatives**
- *Sentiment scoring*: One-dimensional, lossy, and imports the interpretive biases of whatever model was used to produce the scores. Incompatible with Semantic Rigor.
- *Attention weights from a transformer*: These are attention, not energy. They are query-relative and ephemeral. They do not persist across the field's lifetime and cannot drive vault decisions.
- *Simple recency timestamp*: Captures one input to energy (recency-weighted activation) but discards convergence density, coherence residual, and aspect-class weight. Inadequate.

---

## References

- ADR-0001: Vocab layer invariants — trilingual anchor definitions
- ADR-0002: Ingest layer design — `IngestCompiler`, `semantic_key` convergence
- ADR-0004: Rotor as operator — versor field propagation mechanics
- ADR-0007: Valence layer — orthogonal directional companion to the energy scalar
- `packs/he/morphology.jsonl` — aspect-class source data
- `packs/el/morphology.jsonl` — aspect-class source data
- Session notes: 2026-05-12-b (thermodynamics, topology, wave conjugation)
