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

## Native Substrate Direction — Python, Rust, Zig

CORE is not moving toward a wholesale Zig rewrite. The architecture is moving toward a stricter native-substrate boundary:

- **Python** remains the semantic source of truth: cognition runtime, teaching/review workflows, pack ratification, eval harnesses, and Workbench/operator tooling.
- **Rust** remains the incumbent native algebra backend: Cl(4,1) products, versor operations, CGA inner product, exact recall, and diffusion surfaces already proven by parity gates.
- **Zig** is a candidate material for the next native substrate layer: Delta-CRDT arenas/deltas/merge kernels, deterministic modality compilers such as `audio_core_v1`, stable C ABI surfaces, edge-native ingestion, and selected exact recall challenge kernels only after parity and benchmark proof.

The rule is component law, not language preference. Zig may enter where explicit allocation, deterministic buffer ownership, C ABI clarity, and edge-native deployment materially strengthen CORE. Zig must not replace review-gated semantics, introduce approximate recall, hide repair in native code, or turn teacher/shadow models into substrate.

Decision package: [`docs/zig/README.md`](docs/zig/README.md). Adoption gates: [`docs/zig/adoption-gates.md`](docs/zig/adoption-gates.md).

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

### CLI

The `core` CLI exposes curated entry points so reviewers can run any
subsystem in isolation. Highlights:

```bash
core test --list-suites                    # list curated pytest suite aliases
core test --suite fast                     # ~2s iteration lane
core test --suite cognition                # cognition pipeline lane
core test --suite algebra                  # versor / CGA / vault parity
core test --suite adr-0024                 # Forward Semantic Control chain (98 tests)

core demo audit-tour                       # 4-scene pack-layer audit walkthrough (ADR-0027..0041)
core demo pack-measurements                # ADR-0043 — pack-layer claims as per-pack measurements
core demo long-context-comparison          # ADR-0045 — CORE NIAH recall + frozen transformer baselines
core demo anti-regression                  # ADR-0057 — three-gate defense against learning harm
core demo learning-loop                    # ADR-0055..0057 — cold turn → discovery → propose → accept → grounded
core demo phase6                           # 3-condition comparative table (CORE vs baseline)
core demo phase5                           # stratified 5-family mechanism-isolation
core demo all                              # both + combined summary
core demo list-results                     # index every JSON report with headline metrics

core eval --list                           # discover eval lanes
core eval cognition                        # run a discovered lane
core eval gsm8k_math                       # Phase 5 capability lane (correct/wrong/refused triple)
core trace "your text here"                # one-turn field-telemetry trace
core pulse "What is truth?"                # one full cognitive pulse
core bench --suite latency                 # benchmark harness
core bench --suite teaching-loop --runs 100  # ADR-0055..0057 — replayable learning loop determinism
core bench --suite articulation            # Phase 4 capability proof (breadth + determinism + footprint + cross-topic + ollama compare)
core bench --suite articulation --ollama-model llama3:8b  # side-by-side with a local Ollama model
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

## Inter-Session Memory — Reviewed Learning

CORE extends its own teaching corpus through a four-tier path: session vault → turn-event audit → reviewed teaching corpus → ratified packs. No opaque gradient updates, no uncurated ingestion. The only path to active-corpus extension is the review-gated `TeachingChainProposal` ([ADR-0057](docs/decisions/ADR-0057-teaching-chain-proposal-review.md)), built from a contemplated `DiscoveryCandidate` ([ADR-0056](docs/decisions/ADR-0056-contemplation-loop.md)) emitted by the turn loop ([ADR-0055](docs/decisions/ADR-0055-inter-session-memory.md)).

Three independent gates every extension must pass:

| Gate | What it checks | Trust property |
|---|---|---|
| **Eligibility predicate** | polarity ∈ {affirms, falsifies} ∧ ≥1 `source='corpus'` evidence ∧ claim_domain ≠ evaluative ∧ boundary_clean ∧ chain complete | Pre-replay; raises `ProposalError`; no log entry. |
| **Replay-equivalence gate** | Full cognition lane on active vs transient-with-append; any strict-decrease in `intent_accuracy / surface_groundedness / term_capture_rate / versor_closure_rate` auto-rejects with named metrics. | Active corpus byte-identical pre/post. |
| **Operator review** | Explicit `core teaching review <id> --accept` writes one JSONL line via `append_chain_to_corpus` (the sole corpus-write surface). | No auto-apply; replay-equivalence is a precondition, not a permission. |

Supersession is the second operator-direct mutation surface: `core teaching supersede <old_chain_id>` retires an active chain by appending a replacement with `superseded_by`, with byte-identical rollback on any post-audit failure.

Three live demos / benchmarks make the chain demoable end-to-end:

| Demo | Headline claim | Live command | Writeup |
|---|---|---|---|
| **Anti-regression** | Three independent gates each fail closed; bad proposals stop at the cheapest applicable gate. | `core demo anti-regression` | [`docs/evals/anti_regression_demo.md`](docs/evals/anti_regression_demo.md) |
| **Learning loop** | Same deterministic prompt: `[none] I don't know…` before, `[teaching] thought reveals meaning…` after one accept. | `core demo learning-loop` | [`docs/evals/learning_loop_demo.md`](docs/evals/learning_loop_demo.md) |
| **Determinism bench** | N identical inputs → N byte-identical proposal_id / replay metrics / chain_id. 100 runs: `unique=1` everywhere, mean ≈ 1.85s. | `core bench --suite teaching-loop --runs 100` | [`docs/evals/teaching_loop_bench.md`](docs/evals/teaching_loop_bench.md) |
| **Articulation suite** | Every intent shape fires + byte-identical surfaces across reruns + flat per-turn ΔRSS + cross-topic thread context + side-by-side with a local Ollama model showing CORE unique=1, Ollama unique≥2. | `core bench --suite articulation --ollama-model llama3:8b` | [`benchmarks/README.md`](benchmarks/README.md) |

Operator surfaces:

```
core teaching audit                                 # surface load decisions + drop reasons
core teaching propose <candidate-jsonl-path>        # build a proposal, run the replay gate
core teaching proposals --state pending             # inspect the proposal log
core teaching review <proposal_id> --accept --review-date YYYY-MM-DD
core teaching supersede <old_chain_id> --subject ... --intent ... --connective ... --object ... --review-date YYYY-MM-DD
core teaching supersessions                         # pair retired chains with replacements (orphan-aware)
```

---

## Evidence-Governed Domain Layer — The ADR-0091 Chain

CORE distinguishes *contract-passing* from *demonstrated*. A pack that satisfies the nine ADR-0091 predicates earns a `reasoning-capable` ledger row; that's a structural claim, not an empirical one. Promotion to `audit_passed=true` (formerly `expert_demo`; renamed by [ADR-0113](docs/decisions/ADR-0113-rename-expert-demo-to-audit-passed.md)) requires a **reviewer-signed evidence-bundle digest** that reproduces byte-for-byte from on-disk lane results (ADR-0106 + ADR-0109).

> **What `audit-passed` actually means** — and what it does NOT mean.
> The gate verifies CORE *claim-shape compliance*: signed digest, replay determinism, typed refusal, exact recall, grounding-source provenance. **These are claim shapes a transformer LLM cannot structurally produce regardless of raw accuracy.** A frontier LLM might score higher on the same benchmark but cannot pass this contract because it cannot produce a digest that re-derives, cannot guarantee typed refusal, cannot emit a deterministic trace hash, cannot replay byte-equal. **This is NOT a raw-capability claim.** The `expert` ledger tier ([ADR-0114](docs/decisions/ADR-0114-expert-capability-roadmap-gsm8k-first.md); contract shipped in [ADR-0120](docs/decisions/ADR-0120-expert-promotion-contract.md)) sits one tier above `audit-passed` and certifies grammar-coverage + claim-shape discipline on **CORE-authored** evals — explicitly **not** raw-accuracy parity against frontier models. **As of this writing no domain holds `expert`:** `mathematics_logic` was signed into it (ledger flip, 2026-05-23) but the signature has since lapsed against advanced evidence, so the live ledger reports it as `audit-passed` — see the dedicated note below.

| Layer | What it guarantees | ADR |
|---|---|---|
| **Domain Pack Contract v1** | Nine predicate checks on every ratified pack (lemma coverage, operator chain count, intent shapes, holdout coverage, reviewer-resolution, etc.). | [0091](docs/decisions/ADR-0091-domain-pack-contract-v1.md) |
| **Reviewer Registry v1** | YAML-anchored, schema-validated reviewer roster. Wildcard `*` reserved for primary reviewers; domain-scoped reviewers gated by `can_review(domain, scope)`. | [0092](docs/decisions/ADR-0092-reviewer-registry-v1.md) |
| **Fabrication-control eval lane** | Negative-control lane: phantom endpoints, cross-pack non-bridges, sibling collapses must all refuse. `fabricated=0` across all by-class buckets is the gate. | [0096](docs/decisions/ADR-0096-fabrication-control-eval-lane.md) |
| **Audit-passed promotion contract** | Domain-aware, reviewer-signed, replay-deterministic. No domain promotes silently; every `audit_passed=true` row points to an `audit_passed_claims` entry whose SHA-256 reproduces. (Originally landed as `expert-demo`; renamed by ADR-0113.) | [0106](docs/decisions/ADR-0106-expert-demo-promotion-contract.md), [0113](docs/decisions/ADR-0113-rename-expert-demo-to-audit-passed.md) |
| **Lane-shape registry** | Eight lane ids dispatch to five shapes (`cognition_shape`, `accuracy_shape`, `inference_shape`, `refusal_shape`, `symbolic_logic_shape`); unknown lanes fail-closed. | [0109](docs/decisions/ADR-0109-lane-shape-aware-thresholds.md) |

**Current ledger state** (per `core capability ledger`):

| Domain | Status |
|---|---|
| `mathematics_logic` | **`audit-passed`** (first promotion, [ADR-0110](docs/decisions/ADR-0110-mathematics-logic-expert-demo-promotion.md); status string renamed by [ADR-0113](docs/decisions/ADR-0113-rename-expert-demo-to-audit-passed.md)) |
| `physics` | **`audit-passed`** (second promotion, [ADR-0111](docs/decisions/ADR-0111-physics-expert-demo-promotion.md)) |
| `systems_software` | **`audit-passed`** (third promotion, [ADR-0124](docs/decisions/ADR-0124-systems-software-audit-passed-promotion.md)) |
| `hebrew_greek_textual_reasoning` | `reasoning-capable` |
| `philosophy_theology` | `reasoning-capable` |

> **On the `expert` tier (one above `audit-passed`).** The tier is wired and a promotion has been *signed once* — `mathematics_logic` via the [ADR-0120 ledger flip](docs/decisions/ADR-0120-math-expert-ledger-flip.md) (2026-05-23) — yet the table above still reads `audit-passed`, **correctly.** The expert composer requires the reviewer-signed `claim_digest` to match the *current* evidence-bundle digest; when the GSM8K evidence advanced (#488, #500) the recomputed digest changed and the stale signature stopped matching, so the live `core capability ledger` **refuses** the promotion and reports `audit-passed`. This is the signed-digest contract working as designed — a lapsed claim is demoted, not honored. (Details in "Path to … expert capability" below.)

The contract has now demonstrated its load-bearing behavior end-to-end: refused one promotion attempt honestly ([ADR-0107](docs/decisions/ADR-0107-mathematics-logic-expert-demo-deferred.md)), amended its threshold rules once cleanly (ADR-0109), succeeded against `mathematics_logic` (ADR-0110), and succeeded against a second distinct domain `physics` without further contract change (ADR-0111). External readers can distinguish the two ceilings at a glance; the "math-only" objection is retired.

**See the actual demonstration ([ADR-0112](docs/decisions/ADR-0112-runnable-expert-demo-showcase.md), renamed by [ADR-0113](docs/decisions/ADR-0113-rename-expert-demo-to-audit-passed.md)):**

```bash
core demo audit-passed --domain mathematics_logic
core demo audit-passed --domain physics
# → evals/audit_passed/<domain>/latest/audit_passed.html
```

Each run re-derives the signed evidence-bundle digest from on-disk lane result files, asserts byte-for-byte match against `docs/reviewers.yaml`, and renders an HTML showcase with per-lane shape-check verdicts plus the first three sample cases from each split. The composer is read-only and byte-deterministic (same inputs → same SHA-256). An unpromoted domain produces a typed refusal, not a fake showcase.

### Path to actual expert-level capability — Phase 5 substrate complete

The `audit-passed` gate above is intentionally *not* a raw-capability claim. The
honest path to one is laid out in [ADR-0114 — Expert-Capability Roadmap: GSM8K-Math
First](docs/decisions/ADR-0114-expert-capability-roadmap-gsm8k-first.md). Phases 1–4
(parser, solver, verifier, stepped-realizer) and Phase 5 (GSM8K eval lane) have now
all landed.

**Phase 5 substrate is complete as of 2026-05-23.** All 8 sub-phases of
[ADR-0119](docs/decisions/ADR-0119-gsm8k-eval-lane-roadmap.md) have landed.
ADR-0114a's 10 anti-overfitting proof obligations are all discharged for the
`gsm8k_math` lane.

**Three distinct GSM8K numbers — do not conflate them:** (a) the *real* sealed test
(HF `openai/gsm8k`, 1,319 rows): **0 correct / 0 wrong / 1,319 refused**; (b) a real
50-case train sample currently at **6 correct / 0 wrong / 44 refused** (coverage
climbing, wrong=0 held); and (c) a **CORE-authored** 150-case synthetic "public" split
at **150/150** that the frontier comparison (vs Claude 96.4%, GPT-4 92%, Gemini 90.8%)
is scored against — an apples-vs-oranges comparison, as
`evals/gsm8k_math/baselines/comparison_v1.json` itself states, since the public split is
original rule-built problems that exercise the grammar (no benchmark contamination).

**First honest CORE-vs-real-GSM8K measurement (ADR-0119.7):** 0/1,319 correct,
**0/1,319 wrong**, 1,319/1,319 refused. CORE refuses what it cannot grammar-handle;
it does not confabulate. The zero-confabulation property holds against the external
benchmark.

**ADR-0120 shipped the first `expert` promotion contract; the composer is wired and
the gate passes — but no domain currently *holds* `expert`.** The exact, honest state,
because it is easy to overclaim:

- `mathematics_logic` *was* signed into `expert` (the
  [ADR-0120 ledger flip](docs/decisions/ADR-0120-math-expert-ledger-flip.md),
  2026-05-23) on a **composite of three CORE-authored evals** —
  [ADR-0131.4](docs/decisions/ADR-0131.4-composite-math-gate.md) substituted these for
  the original GSM8K `correct_rate ≥ 0.60` requirement: **B1** symbolic-equivalence
  (185/185), **B2** teaching-corpus (40/40), **B3** bounded-grammar (50/50), each
  **wrong=0**, all 10 ADR-0114a obligations discharged.
- That signature has since **lapsed.** The reviewer-signed `claim_digest` is bound to
  the exact evidence bundle; when the GSM8K evidence advanced (#488 → 4/46/0, #500 →
  6/44/0) the recomputed digest changed (`4c46f530… → 02f6d3c8…`), so the signature no
  longer matches and the expert composer **refuses** the promotion. The live
  `core capability ledger` therefore reports `mathematics_logic` as **`audit-passed`**
  today. The contract demoting a stale claim rather than honoring it is the mechanism
  working as designed.
- So `expert` certifies **grammar-coverage + claim-shape discipline on CORE-authored
  problems** — it is **not** a raw-capability parity claim against frontier models, and
  no domain has cleared a real external-benchmark bar. Real GSM8K stays an **ungated**
  stress lane at 0/1,319 correct, 0 wrong, 1,319 refused.

Re-earning the live `expert` row is a reviewer **re-signature over the current
evidence** (operator action), not new capability work — the composite gate already
passes.

To run the GSM8K math eval lane:

```bash
core eval gsm8k_math            # run against CORE-original public split
# evals/gsm8k_math/runner.py   # lane runner (LaneReport with correct/wrong/refused)
```

Full ADR index, frontier, and chain notes: [`docs/decisions/README.md`](docs/decisions/README.md).

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
