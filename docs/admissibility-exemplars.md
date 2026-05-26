# Admissibility Exemplars (ADR-0163 Phase B)

Operator-facing overview of the hand-authored exemplar corpora that feed the
Phase C contemplation runner.  For the full schema, sourcing rules, and
forward reference, see
[`teaching/admissibility_exemplars/contract.md`](../teaching/admissibility_exemplars/contract.md).

## What this is

For each shape category surfaced by the Phase A refusal-taxonomy lane, the
operator hand-authors a small JSONL corpus of canonical exemplars.  Phase C
(contemplation runner) ingests these corpora and emits recognizer proposals;
Phase D ratifies; Phase E re-baselines GSM8K.

Phase B is the **only** phase where the engine learns from operator-authored
statements.  Every dimension of "what shape did the operator think was
canonical?" propagates into the recognizer Phase C derives and the gates
Phase D ratifies.  Therefore: canonical over comprehensive, surface
preservation over normalization, distinguishing over similar.

## Round 1 — categories and counts

The Phase A histogram (`evals/refusal_taxonomy/v1/report.json`) selected
these three categories:

| Rank | Category | Phase A count | Exemplars (this round) |
|---|---|---|---|
| 1 | `descriptive_setup_no_quantity` | 17 | 20 |
| 2 | `temporal_aggregation` | 4 | 20 |
| 3 | `rate_with_currency` | 3 | 20 |

Total: **60 hand-authored exemplars** across three files in
`teaching/admissibility_exemplars/`.

Per-category breakdown of sourcing:

| Category | Train-sample citations | Novel (operator-authored) | Edge cases |
|---|---|---|---|
| `descriptive_setup_no_quantity` | 5 | 12 | 3 |
| `temporal_aggregation` | 4 | 13 | 3 |
| `rate_with_currency` | 3 | 14 | 3 |

(Edge cases overlap with novel; counts above split them out.)

## Files

- [`teaching/admissibility_exemplars/descriptive_setup_no_quantity_v1.jsonl`](../teaching/admissibility_exemplars/descriptive_setup_no_quantity_v1.jsonl)
- [`teaching/admissibility_exemplars/temporal_aggregation_v1.jsonl`](../teaching/admissibility_exemplars/temporal_aggregation_v1.jsonl)
- [`teaching/admissibility_exemplars/rate_with_currency_v1.jsonl`](../teaching/admissibility_exemplars/rate_with_currency_v1.jsonl)
- [`teaching/admissibility_exemplars/contract.md`](../teaching/admissibility_exemplars/contract.md)

## Cross-references

- [ADR-0163 — Path to GSM8K mastery](decisions/ADR-0163-gsm8k-path-to-mastery.md)
- [Phase A refusal taxonomy contract](../evals/refusal_taxonomy/contract.md)
- [ADR-0057 — Proposal review + replay-equivalence](decisions/ADR-0057-teaching-chain-proposal-review.md)
- [ADR-0161 — HITL async queue](decisions/ADR-0161-hitl-async-queue.md)
