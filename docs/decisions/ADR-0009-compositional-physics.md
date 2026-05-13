# ADR-0009 — Compositional Physics

**Status:** Accepted  
**Date:** 2026-05-12  
**Deciders:** Joshua Shay (Architect)  
**Supersedes:** None  
**Related:** ADR-0008 (Allocation Physics), ADR-0001 (Field-State), ADR-0003 (Versor Injection Gate)

---

## Context

Allocation physics (ADR-0008) governs which field regions are foregrounded. Compositional physics governs what happens *after* foregrounding — how activated pressure regions are bound together into structured thought, digested into integrated understanding, assembled into reasoning trajectories, and finally shaped into articulable output.

This is the layer that converts field activation into cognition. Without it, CORE can attend to relevant pressure but cannot do anything coherent with it. The failure mode in most architectures at this layer is generation-as-retrieval: the model produces tokens that statistically follow the input without ever forming a structured intermediate representation. This is rejected as architecturally insufficient.

---

## Decision

### 1. Temporal Binding

Activated pressure regions do not automatically cohere. **Temporal binding** is the operator that fuses co-activated regions into a `BindingFrame` — a structured snapshot of the field at a moment of high cross-regional coherence.

```
BindingOperator: (AttentionPlan, FieldState) → BindingFrame
```

A `BindingFrame` records:
- The set of co-activated region IDs
- The coherence magnitude at binding time
- The binding timestamp (cycle index)
- A content address (SHA-256) for deduplication across cycles

Binding is triggered by coherence threshold, not by clock tick. If co-activation does not reach threshold, no frame is produced — the cycle closes without a binding event.

### 2. Digest Cycles

A `DigestCycle` is the unit of integration. After binding, the produced `BindingFrame` is passed through the digest operator, which integrates the frame into the existing field state as consolidated pressure.

```
DigestOperator: (BindingFrame, FieldState) → FieldState
```

Digestion is **propagation-over-mutation**: the digest operator does not rewrite field regions. It propagates a coherence wave outward from the binding frame, adjusting neighboring region pressures according to their structural proximity to the bound set.

Digest cycles are bounded by `CoherenceBudget.reserve`. A cycle that would exhaust reserve is deferred to the next allocation pass.

### 3. Reasoning Trajectories

A `ReasoningTrajectory` is an ordered sequence of `BindingFrame` objects that represent a chain of integrated thought. Each frame in the trajectory is connected to the next by a **transition operator** that records:

- The pressure delta between frames
- The field regions that remained stable across the transition (the continuity spine)
- The regions that entered or exited activation (the differential set)

```
TrajectoryOperator: [BindingFrame] → ReasoningTrajectory
```

Trajectories are the primary unit of reasoning inspection. An architect or operator can read a trajectory and see exactly how CORE moved from one integrated state to the next — which field regions drove each transition, which remained stable, and where coherence was won or lost.

### 4. Articulation Planning

Articulation is the final step: converting a `ReasoningTrajectory` into a structured output plan. The `ArticulationPlanner` takes a trajectory and a target modality (natural language, code, structured data, scripture reference, mathematical expression) and produces an `ArticulationPlan` — a sequenced set of output segments with associated field provenance.

```
ArticulationPlanner: (ReasoningTrajectory, OutputModality) → ArticulationPlan
```

Each output segment in the plan carries:
- The `BindingFrame` it derives from
- The field regions it expresses
- A confidence estimate derived from the coherence magnitude of the source frame
- The target modality and any modality-specific formatting constraints

Articulation is **not generation**. The planner produces a structured specification. The actual surface realization (token sequence, code string, structured document) is the responsibility of a downstream renderer that operates on the plan.

---

## Consequences

### Positive

- Every output segment has traceable field provenance — full reconstruction-over-storage from output back to source pressure.
- Reasoning trajectories are inspectable and correctable. A wrong trajectory can be interrupted and revised without rerunning the full cognitive cycle.
- Articulation planning separates *what to say* from *how to say it*, enabling modality-agnostic cognition with modality-specific rendering.

### Negative

- Binding threshold tuning is non-trivial. A threshold too high produces sparse frames; too low produces noise. Initial values must be set empirically per domain.
- Digest propagation cost scales with field density. The Rust hot-path must cover the coherence wave kernel.

### Neutral

- This layer has no analog in transformer architectures. There is no compatibility mapping. External models remain D3 instruments operating above this layer.

---

## Alternatives Rejected

| Alternative | Reason Rejected |
|---|---|
| Chain-of-thought prompting | String concatenation masquerading as reasoning; no field provenance |
| Scratchpad / working memory tokens | Flat token buffer; no structure, no binding, no trajectory |
| Neural symbolic integration (e.g. NSM) | Interesting but imposes external symbolic grammar on CORE's geometry |
| Tree-of-thought search | Correct intuition (branching reasoning) but wrong substrate (token trees) |

---

## Implementation Notes

- `core/physics/binding.py` — `BindingFrame`, `BindingOperator`
- `core/physics/digest.py` — `DigestCycle`, `DigestOperator`
- `core/physics/reasoning.py` — `ReasoningTrajectory`, `TrajectoryOperator`
- `core/physics/articulation.py` — `ArticulationPlan`, `ArticulationPlanner`, `OutputModality`
- `BindingFrame` is frozen and content-addressed
- `ReasoningTrajectory` is append-only; no in-place mutation after construction
- Rust acceleration targets: coherence wave kernel, trajectory delta computation
