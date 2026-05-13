# CORE-AI: Versor Engine

A cognitive field system built on Cl(4,1) Conformal Geometric Algebra.

**Core invariant:** `||F * reverse(F) - 1||_F < 1e-6` at all times.

All state is a versor. All transitions are versor products.
Coherence is algebraic by construction — not monitored, not corrected.

## Quick Start

```bash
pip install -e ".[dev]"
pytest tests/test_versor_closure.py  # must pass before anything else
pytest tests/
```

## Architecture

```
raw input -> ingest/gate.py       (normalize once)
          -> field/propagate.py   (versor_apply every step)
          -> generate/stream.py   (nearest by cga_inner)
          -> vault/store.py       (store and recall by cga_inner)
          -> persona/motor.py     (rigid motor, not weight overlay)
```

## The Two Primitives

- `versor_apply(V, F) = V * F * reverse(V)` — the only field transition
- `cga_inner(X, Y) = -d^2 / 2` — the only distance metric

## Layers

| Layer | Purpose |
|---|---|
| `algebra/` | Cl(4,1) multivector math, versor ops, CGA, holonomy |
| `ingest/` | Single injection gate — the only normalization site |
| `field/` | FieldState dataclass and propagation loop |
| `vocab/` | Word-to-versor manifold, edge rotors |
| `vault/` | Exact CGA inner product memory store |
| `persona/` | Persona as CGA motor (screw motion) |
| `generate/` | Token streaming loop |
| `session/` | Session binding: field + vault + vocab + persona |

## Signature

Cl(4,1): `(+, +, +, +, -)` — conformal model of 3D Euclidean space.
Multivectors: `float32` arrays of shape `(32,)`, ordered by grade.
