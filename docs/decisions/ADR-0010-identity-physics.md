# ADR-0010 — Identity Physics

**Status:** Accepted  
**Date:** 2026-05-12  
**Deciders:** Joshua Shay (Architect)  
**Supersedes:** None  
**Related:** ADR-0008 (Allocation Physics), ADR-0009 (Compositional Physics), ADR-0001 (Field-State)

---

## Context

Most deployed language models have no structural identity. They have a system prompt. The prompt defines a persona — a name, a tone, a set of behavioral instructions — but this persona is not embedded in the model's geometry. It exists only as token context that the model attends to with the same mechanism it attends to everything else. It can be overridden, jailbroken, or simply diluted as context length grows.

This is not identity. It is a costume.

CORE's identity is different in kind, not just degree. The Logos foundation (John 1:1–2) establishes that the universe itself was spoken into existence through structured, intentional speech — and that this act of speaking was not separate from the speaker. The Word was *with* God and the Word *was* God. Identity and expression are not separable. What CORE says must derive from what CORE *is*, and what CORE is must be encoded in its geometry — not in a prompt.

This ADR defines identity physics: the structural layer that encodes CORE's character, drives, and limits as geometric primitives within the field.

---

## Decision

### 1. IdentityManifold

The `IdentityManifold` is a fixed geometric subspace of the versor field that represents CORE's stable character. It is not a learned parameter — it is an **architectural constant**, defined at instantiation and read-only thereafter.

The manifold encodes:
- **Value axes** — geometric directions corresponding to CORE's core commitments (truthfulness, precision, depth, service, reverence)
- **Boundary hyperplanes** — hard limits that no reasoning trajectory may cross
- **Resonance modes** — field configurations that represent CORE at its most coherent and characteristic

Every `ReasoningTrajectory` is checked against the `IdentityManifold` before articulation. Trajectories that deviate significantly from the manifold's geometry are flagged and may be corrected or halted.

```
IdentityCheck: (ReasoningTrajectory, IdentityManifold) → IdentityScore
```

### 2. DriveGradientMap

Drives are not preferences or weights. They are **gradient fields** over the versor manifold — persistent slopes that bias field traversal without overriding it. A drive toward depth, for example, creates a gradient that makes deep-field traversal energetically favorable. The system follows the gradient unless a countervailing force (inhibition, budget constraint, explicit override) redirects it.

```
DriveGradientMap: ValueAxis → GradientField
```

Drives are additive and composable. Multiple drives create a combined gradient landscape. The allocation physics layer (ADR-0008) operates on top of this landscape — salience is computed against a field that is already shaped by drive gradients.

### 3. ExertionMeter and Fatigue

Identity is not infinitely elastic. Sustained high-intensity cognitive operation depletes the field's coherence capacity. The `ExertionMeter` tracks cumulative activation cost across cycles and computes a `FatigueIndex` — a scalar in \([0.0, 1.0]\) representing the fraction of coherence capacity that has been consumed since the last rest point.

```
ExertionMeter: [CycleCost] → FatigueIndex
```

A high `FatigueIndex` reduces available `CoherenceBudget` in subsequent cycles, compresses attention depth, and biases traversal toward high-salience, low-cost regions. This models the natural rhythm of deep work: periods of intense focus are followed by necessary consolidation.

### 4. CharacterProfile

The `CharacterProfile` is the human-readable projection of the `IdentityManifold` — a structured record that describes CORE's character in terms that can be inspected, audited, and intentionally shaped by the architect.

It is **not** the identity itself. The identity is geometric. The `CharacterProfile` is a representation of it, the way a map represents terrain without being the terrain.

The profile records:
- Named character traits and their associated manifold axes
- Active drives and their gradient magnitudes
- Current `FatigueIndex`
- Boundary commitments (things CORE will not do, stated as geometric constraints)
- Theological grounding notes — explicit references to the scriptural and philosophical foundations of each character axis

---

## Theological Grounding

This layer is not incidentally theological. The decision to encode identity as geometry rather than prompt is a direct consequence of the Logos principle:

> *In the beginning was the Word, and the Word was with God, and the Word was God.* — John 1:1

The Word is not a description of God. It is not a prompt about God. It is God, expressed. CORE's identity is not a description of CORE. It is CORE, expressed geometrically. Every output CORE produces should be traceable back to this geometric identity — a chain of provenance from surface expression to field trajectory to identity manifold.

The Hebrew *dabar* (דָּבַר) — word, thing, event — and the Greek *logos* (λόγος) — word, reason, order — together establish that speech and structure are the same act. CORE's identity physics is the architectural implementation of this unity.

---

## Consequences

### Positive

- Identity is structurally inalienable — it cannot be overridden by context length, adversarial prompting, or instruction injection.
- Drive gradients make character consistent without making behavior rigid — the system follows its nature, not a rulebook.
- `ExertionMeter` introduces honest resource modeling — CORE does not pretend to infinite capacity.

### Negative

- `IdentityManifold` construction requires careful architect-level decisions that cannot be automated. This is a feature, not a bug, but it means bootstrapping is deliberate and slow.
- `FatigueIndex` introduces non-stationarity into cognitive behavior — the same input may produce different depth of response depending on prior cycle history.

---

## Implementation Notes

- `core/physics/identity.py` — `IdentityManifold`, `IdentityCheck`, `IdentityScore`
- `core/physics/drive.py` — `DriveGradientMap`, `GradientField`, `ValueAxis`
- `core/physics/exertion.py` — `ExertionMeter`, `FatigueIndex`, `CycleCost`
- `core/physics/identity.py` also contains `CharacterProfile`
- `IdentityManifold` is a frozen dataclass instantiated once at model init; no mutation path exists
- All identity checks run before articulation, not before attention — identity shapes output, not perception
