# ADR-0003: Coordinate System Dissolution

**Date:** 2026-05-12  
**Status:** Accepted

## Context

The predecessor system (`core-ai`, `core_logos/rotor_vocabulary.py`) represented
vocabulary using **dual rotors in Geometric Algebra** as an explicit coordinate
system. Every word lived at a position defined by its rotor, and semantic
transformations were computed as rotor compositions. This was an advancement
over transformer embeddings but carried a hidden load: the rotor frame itself
became a load-bearing architectural concern that every downstream component
had to be aware of.

The transition to `AssetOverflow/core` raised the question: does the new design
still require an explicit coordinate system?

## Decision

The new architecture **dissolves the need for an explicit coordinate system**
through the field-state model, not by finding a better coordinate system.

Words are stored as **versors in Cl(4,1)** in `VocabManifold`. But meaning is
not a position in a versor-defined frame — it is a **pressure pattern across
a relational field**. The `FieldState` produced by `field/gate.py` is a
distribution, not a point. Lookup uses CGA inner product (relational), not
distance in a coordinate frame (positional).

Rotors still exist as operators in `algebra/rotor.py`, but they are
**transformations applied to field states**, not the frame that defines where
things are.

## Rationale

The distinction is:

| Old model | New model |
|---|---|
| Meaning = position in rotor frame | Meaning = pressure pattern in field |
| Coordinate system is load-bearing | No coordinate frame; algebra provides operators |
| Downstream must know the frame | Downstream sees only field state + CGA inner product |
| Rotor composition defines relationships | Propagation through field defines relationships |

Serves **Field-State**: the native form of state is a field over a space, not
a heap of positioned objects.

Serves **Geometry-first**: the intrinsic space is Cl(4,1) with CGA metric.
The geometry is *algebraic*, not *coordinatized*. CGA inner product is the
natural proximity measure — no cosine, no Euclidean distance, no frame.

Serves **Compilation-Last**: rotors are implementation targets chosen after the
representation is defined, not the frame the representation is built on.

## Consequences

- **Easier:** No component outside `algebra/` needs to know about rotor
  composition or frame maintenance. The field absorbs incoming pressure;
  the algebra provides operators when needed.
- **Freed:** Numerical drift in rotor compositions is no longer an
  architectural concern — only a local concern inside `algebra/`.
- **Watch:** `vocab/` is the most likely place for the coordinate frame to
  quietly re-emerge, e.g. if word representations are stored as flat
  positional vectors. ADR-0001 closes this specifically.

## Alternatives Considered

- **Keep rotor frame, improve numerical stability:** Rejected. The frame is
  the wrong abstraction, not just an unstable one.
- **Switch to hyperbolic embedding (Poincaré model):** Rejected. Still a
  coordinate system. Trades one frame for another.
- **Pure transformer-style embedding:** Rejected. This is the design
  we are replacing. Cosine similarity over positional vectors is precisely
  what the field-state model supersedes.
