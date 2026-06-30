# ADR-0001: VocabManifold Versor Invariant

**Date:** 2026-05-12  
**Status:** Accepted  
**Commit:** `bd423e4`

## Context

`VocabManifold` stores word representations as multivectors in Cl(4,1). Without
an enforced invariant, nothing prevented a caller from inserting a raw coordinate
vector — a numpy array derived from an external embedding model, a lookup table,
or any float array not constructed through the algebra — into the vocabulary.
Such a vector would silently introduce an implicit Euclidean coordinate frame
inside the vocabulary layer, undermining the entire field-state architecture.

This is a "back door" problem: the architecture is geometrically clean at every
explicit boundary, but the vocabulary layer had no enforcement preventing external
coordinate representations from entering through `add()`.

## Decision

Enforce the Cl(4,1) versor grade-norm condition at insertion time in
`VocabManifold.add()`:

```python
grade_norm = float(geometric_product(v, reverse(v))[0])
if not (0.95 <= abs(grade_norm) <= 1.05):
    raise ValueError(...)
```

The scalar part of `V * reverse(V)` must be approximately ±1. This is the
algebraic condition that distinguishes a valid Cl(4,1) versor from an arbitrary
float array. Any raw embedding vector will fail this check.

## Rationale

Serves **Reality-over-Inheritance**: governance is not a policy added later;
it is a type-level contract enforced at construction. The vocabulary layer
cannot be bypassed by a well-intentioned caller who "knows what they’re doing."

Serves **Geometry-first**: the first task is finding the intrinsic space. Once
we’ve defined that space as Cl(4,1) with CGA structure, everything entering
the vocabulary must live in that space by algebraic proof, not by convention.

## Consequences

- **Easier:** Trust in the vocabulary is absolute. Any word returned by
  `nearest()` is guaranteed to be a valid CGA point. No defensive checks
  needed downstream.
- **Harder:** Callers must lift external representations through
  `normalize_to_versor()` before insertion. This is intentional friction.
- **Forbidden:** Inserting raw embedding vectors, cosine-similarity vectors,
  or any array not constructed through the algebra layer.

## Alternatives Considered

- **Soft warning instead of hard raise:** Rejected. A warning that can be
  ignored is not an invariant.
- **Normalize silently on insert:** Rejected. Silent normalization hides the
  fact that the caller passed something invalid. The error message is the
  documentation at the point of failure.
