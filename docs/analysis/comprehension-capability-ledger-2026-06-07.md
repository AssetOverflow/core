# Comprehension capability ledger (N1)

**As of:** merged `main @ 51b4a6e3` (R2 batch #624–#627 merged).

This ledger answers, for the merged baseline, exactly six questions — so the contemplation
loop (N2–N6) never mistakes a faithful refusal for a missing capability:

```text
What can CORE currently read?      -> §2, §4 (admitted families)
What can it solve?                 -> §4 (R2 solver) + §2 (R1 answer lane)
What does it refuse?               -> §3, §5 (remaining refusals)
Which refusals are correct boundaries?   -> §6 (must_remain_refused = yes)
Which refusals are growth surfaces?      -> §6 (proposal_allowed = yes)
Which organ owns each refusal?           -> §6 (owner)
```

> **The load-bearing distinction, repeated on purpose:** `correct refusal ≠ missing
> capability`. A refusal that is the wrong=0 boundary working (a pronoun with no referent, a
> system with no integer solution) must **stay refused**. The learning loop may only propose
> against refusals that are genuine coverage gaps (§6). N4 encodes this per-family; N5 emits
> proposals *only* for `proposal_allowed = true` rows.

## 1. Merged baseline (verified on merged main)

- R1 setup **7 / 0 / 3** · R1 answers **7 / 0 / 3** · 15-case **15 / 0 / 0**
- R2 reader **10 setup_correct / 0 setup_wrong / 3 refused** · R2 gold **13 / 13 valid**
  (7 solved + 3 solver-refused + 3 reader-refused)
- Serving **unchanged** (every PR's pinned-lane SHA check green)

Two independent, off-serving setup compilers now exist with typed success/refusal states —
enough substrate for a disciplined "think again" loop without LLM-style handwaving.

## 2. R1 admitted families (`generate/quantitative_comprehension.py`)

Relational single-quantity arithmetic, graded by `evals/setup_oracle` + the independent
`evals/relational_metric` oracle. **7 families:** fact; more/fewer-than; times-as-many;
half-as-many (exact divide); multi-step chain; aggregate-then-divide partition; additive
aggregate-query; narrow inverse (base of a more/fewer-than). All compute exact integer answers.
Detail: `r1-inventory-ledger-2026-06-07.md`.

## 3. R1 remaining refusals (all correct wrong=0 boundaries)

`r1-08` pronoun (no grounded referent) · `r1-09` ungrounded base (no grounded fact) · `r1-10`
distractor (compound clause the `X has N unit` template cannot parse). Each must stay refused;
admitting any would breach wrong=0. None is a coverage gap.

## 4. R2 admitted families (`generate/constraint_comprehension/`)

Two-category finite-integer count/weight systems: read → exact Cramer solve → answer-choice
verify (with contradiction flagging). **6 families:** buses/seats, animals/legs, tickets/price,
coins/value, boxes/capacity, vehicles/wheels. Detail: `r2-inventory-ledger-2026-06-07.md`, ADR-0217.

## 5. R2 remaining refusals

- **Reader (gold-backed):** `too_many_categories` (>2), `missing_total_count`,
  `missing_weighted_total`. Defensive (constructed-test): `coefficient_unit_mismatch`,
  `coefficient_conflict`, `category_pair_not_found`, `query_target_not_a_category`.
- **Solver:** `indistinguishable_weights`, `non_integer_solution`, `negative_solution`,
  `verification_failed`.
- **Answer-choice:** `no_matching_option`, `ambiguous_options`, `unknown_provided_label`,
  `unparseable_option`, `no_options`; plus the `contradiction` **verdict** (not a refusal).

## 6. Cross-organ refusal taxonomy draft (formalized by N4)

First-pass mapping of the full refusal surface to the failure-family vocabulary, with
`must_remain_refused` (correct boundary) and `proposal_allowed` (growth surface) and `owner`.
N4 turns this into the executable registry; N5 emits proposals **only** for `proposal_allowed`.

| Family | Evidenced by | owner | must_remain_refused | proposal_allowed |
|---|---|---|---|---|
| `ambiguous_referent` | R1 pronoun `unreadable_quantity_clause` | r1 | **yes** | no (needs entity-resolution design) |
| `ungrounded_base` | R1 `unit_unbound`, `no_single_quantity_query` | r1 | **yes** | no |
| `unsupported_distractor_clause` | R1 `r1-10` `unreadable_quantity_clause` | r1 | **yes** | no (until same-unit target isolation) |
| `unit_incompatible` | R1 `unit_mismatch`, R2 `coefficient_unit_mismatch` | cross | **yes** | no |
| `unsupported_system_size` | R2 `too_many_categories` | r2 | **yes** | no (until ≥3-var solver, R3) |
| `missing_category_pair` | *(reserved — `category_pair_not_found` is too broad; see note)* | r2 | no | **yes** (reserved) |
| `missing_attribute_coefficient` | *(reserved — no emitter yet)* | r2 | no | **yes** |
| `missing_total_count` | R2 `missing_total_count` | r2 | no | **yes** (propose count-constraint fixture) |
| `missing_weighted_total` | R2 `missing_weighted_total` | r2 | no | **yes** (propose weighted-total fixture) |
| `indistinguishable_weights` | R2 solver | r2 | **yes** | no |
| `non_integer_solution` | R2 solver | r2 | **yes** | no |
| `negative_solution` | R2 solver | r2 | **yes** | no |
| `answer_key_contradiction` | R2 answer-choice `contradiction` verdict | r2 | n/a | no — **action: report contradiction** |
| `input_shape` | R1 `non_digit_quantity`/`non_identifier_name`/`no_quantity_template`/`unprojectable`; R2 `query_target_not_a_category`/`category_pair_not_found` | cross | **yes** | no |

> **N6 correction (boundary-first + precise growth).** `category_pair_not_found` fires on *any*
> non-R2 text (0 or 1 categories), so it is **not** a safe growth trigger — it maps to
> `input_shape` ("R2 does not recognize this"), and `missing_category_pair` is reserved until the
> reader distinguishes a partial one-category R2 problem from non-R2 prose. Only the **precise**
> R2 gaps (`missing_total_count`, `missing_weighted_total` — reachable only after two categories +
> matching coefficients are read) remain reachable growth surfaces. The contemplation pass (N6)
> classifies **boundary-first** and treats `input_shape` as non-blocking, so a problem one organ
> recognizes as a substantive boundary never proposes against the other organ's broad refusal.

**Reserved (forward-declared, no current emitter):** `missing_category_pair`,
`missing_attribute_coefficient`, `unsupported_rate_duration`, `unsupported_temporal_state` — named
so the registry is complete, but not reachable until the reader/R3 supplies a precise signal.

## 7. Next contemplation batch (N2–N6)

```text
N2  core/comprehension_attempt/   typed ComprehensionAttempt (organ + outcome + refusal_reason + family + signature + evidence)
N3  setup router                  try R1 then R2; exactly-one setup_correct -> use; else typed refusal
N4  failure-family registry       executable form of §6 (must_remain_refused / proposal_allowed / owner)
N5  proposal-only emitter         teaching/proposals/comprehension_failures/<content_hash>.json — never mounted
N6  generate/contemplation/ v0    single bounded pass chain: route -> classify -> terminal -> maybe emit
```

## 8. Non-claims / boundaries

- This is **not** a new capability batch. R1/R2 capability is unchanged; N2–N6 add a *growth
  organ*, not new math.
- `setup_wrong` / `answer_wrong` stay **0**; serving stays unchanged.
- **No self-modification.** The loop's terminal action is at most a *proposal-only* artifact.
  It cannot ratify, mount, alter a reader, or modify tests except by a human-reviewed PR.
  The alignment is `failure → classification → proposal → review → ratification`, never
  `failure → self-patch`. (CLAUDE.md teaching-safety; ADR-0055/0056/0057.)
- R2 generalization to real GSM8K prose remains **R3**, not claimed here.
