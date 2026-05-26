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

The original Phase A histogram (pre-round-2-extension) selected these three
categories:

| Rank | Category | Phase A count | Exemplars |
|---|---|---|---|
| 1 | `descriptive_setup_no_quantity` | 17 | 20 |
| 2 | `temporal_aggregation` | 4 | 20 |
| 3 | `rate_with_currency` | 3 | 20 |

Round 1 sourcing breakdown:

| Category | Train-sample citations | Novel (operator-authored) | Edge cases |
|---|---|---|---|
| `descriptive_setup_no_quantity` | 5 | 12 | 3 |
| `temporal_aggregation` | 4 | 13 | 3 |
| `rate_with_currency` | 3 | 14 | 3 |

## Round 2 — categories and counts

Round 2 was driven by categorizing the post-#304 GSM8K `train_sample`
still-refused 47 set: 23 had been UNCATEGORIZED under the round-1
categorizer; the categorization sweep surfaced three coherent
sub-shapes, plus five ratified-but-unmatched temporal cases that called
for a v2 widening.

| Rank | Category | Phase A round-2 count (public 50) | Exemplars |
|---|---|---|---|
| — | `discrete_count_statement` (new) | 10 | 20 |
| — | `multiplicative_aggregation` (new) | 2 | 20 |
| — | `currency_amount` (new) | 1 | 20 |
| — | `temporal_aggregation` v2 (widening) | — | 10 |

The "Phase A round-2 count" column is the number of the public 50-case
sample now categorized into the new category by the extended Phase A
categorizer; it is the empirical signal the categorization actually
worked.  Pre-round-2 the public sample carried 14 UNCATEGORIZED cases;
post-round-2 only 1 remains (case 0044, "10% simple interest" with no
change verb — an honest residual outside the three sub-shapes).

Round 2 sourcing breakdown:

| Category | Train-sample citations | Novel (operator-authored) | Edge cases |
|---|---|---|---|
| `discrete_count_statement` | 6 | 11 | 3 |
| `multiplicative_aggregation` | 3 | 13 | 4 |
| `currency_amount` | 3 | 14 | 3 |
| `temporal_aggregation` v2 | 4 | 5 | 1 |

## Files

Round 1:

- [`teaching/admissibility_exemplars/descriptive_setup_no_quantity_v1.jsonl`](../teaching/admissibility_exemplars/descriptive_setup_no_quantity_v1.jsonl)
- [`teaching/admissibility_exemplars/temporal_aggregation_v1.jsonl`](../teaching/admissibility_exemplars/temporal_aggregation_v1.jsonl)
- [`teaching/admissibility_exemplars/rate_with_currency_v1.jsonl`](../teaching/admissibility_exemplars/rate_with_currency_v1.jsonl)

Round 2:

- [`teaching/admissibility_exemplars/discrete_count_statement_v1.jsonl`](../teaching/admissibility_exemplars/discrete_count_statement_v1.jsonl)
- [`teaching/admissibility_exemplars/multiplicative_aggregation_v1.jsonl`](../teaching/admissibility_exemplars/multiplicative_aggregation_v1.jsonl)
- [`teaching/admissibility_exemplars/currency_amount_v1.jsonl`](../teaching/admissibility_exemplars/currency_amount_v1.jsonl)
- [`teaching/admissibility_exemplars/temporal_aggregation_v2.jsonl`](../teaching/admissibility_exemplars/temporal_aggregation_v2.jsonl)

Contract:

- [`teaching/admissibility_exemplars/contract.md`](../teaching/admissibility_exemplars/contract.md)

## Cross-references

- [ADR-0163 — Path to GSM8K mastery](decisions/ADR-0163-gsm8k-path-to-mastery.md)
- [Phase A refusal taxonomy contract](../evals/refusal_taxonomy/contract.md)
- [ADR-0057 — Proposal review + replay-equivalence](decisions/ADR-0057-teaching-chain-proposal-review.md)
- [ADR-0161 — HITL async queue](decisions/ADR-0161-hitl-async-queue.md)
