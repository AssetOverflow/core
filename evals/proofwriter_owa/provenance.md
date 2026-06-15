# evals/proofwriter_owa — provenance (B1: OWA refusal floor)

The ProofWriter-OWA refusal-floor lane (mastery-v2 Step 3, Brief 1). It proves the
open-world soundness floor: the engine's `determine()` never asserts a query `True` when
the open-world truth is `Unknown` or `False`. It hardens "unknown ≠ false" before the
transitive-chain (B2) and closed-world (B4) work can stress it.

## Independent gold (oracle), not a dataset slice

This environment has no live ProofWriter dataset access, so the items are **hand-authored
in ProofWriter-OWA style** — small is-a / relational theories + one yes/no query — rather
than verbatim dataset rows. Critically, the gold label is **not** hand-asserted: it is
computed by a **separate minimal oracle** (`oracle.py`) with its own parser and its own
OWA reasoner, importing **none** of `determine`, `comprehend` / MeaningGraph realization,
or the production predicate-entailment helpers (INV-25 / INV-27 — the gold producer is
disjoint from the solver). The fixture's hand-authored `expected` field pins the oracle's
output, so the oracle is itself verified (`test_oracle_matches_authored_expected`).

Source / semantics reference: AllenAI **ProofWriter** (V2020.12.3, arXiv:2012.13048) — the
open-world `{True, Unknown, False}` label semantics. Attribution only; no dataset
redistribution.

## What the lane checks

- **`wrong == 0`** — `determine()` asserts `True` only on a gold-`True` item. A `True`
  assertion on a gold `Unknown` OR `False` is a soundness breach. (`determine()` is sound,
  so this is a hard floor; the lane makes any regression *findable* against the
  independent oracle.)
- gold-`True` items marked `serving_support` (member/subset subsumption, plus #775
  inverse/symmetric one-hop) **must** determine `True` — no silent coverage loss.
- no `answer=False` is ever constructed (INV-30 holds, behaviorally re-checked here).

## Scope (oracle grammar)

member / subset / is-a closure; explicit negation (`No X is a Y` → disjointness, the
source of every gold-`False`); and #775 inverse/symmetric **one-hop** relational rules.
**No transitive relational chains** — that is Brief 2; an "oracle-only gold side" hook is
left for when it lands.

This lane is **measure-only**: it touches no engine code and is deliberately **not a
capability-index domain** (a refusal floor has low coverage and would drag the index's
`coverage_geomean`). It runs as its own standalone wrong=0 gate.

## Current result

`19 items → 9 correct (all serving_support True), 10 refused (Unknown/False), 0 wrong`.
