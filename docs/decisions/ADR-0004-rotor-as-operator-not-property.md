# ADR-0004: Rotor as Operator, Not Vocabulary Property

**Date:** 2026-05-12  
**Status:** Accepted  
**Commit:** `bd423e4`  
**Implements:** ADR-0003

## Context

`VocabManifold` in the initial `core` implementation included an `edge_rotor()`
method that computed the rotor between two stored word-versors:

```python
def edge_rotor(self, from_idx: int, to_idx: int) -> np.ndarray:
    A = self._versors[from_idx]
    B = self._versors[to_idx]
    R = geometric_product(B, reverse(A))
    R[0] += 1.0
    return normalize_to_versor(R)
```

This method is mathematically correct but architecturally misplaced. Storing it
on `VocabManifold` means the vocabulary is carrying operator construction logic —
implying that the relationship between two words is a property of the vocabulary
rather than a property of a transformation being applied in the field.

## Decision

1. Remove `edge_rotor()` from `VocabManifold`.
2. Create `algebra/rotor.py` with `word_transition_rotor(A, B)` as a free function.
3. Export `word_transition_rotor` from `algebra/__init__.py`.

`VocabManifold` contract is now strictly: store word-versor pairs, support
relational lookup by CGA inner product. Nothing else.

## Rationale

A rotor between two words is not a property of those words in isolation —
it is a description of a *transformation being applied at a moment in the
field*. Storing it on the vocabulary conflates the map (what words exist and
where they are) with the territory (what operations are being performed on
the field state during generation or propagation).

Serves **Field-State**: operators live in `algebra/`; relational structure
lives in `field/`; the vocabulary is a lookup structure, not an operator store.

Serves **Dual-Correction**: the forward operator (field propagation) and its
corrective counterpart (rotor application / coherence restoration) should both
originate in `algebra/`, not be scattered across layers that don’t own them.

## Consequences

- **Cleaner dependency graph:** `vocab/` now imports from `algebra/` for
  algebraic primitives only (grade-norm check). It never constructs operators.
- **Clear callsite semantics:** `algebra.word_transition_rotor(A, B)` at a
  callsite in `field/` or `generate/` is self-documenting: *an operator is
  being constructed here, by the layer that owns operators*.
- **Forbidden:** Any method on `VocabManifold` that constructs a rotor,
  versor product, or transformation. Vocabulary is read-only geometry.

## Alternatives Considered

- **Keep `edge_rotor()` as a convenience method with a deprecation warning:**
  Rejected. Convenience methods that violate layer contracts tend to be the
  ones that get used. Remove cleanly.
- **Move to a separate `VocabOps` class in `vocab/`:** Rejected. The
  operators don’t belong in `vocab/` regardless of what class they live in.
  The layer boundary is the constraint, not the class boundary.
