# Refusal Taxonomy Eval Contract (ADR-0163 Phase A)

## Purpose

`refusal-taxonomy` is a read-only evaluation lane that categorises refused
GSM8K statements by *statement shape*, not by content.  The histogram it
emits is the load-bearing measurement that gates Phase B of ADR-0163: the
top categories by count become the input list for hand-authored exemplar
corpora.

Phase A produces no recognizers and no corpus changes.  Its sole job is to
turn a flat refusal list into a measured distribution of shapes so the
operator can choose what to teach next.

## Source of truth

The v1 case set is derived from:

```
evals/gsm8k_math/train_sample/v1/report.json
```

— every record whose `verdict == "refused"`, with the embedded statement
extracted out of the `reason` envelope.  The case set is rebuilt
deterministically by `scripts/build_refusal_taxonomy_cases.py`; the
script's output is sorted by `case_id` and committed to
`evals/refusal_taxonomy/public/v1/cases.jsonl` (the framework-standard
public-split location).  The Phase A v1 report artifact lives at
`evals/refusal_taxonomy/v1/report.json`.

## Non-goals

This lane MUST NOT:

- mutate any corpus, pack, or language pack
- write to `engine_state`
- create, accept, or reject proposals
- call an LLM, embedding model, or any learned classifier
- alter the GSM8K refusal counts elsewhere in the repo

The lane only reads its own `cases.jsonl` (or an operator-supplied
refused-case set) and emits a histogram.

## Categorizer doctrine

Per ADR-0163 §Constraint #4 and CLAUDE.md, the categorizer is rules-only:

- No LLM call, no embedding, no learned model.
- Deterministic — the output is a pure function of the input string.
- No hidden normalization — lowercasing/padding is only for substring
  word-boundary safety; the original statement is never mutated for
  downstream consumers.
- First-match-wins.  Priority order is fixed in `shape_categories.py`.
- `UNCATEGORIZED` is a first-class outcome.  It is honest measurement,
  not a failure.

Adding a new category requires citing ≥ 3 refused statements as evidence
in the category's docstring.  This is enforced by `tests/test_refusal_taxonomy_lane.py`.

## Shape categories (v1)

The nine baseline categories named in ADR-0163 §Phase A, plus
`uncategorized`:

| Category | Definition |
|---|---|
| `nested_question_target` | "If X, how many/much Y …?" |
| `unit_partition` | hyphenated unit, e.g. "25-foot sections" |
| `rate_with_currency` | `$N` + per-unit framing (per hour, /kg, for one cup) |
| `comparative_with_unit` | "more than", "twice as", "N times", "as many as" |
| `fractional_rate_of_change` | fraction or `%` paired with a change-of-state verb |
| `indefinite_quantity` | "some", "several", "a few", "many", "any" |
| `temporal_aggregation` | "each day", "every X", "in N minutes", day-of-week enumeration |
| `conditional_quantity` | bare "If X, would/will Y" without a `how`-target |
| `descriptive_setup_no_quantity` | no digit, no number-word, no quantifier |
| `uncategorized` | none of the above |

## Case set schema

Each line in `cases.jsonl` is a JSON object:

```json
{"case_id": "gsm8k-train-sample-v1-NNNN",
 "statement": "<the refused statement>",
 "refusal_reason": "candidate_graph: no admissible candidate for ..."}
```

## Lane output

`run_lane(cases)` returns a `LaneReport` with:

```python
metrics = {
    "total": <int>,
    "by_category": {category_value: count, ...},     # every category present
    "uncategorized": <int>,
    "categorized_rate": <float in [0, 1]>,
    "case_digest": <sha256 of canonical case_details>,
}
case_details = [
    {"case_id", "statement", "shape_category", "refusal_reason"},
    ...
]
```

The histogram includes every category from `SHAPE_CATEGORY_ORDER` — counts
of zero are reported explicitly, not omitted.

## Replay & determinism

For a fixed `cases.jsonl` at a fixed commit SHA, `run_lane` returns the
same metrics and case_details bit-for-bit.  `case_digest` is a sha256 over
the canonical-JSON serialization of `case_details` and acts as a single
integrity hash for downstream tooling.

## ADR compatibility

This lane preserves:

- ADR-0163 Phase A boundary — measurement only, no corpus mutation
- ADR-0114a `wrong = 0` invariant — the lane scores shape, not
  correctness, so the GSM8K and capability-axis `wrong` counts elsewhere
  in the repo are unaffected
- CLAUDE.md non-negotiables — no hidden normalization, no LLM fallback,
  deterministic replay
