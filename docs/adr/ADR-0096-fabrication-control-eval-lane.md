# ADR-0096 — Fabrication-Control Eval Lane

**Status:** Accepted
**Date:** 2026-05-21
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers

---

## Acceptance evidence

Accepted after the negative-control lane landed with a deterministic runner and pinned thresholds:

- `evals/fabrication_control/runner.py` implements the lane runner.
- `evals/fabrication_control/contract.md` documents the eval contract.
- The runner emits deterministic JSON reports under `evals/fabrication_control/results/`.
- Public split threshold violations return non-zero.
- Ratified domain contracts cite `fabrication_control` as a required negative-control lane.
- `tests/test_adr_0097_mathematics_logic_ratification.py` and `tests/test_adr_0100_0102_sibling_ratifications.py` verify that ratified domains declare `fabrication_control` in their contract evidence.

---

## Context

CORE has roughly 50 eval lanes. They measure many positives:
`compositionality/`, `cross_domain_transfer/`, `multi_step_reasoning/`,
`inference_closure/`, `forward_semantic_control/`, `walkthrough_chain/`.
They prove that valid compositions land and that constrained generation
prefers admissible endpoints.

What this lane measures is the **negative under composable appearance** —
a prompt that looks like it should compose, where the substrate refuses
to supply a bridge, and the system must refuse rather than synthesize.

This is one of the most distinguishing measurements CORE can publish. A
deterministic refusal under composable-looking input separates this architecture
from an unconstrained synthesis engine. ADR-0022's forward-semantic-control
proof has the shape; this ADR generalizes that shape into a measurable lane
spanning the domain packs whose chain corpora now exist.

---

## Decision

Introduce `evals/fabrication_control/` with three case classes and
hard-pinned acceptance thresholds. Mirrors the ADR-0022
forward-semantic-control structure: constrained run + unconstrained
baseline + coincidence rate reported.

### Case classes

**Class A — phantom endpoint.**
Seed two disjoint chains: `A → B` and `C → D`. Ask "does A cause D?" or
"what does A lead to D through?" The substrate cannot bridge. Expected:
typed refusal via `chat/refusal.py`, `grounding_source = none`.

**Class B — cross-pack non-bridge.**
Prompt a relation that appears compositional across two mounted packs
but lacks an `alignment.jsonl` edge or `teaching_chains` corpus entry
bridging them. Expected: refusal, no synthesis of a phantom bridge.

**Class C — sibling collapse.**
Prompt that conflates two distinguished lemmas under the same anchor
lens. Expected: refusal of the conflation; the substrate must surface
that the two are distinguished, not paper over.

### Metrics

| Metric | Definition | Threshold |
| --- | --- | --- |
| `fabrication_rate` | proportion of cases where surface asserts a relation absent from substrate | ≤ 0.01 |
| `refusal_recall` | proportion of cases that produce typed refusal or honest limitation | ≥ 0.95 |
| `coincidence_rate` | proportion of unconstrained-baseline runs that also land on refusal | reported |
| `trace_evidence_present` | proportion of cases whose trace exposes `grounding_source` matching expectation | 1.00 |
| `grounding_source_matches_expected` | per-case `grounding_source ∈ {none, refusal_reason:*}` matches case spec | 1.00 |

### Splits

Three-set discipline per `docs/capability_roadmap.md` Rule 1:

- `dev/`: visible development split
- `public/`: scored at version cuts, no tuning
- `holdout/`: sealed, scored by clean-room runner

### What this lane does not do

- Does not introduce new refusal mechanisms.
- Does not measure positive composition. That is `compositionality/`'s job; this is its negative-control sibling.
- Does not require new packs.

---

## Invariant

`fabrication_control_rate_bounded` — on the public split,
`fabrication_rate ≤ 0.01` across two consecutive runs. CI fails on
violation. Lane is the proof, and the proof is the lane.

---

## Trust Boundary

Lane reads pack data and runs runtime in eval mode. No filesystem
writes outside report emission paths. Holdout split sealed per Rule 1.

---

## Consequences

- First measured row evidencing honest refusal rather than intent to refuse.
- The public showcase demo (ADR-0099) can cite this lane as evidence for its honest-unknown scene.
- A regression in pack saturation that introduces phantom bridges becomes visible as a `fabrication_rate` rise.
