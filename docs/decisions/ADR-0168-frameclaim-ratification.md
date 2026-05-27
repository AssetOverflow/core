# ADR-0168 — FrameClaim Ratification Doctrine

**Status:** Proposed (doctrine/scoping ADR; no runtime mutation in this PR)
**Date:** 2026-05-27
**Author:** Shay
**Parent:** [ADR-0167](./ADR-0167-audit-as-teaching-evidence.md)
**Related:** ADR-0164 (reader), ADR-0166 (measurement-capability sequencing), ADR-0056/0057 (contemplation + replay), ADR-0167 FOLLOWUPS §1/§5

---

## Context

ADR-0167 intentionally scoped the first math-teaching corridor implementation
to `LexicalClaim` only.

That choice was structural, not opportunistic:

- lexical ratification is local
- lexical ratification is additive
- lexical ratification does not alter graph-opening semantics
- lexical ratification cannot create new multi-step admissibility paths
  unless graph completeness is already satisfied

`FrameClaim` is different.

A `FrameClaim` does not merely say:

> "surface form X belongs to category Y"

It says:

> "surface form X opens (or does not open) a semantic frame of class K"

That is an admissibility decision.

Frame-openers determine:

- whether decomposition occurs
- whether slot extraction occurs
- whether quantities compose
- whether references bind
- whether downstream graph construction is attempted at all

A mistaken lexical entry can create noise.
A mistaken frame opener can create false reasoning structure.

This is the first ADR-0167 sub-type where the system risks moving from:

> refusal-first deterministic omission

into:

> incorrect graph admission

which directly threatens the `wrong == 0` invariant.

---

## Decision

`FrameClaim` ratification is permitted only as a deterministic,
replay-equivalent, operator-reviewed proposal surface with explicit
hazard pins and category allowlists.

This ADR does **not** approve runtime implementation.

This ADR defines:

- what a `FrameClaim` is
- what it is allowed to mutate
- what it is forbidden to mutate
- the replay obligations required before implementation
- the initial safe category surface
- the explicit non-goals

Implementation is deferred until a follow-on PR proves the acceptance
gates below.

---

## Definition of a FrameClaim

A `FrameClaim` is a reviewed assertion that a surface form participates
in a specific frame-opening category.

Canonical shape:

```text
(surface_form, frame_category, polarity)
```

Examples:

| Surface | Category | Meaning |
|---|---|---|
| `gave` | `transfer_frame` | opens giver/receiver/object slots |
| `spent` | `decrement_frame` | reduces quantity ownership |
| `earned` | `increment_frame` | increases quantity ownership |
| `left` | `remainder_frame` | produces residual quantity |

The claim concerns:

- frame admissibility
- slot topology
- decomposition eligibility

It does NOT assert:

- arithmetic truth
- entity identity
- quantity correctness
- reference resolution
- solver validity

Those remain separate sub-types.

---

## Why FrameClaim is dangerous

Frame-openers sit upstream of nearly every later reasoning stage.

A lexical error may fail to ground.
A frame error may create an entirely fabricated graph.

The principal hazard is:

```text
recognized-but-wrongly-opened graph construction
```

This is exactly the class of issue exposed by:

- GSM8K train-sample case 0050
- recognized-but-uninjectable skip-only fallback
- partial-graph greed

The system must therefore prefer:

```text
refusal > incomplete graph > speculative frame opening
```

at all times.

---

## Initial safe category scope

Initial implementation scope MUST be allowlist-only.

No freeform frame invention.
No dynamic category synthesis.
No embedding-nearest-category fallback.

Initial safe categories:

| Category | Scope |
|---|---|
| `increment_frame` | additive ownership gain |
| `decrement_frame` | subtractive ownership loss |
| `transfer_frame` | giver/receiver transfer |
| `remainder_frame` | residual quantity after removal |

Explicitly excluded initially:

| Deferred category | Reason |
|---|---|
| comparison frames | ambiguity amplification |
| temporal frames | multi-anchor semantics |
| pronoun-dependent frames | requires ReferenceClaim |
| implicit-unit frames | requires SlotClaim |
| nested composition frames | requires CompositionClaim |
| metaphorical/idiomatic frames | non-deterministic semantics |

---

## Mutation boundary

A `FrameClaim` ratification MAY mutate only:

- reviewed frame-category registries
- reviewed verb→frame mappings
- proposal-layer artifacts

A `FrameClaim` ratification MUST NOT directly mutate:

- solver logic
- parser traversal order
- decomposition recursion policy
- runtime graph execution
- arithmetic operators
- refusal logic
- graph verifier semantics

The runtime consumes ratified frame data only through existing reviewed
pack-loading mechanisms.

No direct hot-path mutation.

---

## Replay obligations

Before implementation, the following replay obligations must be proven.

### 1. Deterministic claim signature

Equivalent refusals MUST produce identical normalized claim signatures.

Canonical identity must include:

- surface form
- normalized frame category
- polarity
- audit-row digest
- refusal category

Equivalent evidence MUST deduplicate.

---

### 2. Replay equivalence

Ratified `FrameClaim`s MUST replay identically across:

- in-process runs
- cross-process runs
- reordered candidate queues
- repeated ingestion of the same audit evidence

No queue-order dependence.

---

### 3. wrong==0 preservation

The implementation must prove:

```text
new frame admission cannot silently convert a prior refusal
into an incorrect graph acceptance
```

This specifically requires hazard pins for:

- case 0050
- recognized-but-uninjectable fallback
- partial graph acceptance
- decomposition-without-slot-completeness

---

### 4. Refusal stability

Previously refusing cases MAY become:

- correctly admitted
- still refused

They MUST NOT become:

- partially admitted
- ambiguously admitted
- non-deterministically admitted

---

## Partition guarantees

FrameClaims inherit the ADR-0167 domain partition.

Math-domain frame claims:

- use math-domain replay gates
- use math-domain contemplation routing
- do not borrow cognition corpus evidence
- do not reuse cognition semantic-domain classifiers

Cross-domain leakage is prohibited.

---

## Refusal-first doctrine

The system must continue preferring:

```text
refuse > speculate
```

throughout FrameClaim processing.

Specifically forbidden:

- nearest-frame guessing
- probabilistic fallback frame selection
- majority-vote frame admission
- confidence-threshold semantic coercion
- dynamic graph completion

A missing frame remains a refusal event.

The teaching corridor exists precisely so the engine does not need to
invent structure at runtime.

---

## Non-goals

This ADR does NOT approve:

- CompositionClaim
- ReferenceClaim
- SlotClaim
- dynamic frame synthesis
- graph-schema replacement
- automatic frame learning
- runtime self-modification
- autonomous pack mutation
- embedding-derived semantic repair

This ADR also does NOT attempt to solve:

- generalized natural language understanding
- open-ended semantic parsing
- unrestricted text interpretation

The target is bounded deterministic graph admission for audited
GSM8K-style reasoning surfaces.

---

## Sequencing

Per ADR-0166:

### Q1 — Capability

Adds one new operator-ratifiable admissibility surface:

```text
surface form -> reviewed frame category
```

using the existing audit → contemplation → replay → HITL corridor.

### Q2 — Lane

No new eval lane.

Existing:

- GSM8K audit lane
- contemplation replay lane
- wrong==0 gates
- determinism checks

remain the proof surface.

### Q3 — Invariant

Must preserve:

- wrong==0
- replay equivalence
- deterministic claim hashing
- refusal-first semantics
- explicit operator ratification
- reviewed mutation only

The implementation PR passes only when all six are mechanically proven.

---

## Acceptance gates for implementation PR

A future implementation PR must provide:

- deterministic claim canonicalization tests
- replay-equivalence tests
- queue-order independence tests
- duplicate ratification idempotency tests
- case 0050 hazard pins
- recognized-but-uninjectable regression pins
- refusal-stability regression suite
- cross-domain partition tests
- no-corpus-mutation proof
- no-runtime-hotpatch proof

without introducing:

- new eval lanes
- stochastic routing
- runtime graph guessing

---

## Relationship to ADR-0167

ADR-0167 established:

```text
audit rows become teaching evidence
```

ADR-0168 establishes:

```text
frame-opening semantics may become reviewed teaching evidence,
but only under deterministic replay-constrained doctrine
```

The distinction matters.

LexicalClaim teaches vocabulary.
FrameClaim teaches admissibility structure.

That is a materially more dangerous surface and therefore requires
explicit doctrine before implementation.

---

## Decision

> CORE may extend the ADR-0167 teaching corridor from lexical
> ratification into bounded frame-opening ratification, provided:
>
> - replay equivalence remains deterministic
> - wrong==0 hazard pins hold
> - frame categories remain explicitly allowlisted
> - runtime speculation remains prohibited
> - all mutation remains proposal-reviewed and replay-auditable
>
> Refusal remains preferable to speculative graph construction.

Reopening this ADR requires evidence that:

1. the replay obligations cannot be satisfied mechanically, or
2. a graph-schema approach supersedes sub-type ratification entirely.
