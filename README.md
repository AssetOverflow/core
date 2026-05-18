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

## The Truth-Seeking Schema

Co-equal with the algebraic substrate. CORE's epistemic schema is a foundational architectural commitment: every claim that enters the runtime field carries a typed position in a revision graph (`SPECULATIVE`, `COHERENT`, `CONTESTED`, `FALSIFIED`); coherence — not source authority — is the only admission signal; no claim is ever locked, even when COHERENT; identity cannot be rewritten by content; and exactly one mutation path admits knowledge, enforced by a CI-level architectural-invariant test.

The schema is the structural defense against the failure modes that afflict both fluent LLMs and human reasoning: confabulation, exaggeration, deference to authority, self-protection through erasure, self-promotion through self-citation, and the ossification of mistaken beliefs.

A system that samples cannot have these properties — sampling has no place to attach an epistemic status. CORE has them because every admitted claim carries one and the only path to admission is the review path.

**Full architectural commitment, including honestly-published gaps:** [`docs/truth_seeking_schema.md`](docs/truth_seeking_schema.md).
**Reproducible measurements:** [`evals/CLAIMS.md`](evals/CLAIMS.md).

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

### CLI

The `core` CLI exposes curated entry points so reviewers can run any
subsystem in isolation. Highlights:

```bash
core test --list-suites                    # list curated pytest suite aliases
core test --suite fast                     # ~2s iteration lane
core test --suite cognition                # cognition pipeline lane
core test --suite algebra                  # versor / CGA / vault parity
core test --suite adr-0024                 # Forward Semantic Control chain (98 tests)

core demo phase6                           # 3-condition comparative table (CORE vs baseline)
core demo phase5                           # stratified 5-family mechanism-isolation
core demo all                              # both + combined summary
core demo list-results                     # index every JSON report with headline metrics

core eval --list                           # discover eval lanes
core eval cognition                        # run a discovered lane
core trace "your text here"                # one-turn field-telemetry trace
core pulse "What is truth?"                # one full cognitive pulse
core bench --suite latency                 # benchmark harness
core doctor --packs --rust                 # environment + pack + Rust status
```

Every demo run rewrites `evals/forward_semantic_control/results/`
including an auto-refreshed `index.json` manifest — the single
place reviewers can read to see every available report.

---

## Forward Semantic Control — The ADR-0024 Chain

CORE generates text without sampling. The generation walk is
deterministic at the algebra level, but a deterministic walk over a
boundary-only candidate scorer can still emit tokens that are
inadmissible under the relation being asserted (e.g. answering a
*causes* question with the *means*-target). The ADR-0024 chain closes
that gap with five Architecture Decision Records and six phases of
implementation evidence.

| Layer | What it guarantees | ADR |
|---|---|---|
| **AdmissibilityRegion** | A typed region (`allowed_indices`, `relation_blade`, `frame_versor`) carried alongside every generation step. | [0022](docs/decisions/ADR-0022-forward-semantic-control.md) |
| **Region intersection proof** | The admissible token set is honored at the language/salience intersection layer. | [0023](docs/decisions/ADR-0023-forward-semantic-control-proof.md) |
| **Inner-loop destination check** | Each candidate's `cga_inner(versor(candidate), relation_blade)` is checked at the destination; rejection appears in `rejected_attempts`; exhaustion raises a typed `InnerLoopExhaustion`. | [0024](docs/decisions/ADR-0024-inner-loop-admissibility.md) |
| **Rotor / frame admissibility** | The rotor's *effect* on the field state is additionally checked against `frame_versor` in `generate/rotor_admissibility.py` — separate from algebra closure (intentional). | [0025](docs/decisions/ADR-0025-rotor-frame-admissibility-design-note.md) |
| **Ranked-with-margin gate** | Static-threshold tuning fails geometrically under Cl(4,1) signature; replaced with a scale-invariant margin gate (admit iff `score(top) − score(second) ≥ δ`). | [0026](docs/decisions/ADR-0026-ranked-admissibility-with-margin.md) |

The chain's three head-to-head claims, all CI-enforced:

| Claim | Test contract | Live demo |
|---|---|---|
| **C1 — Replay determinism** | `core test --suite phase6 -k TestC1` | `core demo phase6` |
| **C2 — Traced rejection** | `core test --suite phase6 -k TestC2` | `core demo phase6` |
| **C3 — Coherent refusal** | `core test --suite phase6 -k TestC3` | `core demo phase6` |

Full evidence:

* Runtime contract: [`docs/runtime_contracts.md`](docs/runtime_contracts.md) — Refusal / Margin / Rotor admissibility sections
* Stratified findings: [`docs/evals/phase5_stratified_findings.md`](docs/evals/phase5_stratified_findings.md) — 5 failure-mode families, 20 cases, per-family pass rates
* Comparative demo: [`docs/evals/phase6_comparative_demo.md`](docs/evals/phase6_comparative_demo.md) — three head-to-head conditions vs in-system baseline
* Reports directory: `evals/forward_semantic_control/results/`

---

## Safety Pack

Sibling to the identity packs but architecturally distinct: the safety pack at `packs/safety/core_safety_axes_v1.json` carries the boundaries CORE will **never** cross — `no_fabricated_source`, `no_hot_path_repair`, `no_identity_override`, `no_silent_correction`, `preserve_versor_closure`. The pack loads unconditionally at runtime startup (fail-closed on missing or unverified), and its boundaries are unioned into whatever identity pack is selected. Identity packs may *add* boundaries on top, but may never remove safety boundaries.

This is the architecture downstream robotics, healthcare, and other high-stakes deployments will need before they can build CORE into anything that matters. Full doctrine: [`docs/safety_packs.md`](docs/safety_packs.md); decision record: [ADR-0029](docs/decisions/ADR-0029-safety-packs.md).

---

## Identity Packs

CORE's identity is load-bearing: every reasoning trajectory is scored against an `IdentityManifold` of value axes, and a `PersonaMotor` derived from those axes biases every field walk. As of [ADR-0027](docs/decisions/ADR-0027-identity-packs.md) the manifold is no longer hardcoded — it is loaded at runtime from a swappable, content-addressed pack under `packs/identity/`.

The shipping default `identity.default_general_v1` carries the previously-hardcoded three axes (`truthfulness`, `coherence`, `reverence`) so the default behavior is preserved. Two specialization packs ship alongside it for demonstrating identity-divergence: `identity.precision_first_v1` and `identity.generosity_first_v1`. Override on the chat surface with `core chat --identity <pack_id>`.

[ADR-0028](docs/decisions/ADR-0028-identity-surface-wiring.md) makes the swap *visibly load-bearing*: each pack carries a `surface_preferences` block (hedge thresholds, hedge phrases, claim-strength policy) consumed by the assembler. On the same prompt at the same alignment, `precision_first_v1` hedges sooner with "Arguably," / "In some cases," while `generosity_first_v1` leaves the assertion bare — see `tests/test_identity_surface_divergence.py` for the proof.

Robotics, personalization, and creative-tool builders author their own ratified identity packs via the formation pipeline's `identity_anchor` template, then ship them under `packs/identity/` in their deployment. Full format spec, loader contract, and authoring guide: [`docs/identity_packs.md`](docs/identity_packs.md).

---

## Teaching Order

CORE's manifold is built by ratified relations under a strict prerequisite DAG — not by absorbing a corpus. The "elementary → college" intuition is right at the macro level (simple before composed, anchored before novel) and wrong at the literal level (don't import a K–12 corpus). Five-layer ordering: **identity axes → atomic definitions → binary relations → composed relations → domain expansion**, re-applied inside every new domain.

Full doctrine, decision rules, and curriculum-platform locations: [`docs/teaching_order.md`](docs/teaching_order.md).

---

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
