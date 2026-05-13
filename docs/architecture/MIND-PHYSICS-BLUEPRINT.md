# CORE Mind-Physics Blueprint

**Version:** 0.1.0  
**Date:** 2026-05-12  
**Status:** Draft — Under Active Development

---

## The Three Physics Layers

CORE's cognitive cycle is governed by three physics layers that compose in sequence:

```
FieldState (populated by ingest layer, ADR-0007)
       │
       ▼
┌─────────────────────────────┐
│   ALLOCATION PHYSICS        │  ADR-0008
│   SalienceOperator          │  curvature → SalienceMap
│   AttentionOperator         │  SalienceMap + Budget → AttentionPlan
│   InhibitionOperator        │  AttentionPlan + FieldState → InhibitionMask
└─────────────┬───────────────┘
              │  foregrounded field regions
              ▼
┌─────────────────────────────┐
│   COMPOSITIONAL PHYSICS     │  ADR-0009
│   BindingOperator           │  co-activation → BindingFrame
│   DigestOperator            │  BindingFrame → FieldState (updated)
│   TrajectoryOperator        │  [BindingFrame] → ReasoningTrajectory
│   ArticulationPlanner       │  Trajectory + Modality → ArticulationPlan
└─────────────┬───────────────┘
              │  structured output plan
              ▼
┌─────────────────────────────┐
│   IDENTITY PHYSICS          │  ADR-0010
│   IdentityCheck             │  Trajectory × IdentityManifold → IdentityScore
│   DriveGradientMap          │  persistent gradient bias on FieldState
│   ExertionMeter             │  cumulative cost → FatigueIndex
└─────────────┬───────────────┘
              │  validated, identity-consistent ArticulationPlan
              ▼
         RENDERER
         (modality-specific surface realization)
```

---

## Data Flow Summary

| Layer | Input | Output | ADR |
|---|---|---|---|
| Ingest | raw source (any modality) | `CandidateGeometricPressure` → `FieldState` | ADR-0007 |
| Allocation | `FieldState` | `AttentionPlan`, `InhibitionMask` | ADR-0008 |
| Compositional | `AttentionPlan`, `FieldState` | `ReasoningTrajectory`, `ArticulationPlan` | ADR-0009 |
| Identity | `ReasoningTrajectory`, `ArticulationPlan` | `IdentityScore`, validated plan | ADR-0010 |
| Renderer | `ArticulationPlan` | surface output (text, code, data) | TBD |

---

## Next Steps

- [ ] Rust acceleration targets: curvature kernel, coherence wave, trajectory delta
- [ ] `IdentityManifold` bootstrapping protocol (architect-level, deliberate)
- [ ] Renderer interface definition (ADR-0011, planned)
- [ ] Integration tests across the full ingest → allocation → compositional → identity cycle
