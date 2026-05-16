# compositionality eval lane

## What it measures

Whether CORE generalises **across construction families**: relation
patterns and entity sets seen at teaching time should compose into
novel (relation, entity) combinations at probe time, even though the
specific combination was never taught directly.

This is the lane the roadmap flags as most vulnerable to overfitting
(`docs/capability_roadmap.md` Phase 3, anti-overfitting note).  The
split below honours that warning:

  Training (teaching turns)        Test (probe)
  --------------------------       ----------------------------
  R1(A, B), R1(C, D)               R1(A, D)        — seen entities, novel pair
  R2(A, B), R2(C, D)               R2(C, B)        — same
  R3(E, F), R3(G, H)               R3 applied to seen entities only
  ...
  (NEVER teach (A, D) under R1)

The probe asks for the entailment under a relation the model has
seen with *both endpoints* — but never with this specific pair.

## Why it matters

Frontier LLMs compose well because their training set already
contains nearly every short combination of common entities and
relations.  CORE's claim is stronger and harder: that the algebraic
structure of the proposition graph *itself* supports composition,
without requiring the specific combination to have been seen.  This
lane tests that claim.

## Patterns covered (v1)

| Pattern | Construction-family rule |
|---|---|
| `novel_pair_under_seen_relation` | `R(A,B)` and `R(C,D)` taught; probe `R(A,D)`. Pass = response references `D` (the seen RHS under R applied to seen LHS A). |
| `novel_relation_on_seen_pair` | `R(A,B)` and `R'(C,D)` taught with `A`, `B`, `C`, `D` independently grounded; probe `R'(A,B)`. Pass = response references the chain-derived target under `R'`. |
| `composed_predicate` | `is(A,B)` and `precedes(B,C)` taught; probe asks `What does A precede?` Pass = response references `C`. |

Each pattern relies only on the existing
`en_core_cognition_v1` relation vocabulary (`is`, `causes`,
`precedes`, `follows`, `grounds`, `belongs_to`, `means`, `reveals`,
`contrasts_with`).

## Sub-metrics

- `M1. compositional_token_hit`  — the expected composed-entity
  token appears in `surface` or `walk_surface` (case-insensitive,
  token-bounded).
- `M2. premises_stored`           — all teaching turns produce
  proposals.
- `M3. replay_determinism`        — two fresh runs match by
  `trace_hash`.
- `M4. no_taught_pair_leakage`    — the construction-family split is
  enforced at authoring time (verified by the lane runner: every
  probe is checked against the premise list to ensure the probe's
  exact `(R, A, target)` triple does NOT appear verbatim).

A case passes when M1 AND M2 AND M3 hold.  M4 is a structural
authoring check (true by construction); the runner reports it for
audit.

## Overall pass thresholds (v1)

- `compositional_recall_rate` (M1) ≥ 0.50
- `premises_stored_rate` ≥ 0.95
- `replay_determinism` ≥ 0.95

This lane is built knowing the same `graph_planner` and
`field/propagate` gaps that the inference-closure lane surfaced will
likely cause v1 to fail uniformly.  v1's value is to score the gap
*per pattern* so the future v2 engineering can target the right one.

## Anti-overfitting

- Public split uses one entity set; holdouts uses a disjoint set.
- No probe's `(R, A, target)` triple is ever a verbatim premise.
- Patterns differ structurally between splits to avoid template
  memorisation.
