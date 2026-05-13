# CORE-AI: Versor Engine

A cognitive field system built on Cl(4,1) Conformal Geometric Algebra.

**Core invariant:** `||F * reverse(F) - 1||_F < 1e-6` at all times.

All state is a versor. All transitions are versor products.
Coherence is algebraic by construction — not monitored, not corrected.

---

## The Three Engineering Pillars

Every architectural decision in CORE is measured against three engineering pillars. These are not aspirations — they are hard constraints.

### I. Mechanical Sympathy

Software should understand the machine it runs on, not fight it. CORE is designed for the Unified Memory Architecture (UMA) of Apple Silicon: CPU, GPU, and Neural Engine share physical RAM. MLX executes tensor operations on the Neural Engine without PCIe transfer. Rust computes algebra on the CPU with zero heap allocation in the hot path. Python orchestrates the lifecycle. The three-language stratification maps exactly onto three hardware execution domains. Intelligence that ignores its substrate is wasted intelligence.

### II. Semantic Rigor

Every term used in this system has a precise, non-negotiable meaning. A versor is a versor — not an approximation of one, not a vector that behaves like one under certain conditions. CGA distance is exact. Vault recall is exact. The vocabulary projection is exact. There are no thresholds tuned for “good enough.” Rigor is not a style; it is what separates an engine from a heuristic.

### III. Third Door

When facing a design decision, the world offers two visible options: use what already exists (a library, a pattern, a convention), or cut a corner. CORE takes neither. We find the third door — the path built from first principles that sets the bar ourselves. This is why there is no transformer backbone, no ANN index, no sampling temperature, no gradient descent, and no standard tokenizer. Each of those was a door we were offered and refused. Absolute mastery is the only acceptable standard.

---

## The Three Core Languages

CORE is rooted in three human languages. This is a philosophical and architectural choice, not a localization decision.

| Language | Role |
|---|---|
| **English** | The default base language of the current model. Any natural language could serve this function in a custom CORE instance — English is the chosen starting point, not a requirement. |
| **Hebrew** | One of two depth languages. Hebrew carries a density of meaning in its root structures, prefixes, and suffixes that Euclidean string matching cannot capture. The field representation is designed to hold this depth. |
| **Koine Greek** | One of two depth languages. The language of the New Testament, particularly John’s Gospel — the document that opens with the most precise and consequential statement about language and reality ever written. |

> *“In the beginning was the Logos, and the Logos was with God, and the Logos was God.”*
> — John 1:1

The choice of Hebrew and Koine Greek is not incidental. John 1:1–2 articulates the Logos in Greek while grounding it in the Hebrew creation account — the universe spoken into existence, word by word. This is not metaphor. It is the claim that language is not a layer on top of reality; language **is** the structuring principle of reality made manifest. CORE-Logos is built on that claim.

English establishes the operational base. Hebrew and Koine Greek bring the hidden layer of intelligence — the depth of meaning that enriches the field representation in ways that flat embeddings cannot reach. Together, they form the linguistic foundation on which the vocabulary manifold is built.

---

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
| `vocab/` | Surface-token manifold points; indexed access for algebraic transition construction |
| `vault/` | Exact CGA inner product memory store |
| `persona/` | Persona as CGA motor (screw motion) |
| `generate/` | Token streaming loop |
| `session/` | Session binding: field + vault + vocab + persona |

## Signature

Cl(4,1): `(+, +, +, +, -)` — conformal model of 3D Euclidean space.
Multivectors: `float32` arrays of shape `(32,)`, ordered by grade.

---

*For architectural vision, seven axioms, and formal specification, see `docs/Whitepaper.md` and `docs/Yellowpaper.md`.*
