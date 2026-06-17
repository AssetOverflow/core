# GSM8K post-Gate-A1 frontier microscope lookback

**Date:** 2026-06-17
**Branch:** `docs/gsm8k-post-gate-a1-frontier-microscope`
**Main merge anchor:** `bb083004` (PR #805 Gate A1 implementation)
**Tool:** `scripts/gsm8k_post_gate_a1_frontier_microscope.py`
**Scope:** docs/tooling only — no runtime, no `report.json` rebaseline, no implementation ratification

## Purpose

After Inc3 (#799/#801) and Gate A1 (#803/#805), the injector frontiers for
`rate_with_currency` and `comparative_with_unit` are closed. Aggregate
train_sample proxy remains **6/44/0** with **wrong=0**. This lookback runs a
deterministic live microscope over ephemeral `build_report(cases)` to name the
**exact remaining refusal taxonomy** and nominate the next **ratification
candidate** (not an implementation decision).

## Gate naming (fixed)

| Name | Meaning |
|---|---|
| **Gate A2 (roadmap)** | Partition / chunking family |
| **Gate A2a** | Narrow ratification candidate within Gate A2: unit partition / chunking primitive |
| **Gate A1b / Comparative-A2** | Additive comparative (`compare_additive`) — **not** roadmap Gate A2 |

## Measurement method

```bash
PYTHONPATH=. .venv/bin/python scripts/gsm8k_post_gate_a1_frontier_microscope.py
```

- Reads `evals/gsm8k_math/train_sample/v1/cases.jsonl` (50 cases)
- Builds ephemeral report via `evals.gsm8k_math.train_sample.v1.runner.build_report`
- **Does not write** `evals/gsm8k_math/train_sample/v1/report.json`
- Emits aggregate buckets plus a **44-row `refusal_table`** with per-case blocking layer,
  candidate primitive, expected movement, and evidence snippet

Pinned artifact unchanged: `report.json` stays Inc1-era **6/44/0**.

## Live counts (ephemeral main @ bb083004)

| Metric | Value |
|---|---:|
| correct | 6 |
| refused | 44 |
| wrong | 0 |
| `rate_with_currency` no-injection | **0** |
| `comparative_with_unit` no-injection | **0** |
| total `recognized_no_injection` | 31 |

### Aggregate buckets (summary)

| Top bucket | Count |
|---|---:|
| `recognized_no_injection` | 31 |
| `no_admissible_statement` | 7 |
| `no_admissible_question` | 5 |
| `no_solvable_branch` | 1 |

**`recognized_no_injection` by category:** `discrete_count_statement` 19,
`descriptive_setup_no_quantity` 4, `currency_amount` 3, `multiplicative_aggregation` 3,
`temporal_aggregation` 2

**DCS subfamilies (19):** `dcs_composition_wall` 14, `dcs_misroute_fraction_change` 2,
`dcs_misroute_unit_partition` 1 (**0002**), `dcs_misroute_comparative_multiplicative` 1 (0033),
`dcs_misroute_comparative_additive` 1 (0016)

**Expected movement histogram:** `diagnostic_only` 25, `downstream_reclassification` 19,
`correct_lift` 0 (none nominated — composition/multi-step dominates)

## Case-level refusal table (all 44 refused cases)

Full per-case `reason` strings are in the JSON `refusal_table` emitted by the microscope.
Truncated reasons shown here for doc readability.

| case_id | verdict | top bucket | subfamily | recognizer cat | blocking layer | next primitive | movement | evidence | reason (truncated) |
|---|---|---|---|---|---|---|---|---|---|
| 0001 | refused | recognized_no_injection | no_injection_temporal_aggregation | temporal_aggregation | recognizer_injector | temporal_tariff | diagnostic_only | If she works more than 8 hours per shift, she is eligible for overtime, which is paid by your... | candidate_graph: recognizer matched but produced no injection for sta... |
| 0002 | refused | recognized_no_injection | dcs_misroute_unit_partition | discrete_count_statement | recognizer_injector | unit_partition | downstream_reclassification | She splits it up into 25-foot sections. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0003 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | The local bookstore donated 48 boxes of erasers. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0004 | refused | no_admissible_statement | nested_fraction_partition | — | statement_parser | fraction_partition | diagnostic_only | Half of the kids are going to soccer camp, and 1/4 of the kids going to soccer camp are going... | candidate_graph: no admissible candidate for statement: 'Half of the ... |
| 0005 | refused | no_admissible_statement | affine_equation_fraction_target | — | statement_parser | fractional_delta | diagnostic_only | In one hour, Addison mountain's temperature will decrease to 3/4 of its temperature. | candidate_graph: no admissible candidate for statement: "In one hour,... |
| 0006 | refused | recognized_no_injection | no_injection_multiplicative_aggregation | multiplicative_aggregation | recognizer_injector | multiplicative_aggregate | diagnostic_only | Mandy started reading books with only 8 pages when she was 6 years old. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0007 | refused | no_admissible_question | inverse_residual_more | — | question_parser | inverse_residual_question | downstream_reclassification | How many more boxes do they need if Francine has a total of 85 crayons? | candidate_graph: no admissible candidate for question: 'How many more... |
| 0008 | refused | no_admissible_question | production_yield_question | — | question_parser | yield_question_frame | downstream_reclassification | If 50 beads are used to make one bracelet, how many bracelets will Marnie be able to make out... | candidate_graph: no admissible candidate for question: 'If 50 beads a... |
| 0009 | refused | no_admissible_question | conditional_aggregate_total | — | question_parser | conditional_aggregate_question | downstream_reclassification | If Jen has 150 ducks, how many total birds does she have? | candidate_graph: no admissible candidate for question: 'If Jen has 15... |
| 0010 | refused | no_admissible_statement | affine_equation_fraction_delta | — | statement_parser | affine_equation | diagnostic_only | Marion has 1/4 more than what Yun currently has, plus 7. | candidate_graph: no admissible candidate for statement: 'Marion has 1... |
| 0011 | refused | no_solvable_branch | rate_graph_unsolvable | — | graph_composition | rate_composition | downstream_reclassification | Alexa has a lemonade stand where she sells lemonade for $2 for one cup. | candidate_graph: no branch produced a solvable graph |
| 0012 | refused | recognized_no_injection | no_injection_descriptive_setup_no_quantity | descriptive_setup_no_quantity | recognizer_injector | relation_hypothesis | diagnostic_only | He put all of them in his aquarium but his fish ate half of them. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0013 | refused | recognized_no_injection | no_injection_multiplicative_aggregation | multiplicative_aggregation | recognizer_injector | multiplicative_aggregate | diagnostic_only | Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day to her channel. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0015 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | Traveling from Manhattan to the Bronx, Andrew rides the subway for 10 hours, takes the train... | candidate_graph: recognizer matched but produced no injection for sta... |
| 0016 | refused | recognized_no_injection | dcs_misroute_comparative_additive | discrete_count_statement | recognizer_injector | compare_additive | downstream_reclassification | On Rudolph's car trip across town, he traveled 2 more than 5 miles and encountered 3 less tha... | candidate_graph: recognizer matched but produced no injection for sta... |
| 0017 | refused | recognized_no_injection | no_injection_temporal_aggregation | temporal_aggregation | recognizer_injector | temporal_tariff | diagnostic_only | He's charging $50.00 per day or $500.00 for 14 days. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0019 | refused | recognized_no_injection | no_injection_currency_amount | currency_amount | recognizer_injector | currency_mutation | diagnostic_only | After the first appointment, John paid $100 for pet insurance that covers 80% of the subseque... | candidate_graph: recognizer matched but produced no injection for sta... |
| 0020 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | Two puppies, two kittens, and three parakeets were for sale at the pet shop. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0021 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | He bench presses 15 pounds for 10 reps and does 3 sets. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0022 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | She goes out fishing today and catches twice as many fish as she caught in total in the past... | candidate_graph: recognizer matched but produced no injection for sta... |
| 0023 | refused | recognized_no_injection | no_injection_descriptive_setup_no_quantity | descriptive_setup_no_quantity | recognizer_injector | relation_hypothesis | diagnostic_only | Cindy collected twice as many, and Rex collected half of Nicole and Cindy's combined total. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0025 | refused | no_admissible_question | multiplicative_peer_pick | — | question_parser | peer_partition_question | downstream_reclassification | If three of Lilibeth's friends pick the same amount as her, how many strawberries do Lilibeth... | candidate_graph: no admissible candidate for question: "If three of L... |
| 0026 | refused | no_admissible_statement | each_binding_currency | — | statement_parser | each_entity_binding | downstream_reclassification | Aaron and his brother Carson each saved up $40 to go to dinner. | candidate_graph: no admissible candidate for statement: 'Aaron and hi... |
| 0027 | refused | recognized_no_injection | no_injection_descriptive_setup_no_quantity | descriptive_setup_no_quantity | recognizer_injector | relation_hypothesis | diagnostic_only | The number of followers he has on Twitter is half the number of followers he has on Instagram... | candidate_graph: recognizer matched but produced no injection for sta... |
| 0028 | refused | recognized_no_injection | no_injection_currency_amount | currency_amount | recognizer_injector | currency_mutation | diagnostic_only | It cost $100,000 to open initially. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0030 | refused | no_admissible_statement | numeric_expression_duration | — | statement_parser | duration_multiplier | downstream_reclassification | It is a 2-hour drive each way. | candidate_graph: no admissible candidate for statement: 'It is a 2-ho... |
| 0031 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | Jeremie wants to go to an amusement park with 3 friends at the end of summer. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0032 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | He draws and colors 10 pictures. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0033 | refused | recognized_no_injection | dcs_misroute_comparative_multiplicative | discrete_count_statement | recognizer_injector | compare_multiplicative | downstream_reclassification | Rachel is 12 years old, and her grandfather is 7 times her age. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0034 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | He can run 40 yards within 5 seconds. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0035 | refused | no_admissible_question | inverse_residual_more | — | question_parser | inverse_residual_question | downstream_reclassification | How many more apples would Martha need to give away to be left with only 4 of them? | candidate_graph: no admissible candidate for question: 'How many more... |
| 0036 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | She studied for 2 hours on Wednesday and three times as long on Thursday. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0037 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | Michael wants to lose 10 pounds by June. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0039 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | Orlando gained 5 pounds. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0040 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | He now has 2 horses, 5 dogs, 7 cats, 3 turtles, and 1 goat. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0041 | refused | recognized_no_injection | dcs_misroute_fraction_change | discrete_count_statement | recognizer_injector | fraction_of_prior | diagnostic_only | The guests eat all of 1 pan, and 75% of the 2nd pan. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0043 | refused | recognized_no_injection | no_injection_currency_amount | currency_amount | recognizer_injector | currency_mutation | diagnostic_only | Her mother gave her an additional $4, and her father twice as much as her mother. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0044 | refused | recognized_no_injection | dcs_misroute_fraction_change | discrete_count_statement | recognizer_injector | fraction_of_prior | diagnostic_only | John invests in a bank and gets 10% simple interest. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0045 | refused | recognized_no_injection | no_injection_multiplicative_aggregation | multiplicative_aggregation | recognizer_injector | multiplicative_aggregate | diagnostic_only | Each survey has 10 questions. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0046 | refused | recognized_no_injection | no_injection_descriptive_setup_no_quantity | descriptive_setup_no_quantity | recognizer_injector | relation_hypothesis | diagnostic_only | Half of the students are girls, the other half are boys. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0047 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | He then packs an equal number of the macaroons in 4 different brown bags, ready for delivery. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0048 | refused | no_admissible_statement | numeric_expression_recurrence | — | statement_parser | recurrence_frame | downstream_reclassification | Every week, he gets 6 cards. | candidate_graph: no admissible candidate for statement: 'Every week, ... |
| 0049 | refused | recognized_no_injection | dcs_composition_wall | discrete_count_statement | recognizer_injector | derivation_composer | diagnostic_only | Malcolm is trying to find the fastest walk to school and is currently comparing two routes. | candidate_graph: recognizer matched but produced no injection for sta... |
| 0050 | refused | no_admissible_statement | numeric_expression_recurrence | — | statement_parser | recurrence_frame | downstream_reclassification | Mark does a gig every other day for 2 weeks. | candidate_graph: no admissible candidate for statement: 'Mark does a ... |

## Recommended next ratification candidate

**Gate A2a unit partition / chunking primitive** (within roadmap Gate A2 partition/chunking).

This is a **ratification candidate**, not an implementation decision. Implementation
follows only after a ratification doc proves a shared narrow primitive with
wrong=0 admission tests.

### Why Gate A2a (evidence)

1. **One confirmed DCS unit-partition misroute:** case **0002** — `1000 feet` split into
   `25-foot sections`, blocked at `recognizer_injector` with
   `dcs_misroute_unit_partition` → candidate primitive `unit_partition`, movement
   `downstream_reclassification`.
2. **Broader partition/chunk overlap exists but is not unified:** heuristic tag
   `partition_chunking` also touches 0003 (multiplicative product) and 0035 (inverse
   residual question); parser-layer partition-adjacent cases include 0004, 0025, 0047.
   These do **not** share one primitive yet — ratification must name what is in/out of
   Gate A2a v1.
3. **Inc3/Gate A1 precedent:** closed injector buckets first with a ratified v1 template;
   aggregate 6/44/0 unchanged; movement is reclassification visibility.

### Why this is ratification, not implementation

- Only **one** DCS misroute is confirmed for `unit_partition` on current serving code.
- Partition/chunk **candidates** appear across statement parser, question parser, and
  downstream composition buckets — implementation without ratification would smuggle
  scope (affine fractions, peer-pick questions, DCS composition wall).
- Ratification must prove a **shared narrow primitive** (total → chunk count → per-chunk
  unit) with exemplars, confusers, and wrong=0 replay before any injector/parser code.

## Not next (explicit deferrals)

| Track | Defer because |
|---|---|
| **Gate A1b / Comparative-A2 (additive comparative)** | Only one simple same-sentence DCS misroute (0016); no cluster of additive entity-comparison refusals at injector. Defer unless a future microscope pass finds ≥3 same-sentence `more than` / `less than` entity-comparison refusals with shared template. |
| **Inc4 rate denom-state** | Live rate cases refuse on overtime (0001), tariff (0017), profit/composition (0011 graph), not merely missing hour/kg/cup Initial. Downstream rate refusals = 2. Denom-state alone does not explain the frontier. |
| **Broad DCS widening** | 14/19 DCS refusals are `dcs_composition_wall` → `derivation_composer`. Forbidden without a composition-wall ratification; metric-inert injector widening risks incomplete readings under wrong=0. |
| **`report.json` rebaseline** | Separate ratified PR only; pinned artifact remains historical 6/44/0 in this PR. |

## Gate A2a ratification seed (docs only — not ratified)

**Candidate primitive names:** `unit_partition` / `partition_count` / `unitize`

**Template examples (from train_sample surfaces):**

| Surface pattern | Case hint | Notes |
|---|---|---|
| `N total-units split into M-unit sections` | 0002: 1000 feet → 25-foot sections | Canonical Gate A2a exemplar |
| `N beads per bracelet` (yield/partition question) | 0008: 50 beads → bracelets | Question-layer binding — may be out of v1 |
| `N crayons per box` / residual box count | 0007: boxes vs loose crayons | Inverse residual — likely out of v1 |

**Open design questions (must be resolved in ratification):**

1. **Output unit:** chunk count vs retained measure unit vs dual unknowns?
2. **Divisibility:** exact division required (0002: 1000/25) vs refuse non-integer chunk counts?
3. **Fractional results:** 1/4 given away + half stored (0002 full problem) — in v1 scope or composition follow-up?
4. **Source grounding:** total quantity referent vs chunk-size referent — which entity keys are grounded from the statement?
5. **Inverse direction:** “how many more boxes” (0007) — partition primitive or question-frame primitive?
6. **Downstream question binding:** per-chunk query (`how much does she keep on hand`) requires partition+remainder composition — v1 injector only or paired composition ratification?

## Tests / validation (this PR)

```bash
git diff --check origin/main...HEAD
PYTHONPATH=. .venv/bin/python -m pytest tests/test_gsm8k_post_gate_a1_frontier_microscope.py -q
PYTHONPATH=. .venv/bin/python -m pytest tests/test_gsm8k_frontier_report.py -q
.venv/bin/core test --suite smoke -q
```

## Explicit non-changes

- No Gate A2a implementation
- No Gate A1b / Comparative-A2 implementation
- No Inc4 denom-state
- No runtime / generate / solver / recognizer edits
- No `report.json` rebaseline