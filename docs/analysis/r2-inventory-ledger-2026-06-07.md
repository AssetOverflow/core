# R2 finite-integer constraint-compiler inventory ledger

**As of:** R2 C5–C9 (reader landed), on `main @ 0e6a7f9a` + `feat/r2-constraint-setup-compiler`
**Lane state:**
- R2 reader (setup): **10 setup_correct / 0 setup_wrong / 0 missed** + **3 correct reader-refusals**
- R2 answers: **7 solved / 0 wrong** + **3 solver-refused** + **3 reader-refused**
- R2 gold validation: **13 / 13 valid**
- R1 unchanged: **7 / 0 / 3** · 15-case **15 / 0 / 0**

This is the R2 twin of the R1 ledger: a decision artifact recording exactly which constraint
families the off-serving organ now *reads, solves, and verifies*, which it *refuses*, and the
gate protecting each. R2 is disjoint from the GSM8K serving path (imports no
`generate.derivation` / `core.reliability_gate`), so none of this moves the sealed serving
metric. See ADR-0217 for the contract (renumbered from 0211 — see that ADR's header).

## Reproduce

```bash
.venv/bin/python -m evals.constraint_oracle           # gold validation -> 13/13 valid
.venv/bin/python -m evals.constraint_oracle reader    # reader grading  -> setup_wrong 0
.venv/bin/python -m pytest tests/test_constraint_reader.py tests/test_constraint_solver.py \
    tests/test_answer_choices.py tests/test_constraint_oracle.py \
    tests/test_constraint_comprehension_model.py -q
```

## The pipeline (per the north star)

```text
prose -> read_constraint_problem -> ConstraintProblem -> solve (Cramer, exact int) -> answer
      -> verify_answer_choice (tie to one option / flag a wrong key)
```

Four independent gates, each wired to fail loudly (the wrong=0 boundary):

| Gate | Module | Refuses |
|---|---|---|
| reader | `generate/constraint_comprehension/reader.py` | `too_many_categories`, `missing_total_count`, `missing_weighted_total` (+ defensive `coefficient_unit_mismatch`, `query_target_not_a_category`) |
| setup oracle | `evals/constraint_oracle/signature.py` | any drift in unknowns/facts/constraints/query vs gold ⇒ `setup_wrong` |
| solver | `generate/constraint_comprehension/solver.py` | `indistinguishable_weights`, `non_integer_solution`, `negative_solution`, `verification_failed` |
| answer-choice | `generate/answer_choices/verify.py` | `no_matching_option`, `ambiguous_options`, `unknown_provided_label`; flags `contradiction` |

## Per-fixture ledger (13 fixtures)

| Fixture | Family | Reader (setup) | Solver | Answer |
|---|---|---|---|---|
| `r2-001-buses` | buses / seats | ✅ correct | `large=4` | C ✅ |
| `r2-002-chickens` | animals / legs | ✅ correct | `chicken=11` | A ✅ |
| `r2-003-tickets` | tickets / price | ✅ correct | `adult=20` | B ✅ |
| `r2-004-coins` | coins / value | ✅ correct | `dime=9` | A ✅ |
| `r2-005-boxes` | boxes / capacity | ✅ correct | `large=4` | A ✅ |
| `r2-006-vehicles` | vehicles / wheels | ✅ correct | `car=6` | B ✅ |
| `r2-007-pens` | tools / price | ✅ correct | `pen=9` | B ✅ |
| `r2-008-negative` | buses / seats | ✅ correct | ⛔ `negative_solution` | — |
| `r2-009-non-integer` | items / price | ✅ correct | ⛔ `non_integer_solution` | — |
| `r2-010-indistinguishable` | vehicles / wheels | ✅ correct | ⛔ `indistinguishable_weights` | — |
| `r2-011-missing-total-count` | (incomplete) | ⛔ `missing_total_count` | — | — |
| `r2-012-missing-weighted-total` | (incomplete) | ⛔ `missing_weighted_total` | — | — |
| `r2-013-too-many-categories` | (ambiguous) | ⛔ `too_many_categories` | — | — |

**Key reconciliation:** the three `solver_refuses` fixtures (008–010) read **setup_correct** —
the reader's job is the *setup*, not solvability. Equal coefficients (010) are not a reader
refusal; they are the solver's `indistinguishable_weights`. So the reader reads all ten
well-formed setups and the solver owns the three unsolvable ones. This is the load-bearing
division of labor that keeps the reader's wrong=0 boundary clean.

## Covered families (the near-term milestone)

The six two-category count/weight families the user named are all read → solved → verified
with `setup_wrong = 0`, `answer_wrong = 0`, and answer-key contradictions flaggable:

```text
bus / seat        chicken / leg      ticket / price
coin / value      box / capacity     vehicle / wheel   (+ tool / price)
```

## Deferred to R3 (NOT in this batch — see ADR-0217 §2)

- ≥3 categories, inequalities, multi-step / mixed constraints, distractor exclusion,
  rates / unit conversion.
- The **typed contemplation loop + reviewed-failure learning** (plan Phases 6–7). When built,
  the failure-learning half routes through the existing `teaching/*` proposal-only flywheel
  (ADR-0055/0056/0057) — never a parallel correction path.
- Generalization to **real** GSM8K constraint prose (this gold is curated synthetic v1; the
  reader recognizes structural patterns, not fixed strings, but real-corpus validation is R3).

## Decision and trajectory

R2 v1 is the off-serving finite-integer two-category constraint setup compiler, complete on
the C0–C9 ladder. It is a meaningful capability leap (constraint *systems*, not relational
arithmetic) built on the same disciplined ladder as R1 — gold → setup oracle → solver →
answer verifier → reader — and it earns each family only where the gold + oracle + refusal
tests already license it. No guessed math, no silent correction, no answer without a proven
setup. Next axis (a later batch): R3 / the typed contemplation + reviewed-failure-learning
bridge to the L11 flywheel.
