# CORE-AI: Versor Engine

A cognitive field system built on Cl(4,1) Conformal Geometric Algebra.

**Core invariant:** `||F * reverse(F) - 1||_F < 1e-6` at all times.

All state is a versor. All transitions are versor products.
Coherence is algebraic by construction — not monitored, not corrected.

---

## Research Status

CORE is an independent AI research project exploring deterministic cognition, explicit epistemic state, replayable reasoning, refusal-first behavior, and audited learning paths.

The current public proof corridor is strongest in:

- deterministic replay
- traced rejection
- coherent refusal
- review-gated learning
- invariant-preserving runtime transitions
- bounded-domain reasoning demonstrations

CORE should currently be evaluated as a reproducible research system with measurable invariants and public evidence — not as a finished frontier-general model.

For a recruiter/funder/collaborator entry point, see [`docs/research_portfolio.md`](docs/research_portfolio.md).

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

## The Truth-Seeking Schema

Co-equal with the algebraic substrate. CORE's epistemic schema is a foundational architectural commitment: every claim that enters the runtime field carries a typed position in a revision graph (`SPECULATIVE`, `COHERENT`, `CONTESTED`, `FALSIFIED`); coherence — not source authority — is the only admission signal; no claim is ever locked, even when COHERENT; identity cannot be rewritten by content; and exactly one mutation path admits knowledge, enforced by a CI-level architectural-invariant test.

The schema is the structural defense against the failure modes that afflict both fluent LLMs and human reasoning: confabulation, exaggeration, deference to authority, self-protection through erasure, self-promotion through self-citation, and the ossification of mistaken beliefs.

A system that samples cannot have these properties — sampling has no place to attach an epistemic status. CORE has them because every admitted claim carries one and the only path to admission is the review path.

**Full architectural commitment, including honestly-published gaps:** [`docs/truth_seeking_schema.md`](docs/truth_seeking_schema.md).
**Reproducible measurements:** [`CLAIMS.md`](CLAIMS.md) (auto-generated from `scripts/generate_claims.py`).

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
pytest tests/test_versor_closure.py        # the core invariant — must pass first
pytest tests/                              # full suite (~4 minutes, 1099 tests)
```

### Watch the flywheel turn — one command

For a public-facing reproduction of the core thesis, in **four
falsifiable scenes**:

```bash
core demo flywheel
```

This runs end-to-end on the canonical pack:

1. **Ratify** — `apply_composition_claim()` writes a reviewed JSONL
   artifact; RAT-1's `compile_pack` regenerates the runtime
   `compositions.jsonl` + updates the manifest checksum.
2. **Load** — `composition_registry` reads the new entry on the next
   runtime turn.
3. **Solve** — a real problem (`"Lilibeth fills 6 baskets where each
   basket holds 50 strawberries. How many strawberries does Lilibeth
   have?"`) admits via the matcher → injector → admission chain and
   produces `answer=300`.
4. **Hazard** — case 0050 (the `wrong=0` canary) remains refused —
   no SAFE composition category can convert it from refused to
   wrong.

Every scene is byte-deterministic; the canonical pack is read-only
throughout; the demo mutates only a synthetic test pack in a
tempdir. See [`evals/flywheel_demo/run_tour.py`](evals/flywheel_demo/run_tour.py).

```bash
core teaching coverage --use-reader        # per-shape histogram + hazard pin status
core teaching coverage --use-reader --delta  # diff vs HEAD's committed report.json
```
