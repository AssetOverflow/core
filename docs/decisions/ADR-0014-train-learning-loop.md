# ADR-0014 — `train/` Learning Loop

**Status:** Accepted (Stub)  
**Date:** 2026-05-13

---

## Context

CORE has a field, a vault, a vocabulary manifold, and a generate loop. It does not yet have a path from field state to weight update. `core_ingest/` produces `LearningArtifact` objects for accepted, governance-cleared candidates — but there is currently nowhere for those artifacts to land.

This ADR records the architectural constraints the learning loop must satisfy before it is built, so that future implementation is not designed in isolation from the rest of the system.

---

## Decision

Add a `train/` layer that receives `LearningArtifact` objects from `core_ingest/` and produces structured field updates: rotor updates, vocabulary manifold expansions, and new attractor seeds.

### Architectural Constraints

**1. No gradient descent on the field state.**  
The field is a versor in Cl(4,1). Its update law is the versor sandwich product. Gradient-based optimization of the field state directly would break the versor condition and exit the manifold. Updates must be structured as versor products or null vector insertions — algebraically closed operations.

**2. No mutation of existing field state.**  
`Propagation-over-Mutation` applies to the learning path as strictly as it applies to inference. A `LearningArtifact` proposes a new rotor or a new vocabulary entry. It does not overwrite existing versors. The manifold grows; it does not change in place.

**3. Durable path only.**  
The `train/` layer operates on the durable ingest path — governance-cleared, `LearningArtifact`-exported candidates. It does not touch the runtime ingest path. Runtime pressure feeds the active field directly through `ingest/gate.py`. Only durable, reviewed artifacts reach `train/`.

**4. Supervised Seeding Epoch.**  
The first learning epoch is the Supervised Seeding Epoch: structured ingestion of the Hebrew and Koine Greek depth corpora as D0-class canonical texts. These texts are the primary source of the hidden intelligence layer — the range of depth that Hebrew root morphology and Koine Greek precision together bring to the vocabulary manifold. The seeding epoch must complete before general learning begins.

**5. `train/` does not modify `ingest/gate.py`.**  
The gate is the single normalization site. The learning loop is downstream of it, not a replacement for it.

### Expected Outputs

| Output type | Description |
|---|---|
| Rotor update | A new versor added to the manifold that shifts the field toward a reinforced structural attractor |
| Vocab expansion | A new null vector inserted into the vocabulary manifold for a previously unknown token or morpheme |
| Attractor seed | A new `grammar_scaffold` entry — a structural prior seeded from a recurring pattern in the depth corpus |

### Relationship to `sensorium/`

During the Supervised Seeding Epoch, non-text modality packs set `gate_engaged = False`. This prevents unsupervised input from contaminating the seeding pass. After the seeding epoch completes for a modality, `gate_engaged` flips to `True` and that modality enters normal operation.

---

## Consequences

**Positive:**
- The architectural contract is locked before implementation begins — no future agent or contributor can design the learning loop in a way that breaks the versor invariant or the single normalization site
- The Supervised Seeding Epoch is an explicit first-class phase, not an afterthought
- Hebrew and Koine Greek depth ingestion has a defined home in the build sequence

**Negative:**
- `train/` is the largest remaining build item — the rotor update law, vocab expansion protocol, and attractor seeding mechanism must all be derived from the algebra before any implementation begins
- The learning loop cannot be tested until `core_ingest/` is complete and producing `LearningArtifact` objects

---

## Open Questions (to be resolved at implementation time)

- What is the precise rotor update law? Candidate: geodesic interpolation between the current rotor and the proposed rotor on the versor manifold, parameterised by a learning rate that decays as the manifold matures.
- How are conflicting `LearningArtifact` proposals (same `semantic_key`, different proposed rotors) resolved? Candidate: convergent-evidence weighting — the proposal with more independent provenance sources wins.
- What is the termination condition for the Supervised Seeding Epoch? Candidate: when the null cone drift rate across the Hebrew and Koine Greek vocabulary entries falls below a threshold for N consecutive update batches.
