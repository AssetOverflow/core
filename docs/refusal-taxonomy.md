# Refusal Taxonomy — ADR-0163 Phase A

The refusal-taxonomy lane categorises every refused GSM8K statement by
*statement shape*, not by content.  It is the load-bearing measurement
that gates Phase B of [ADR-0163](decisions/ADR-0163-gsm8k-path-to-mastery.md):
the top categories by count become the operator's input list for
hand-authored exemplar corpora.

The lane is **read-only**.  It does not mutate the active corpus, packs,
language packs, or proposal log.  The categorizer is rules-only — no LLM
call, no embedding, no learned classifier — per ADR-0163 §Constraint #4
and CLAUDE.md.

## v1 histogram (50-case GSM8K train sample)

| Count | Category |
|------:|----------|
| 17 | `descriptive_setup_no_quantity` |
| 14 | `uncategorized` |
|  4 | `temporal_aggregation` |
|  3 | `rate_with_currency` |
|  3 | `fractional_rate_of_change` |
|  3 | `indefinite_quantity` |
|  3 | `comparative_with_unit` |
|  2 | `nested_question_target` |
|  1 | `unit_partition` |
|  0 | `conditional_quantity` |

Total: 50.  Uncategorized rate: 28%.  Categorized rate: 72%.

Case digest: `d030f826cb0f4088771d90c52c8be2ff75054ab27c7d47eae8dbfe1225b2eea1`.

## Top three by count (Phase B candidates)

1. **`descriptive_setup_no_quantity` (17)** — statements with no
   extractable measurement at all.  The candidate-graph needs to admit
   pure-context lines as setup rather than refusing them.
2. **`temporal_aggregation` (4)** — repeated/aggregated time framing
   ("each day", "every other day for 2 weeks", "in 5 minutes",
   day-of-week enumeration).
3. **Tie at 3** — `rate_with_currency`, `fractional_rate_of_change`,
   `indefinite_quantity`, `comparative_with_unit`.  The operator
   selects which member of the tie (or combination) to seed in Phase
   B's first round; the agent does not make that call.

ADR-0163 §Phase B ratchet is "three categories per round".  The 17/4
spread suggests Round 1 should anchor on
`descriptive_setup_no_quantity` plus two of the tied trio.

## Reading the uncategorized tail (14)

`uncategorized` is honest measurement, not failure.  The 14 statements
that no rule fires for share these emergent sub-shapes (not yet promoted
to first-class categories — none has ≥ 3 instances individually):

- **bare declarative quantity** — "Nicole collected 400 Pokemon cards."
  / "A school has 100 students." / "Malcolm has 240 followers on
  Instagram and 500 followers on Facebook."
- **distributive** — "each saved up $40" / "each weighing 5 ounces"
- **sequential change** — "had 20 paperclips initially, lost 12"
- **word-number enumeration** — "Two puppies, two kittens, and three
  parakeets" / "a hundred ladies"
- **percentage-rate without change verb** — "10% simple interest"
- **quantity embedded in narrative** — "3 friends at the end of summer"
  / "lose 10 pounds by June"

The operator decides whether any of these warrant promotion to a
first-class category in v2 of the taxonomy (each promotion requires
≥ 3 cited refused statements per ADR-0163 §Risks).

## How to re-run

```bash
# Run via the eval framework (uses the standard public/v1/cases.jsonl)
uv run core eval refusal_taxonomy

# Run via the teaching CLI on an arbitrary refused-case set
uv run core teaching refusal-taxonomy \
    --input evals/gsm8k_math/train_sample/v1/report.json

# Regenerate the v1 cases.jsonl from the source GSM8K report
uv run python scripts/build_refusal_taxonomy_cases.py
```

## Phase A boundary (what this lane does NOT do)

- It does not add or modify recognizers.
- It does not author exemplar corpora (that is Phase B).
- It does not emit recognizer proposals (that is Phase C).
- It does not change the GSM8K `correct/refused/wrong` counts.  Per
  ADR-0114a, the `wrong = 0` invariant on G1..G5 and S1 is unchanged
  by this work.
