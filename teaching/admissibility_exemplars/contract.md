# Admissibility Exemplars Contract (ADR-0163 Phase B)

## Purpose

`teaching/admissibility_exemplars/` holds operator-authored exemplar corpora for
refusal shape categories surfaced by the Phase A refusal-taxonomy lane.

Each exemplar is a **seed**, not a sample.  Phase C (contemplation runner) will
ingest these files as a candidate source and derive `DerivedRecognizer`
proposals that generalize the shape.  The seeds must therefore be the cleanest,
most canonical instances of their shape — ambiguous seeds produce ambiguous
recognizers.

See [ADR-0163 §Phase B](../../docs/decisions/ADR-0163-gsm8k-path-to-mastery.md)
for the contract this file implements.

## Round 1 — categories

The Phase A histogram (`evals/refusal_taxonomy/v1/report.json`) surfaced this
distribution:

```
descriptive_setup_no_quantity  17  <- selected (rank 1)
uncategorized                  14
temporal_aggregation            4  <- selected (rank 2)
rate_with_currency              3  <- selected (rank 3, operator pick)
comparative_with_unit           3
fractional_rate_of_change       3
indefinite_quantity             3
nested_question_target          2
unit_partition                  1
conditional_quantity            0
```

`rate_with_currency` was selected over the other three-count categories
(`comparative_with_unit`, `fractional_rate_of_change`, `indefinite_quantity`)
by operator decision: GSM8K is heavy on money/rate framings and the lift
compounds with `temporal_aggregation` (per-time-unit framings).

`uncategorized` is intentionally not addressed in round 1 — Phase B writes
exemplars for *named* shapes; the uncategorized tail is the next-round work
once a categorizer rule surfaces what shape these statements actually carry.

## Exemplar schema

Each line in a `*.jsonl` file is a JSON object:

```json
{
  "exemplar_id": "<category>-v1-<NNNN>",
  "shape_category": "<value from ShapeCategory enum>",
  "statement": "<the natural-language sentence>",
  "expected_graph": {
    "subject": "<canonical subject lemma or null>",
    "quantity_anchors": [ ... ],
    "graph_intent": "<setup|measurement|comparison|rate|aggregate|null>",
    "outcome": "<admissible|inadmissible_by_design>"
  },
  "provenance": {
    "source": "phase_b_seed",
    "author": "<author name>",
    "round": 1,
    "category_rank": <1|2|3>,
    "train_case_id": "<optional — gsm8k-train-sample-v1-NNNN when verbatim>",
    "author_note": "<optional — uncertainties flagged for operator review>"
  }
}
```

`shape_category` MUST be a valid member of `ShapeCategory` in
`evals/refusal_taxonomy/shape_categories.py`, and it MUST equal the category
this file is named for.

## Per-category `quantity_anchors` schema

### `descriptive_setup_no_quantity`

```json
"quantity_anchors": []
"graph_intent": "setup"
"outcome": "inadmissible_by_design"
```

These statements have no extractable quantity.  Phase C's recognizer will
produce a *setup admission* verdict for them — they are context that should be
admitted as setup-only, not refused outright.

### `temporal_aggregation`

```json
"quantity_anchors": [
  {
    "kind": "event_count_per_window",
    "count_token": "<numeric or word-form token>",
    "window_unit": "<day|week|month|year|hour|minute|second>",
    "window_quantifier": "<each|every|per>",
    "subject_role": "<who/what the events apply to>"
  },
  ...
]
"graph_intent": "aggregate"
"outcome": "admissible"
```

Multiple anchors may appear when a statement enumerates several events (e.g.,
day-of-week enumeration).

### `rate_with_currency`

```json
"quantity_anchors": [
  {
    "kind": "currency_per_unit_rate",
    "currency_symbol": "<$|£|€|¥>",
    "amount": "<numeric token>",
    "amount_kind": "<integer|decimal|word>",
    "per_unit": "<hour|day|week|month|year|kg|lb|cup|item|...>",
    "subject_role": "<who is paid / what is sold>"
  }
]
"graph_intent": "rate"
"outcome": "admissible"
```

## Sourcing rules

For each category, the corpus MUST satisfy:

- **At least 3 verbatim train-sample citations.**  These cite a real
  `case_id` from `evals/gsm8k_math/train_sample/v1/report.json` via the
  `provenance.train_case_id` field.  The statement string MUST equal the
  refused statement in that case verbatim — no normalization, no punctuation
  edits, no contraction expansion.
- **At least 12 operator-authored novel statements** that instantiate the
  shape canonically and were not mined from GSM8K.
- **At least 2 edge cases** that exercise the shape's boundary (alternative
  surface forms, threshold-of-rule instances, currency variants).
- **No duplicate statements** within a file.
- **No statement shared across files** — every statement belongs to exactly
  one category.

## Disjointness and category fidelity

Every exemplar MUST belong unambiguously to its named category, where
"unambiguously" is operationalized as: `categorize(statement)` from
`evals/refusal_taxonomy/shape_categories.py` returns the file's category.

This is not enforced by tests in this PR (the categorizer is a coarser
rules-only filter than the recognizer Phase C will derive), but it is the
authoring guideline that produces clean seeds.  Where a statement could
plausibly belong to a different category, it is excluded from this corpus.

## Determinism

Each `*.jsonl` file is sorted by `exemplar_id` (lexicographic) and committed
in that order.  Lines have no trailing whitespace and a single trailing
newline.  The file is byte-stable across re-sorts.

## Holdout / split discipline

Train-sample citations come only from
`evals/gsm8k_math/train_sample/v1/report.json` (the 50-case sample).  The
public, holdout, and full GSM8K splits MUST NOT be mined for exemplars —
doing so would tune against the benchmark we are honestly measuring.

## Forward reference — Phase C

Phase C will:

1. Read each `*_v1.jsonl` as a candidate source alongside
   `teaching/discovery/discovery_candidates.jsonl`.
2. Decompose statements into recognizer patterns.
3. Emit `DerivedRecognizer` proposals to
   `teaching/proposals/proposals.jsonl` via the standard ADR-0057 path.
4. Surface the proposals in the HITL queue (ADR-0161) for operator review.

Phase B ships inputs only.  No recognizer logic, no proposal logging, no
runtime change lands with this corpus.
