# ADR-0136 — Statement-Layer Corridor: Graduated GSM8K Admission via Parser Extension

**Status:** Active
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Parent:** [ADR-0131.G](./ADR-0131.G-gsm8k-coverage-probe.md)
**Depends on:**
[ADR-0115](./ADR-0115-math-problem-parser-and-graph.md),
[ADR-0116](./ADR-0116-deterministic-solver.md),
[ADR-0117](./ADR-0117-solution-trace-verifier.md)

---

## Context

ADR-0131.G pinned the GSM8K coverage probe at **0/50 admission** and established
`admitted_wrong == 0` as a standing architectural invariant. The G.x capability
axes (G.1–G.5) have landed on main; as of ADR-0131.5 (probe retirement), the
GSM8K probe is no longer a per-iteration gate — it activates only when a new
iteration claims Δadmission_rate ≥ 0.02.

A taxonomy pass over all 50 refused cases (S.0) produced the following breakdown:

| Primary barrier | Count | Notes |
|---|---|---|
| `context_filler` | 23 | Narrative scene-setters; parser's refusal is correct |
| `compound_statement` | 5 | Two operations in one sentence |
| rate/capacity/price class | 4 | Direct targets of S.1 |
| `distributive_multiply` | 1 (+5 secondary) | N bags × M items each |
| diverse long-tail | 17 | Age anchors, goal statements, multi-step chains, etc. |

The 23 context-filler cases will not be addressed by statement-layer work alone —
they need semantic classification of scene-setting sentences, which is a separate
architectural concern. **The safety rail stands: if a sentence cannot parse into
a numeric initial-state candidate, the problem is refused.**

The G.x micro-extension approach has been retired. Each G.x axis targeted one
regex shape in isolation; the return per axis was tiny and the axes were not
composable into a coherent parser narrative. The Statement-Layer Corridor replaces
G.x with a phased taxonomy-driven program that:

1. Classifies all refusals before writing any code.
2. Targets the highest-signal unlockable barriers first.
3. Ships each phase as a self-contained unit with a curated axis lane, `wrong == 0`
   gate, and honest GSM8K delta.
4. Never attempts to bypass the context-filler safety rail.

---

## Decision

Organize parser extension work as a **corridor of phases** rooted at ADR-0136:

| Phase | ADR | Scope | Primary barrier targeted |
|---|---|---|---|
| S.0 | (this doc) | Taxonomy — deterministic classification of 50 refused cases | — |
| S.1 | ADR-0136.S.1 | Rate/event statements — capacity-rate + earnings-rate shapes | rate class (≤4 cases) |
| S.2 | ADR-0136.S.2 | Temporal statements — time anchors, duration expressions | time/age long-tail |
| S.3 | ADR-0136.S.3 | Compound statements — two operations in one sentence | `compound_statement` (5 cases) |
| S.4 | ADR-0136.S.4 | Coreference — pronoun + ellipsis resolution across sentences | cross-sentence barriers |

Phases S.2–S.4 are deferred; scope and sequencing will be revisited after S.1 lands.

---

## Taxonomy (S.0)

Stored at: `evals/gsm8k_math/train_sample/v1/refusal_taxonomy.json`

Schema v1. Each record carries:
- `case_id` — GSM8K case identifier
- `primary_barrier` — the single barrier that causes refusal even if all others were resolved
- `secondary_barriers` — additional barriers present in the problem
- `notes` — free-text rationale

**Key finding.** The case with the shallowest barrier is `gsm8k-0014`:

```
Bob can shuck 10 oysters in 5 minutes.
How many oysters can he shuck in 2 hours?
```

This is a single-statement capacity-rate problem with a pronoun question. It is the
proof case for S.1: it must admit with `answer == 240.0`.

---

## Invariants

These invariants are non-negotiable across all corridor phases:

- **`admitted_wrong == 0`** — no GSM8K case is admitted with a wrong answer.
- **Context-filler safety rail** — sentences without parseable numeric initial state
  are refused; no soft-fail or skip-and-continue.
- **Honest delta** — each phase's PR body states the exact pre/post GSM8K admission
  count; no rounding, no "approximately".
- **No solver/graph/verifier changes** — rate-path short-circuits and new extractors
  live in `math_candidate_parser.py` and `math_candidate_graph.py` only.

---

## Consequences

- The G.x capability axis namespace is closed. New axes use the S.x naming convention.
- Each S.x phase ships its own curated axis lane at
  `evals/math_capability_axes/S<N>_<name>/v1/cases.jsonl`.
- The GSM8K probe re-activates when a phase claims ≥1 new admission
  (Δadmission_rate ≥ 0.02); otherwise it stays retired per ADR-0131.5.
- S.1 is the only phase that can honestly claim unlocking the context-filler-gated
  cases once sentence-semantic classification lands (out of S.x scope).

---

## Deferred

- Context-filler gated problems (23 cases) — requires semantic classification of
  narrative scene-setting sentences; architecturally separate from statement parsing.
- Conditional branching (`if she works more than 8 hours`) — needs branching semantics
  in the solver.
- Percentage/interest rates — needs decimal arithmetic extension.
- Multi-statement rate problems (duration in separate sentence from capacity) — needs
  coreference, addressed in S.4.
