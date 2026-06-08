# R3 single-rate inventory ledger (v1)

**As of:** R3 slice-1 (single-rate organ), branch `feat/r3-single-rate` off `main @ a00e87b2`.
**Lane state:**
- R3 reader (setup): **8 setup_correct / 0 setup_wrong / 0 missed** + **4 correct reader-refusals**
- R3 answers: **6 solved / 0 wrong** + **2 solver-refused** + **4 reader-refused** → **6 / 0 / 6**
- R3 gold validation: **12 / 12 valid**
- R1 unchanged **7/0/3** · R2 unchanged **10/0/3** · serving unchanged

R3 v1 supports **explicit single-rate integer problems with exact compound-unit composition** —
nothing more. It is a fresh off-serving organ (`generate/rate_comprehension/`,
`evals/rate_oracle/`) that introduces the genuinely new R3 substrate: **compound units**.

## Reproduce
```bash
.venv/bin/python -m evals.rate_oracle           # gold validation -> 12/12 valid
.venv/bin/python -m evals.rate_oracle reader    # reader grading  -> setup_wrong 0
.venv/bin/python -m pytest tests/test_rate_units.py tests/test_rate_oracle.py \
    tests/test_rate_solver.py tests/test_rate_reader.py -q
```

## The new substrate: compound-unit algebra (R3a)
`mile/hour` is `quantity / time`. The three single-rate operations verify composition, and a
non-composing op **refuses** (the wrong=0 dimensional gate):
```text
rate × time      -> quantity   (mile/hour × hour = mile)   [time must be the rate denominator]
quantity ÷ time  -> rate       (mile ÷ hour = mile/hour)
quantity ÷ rate  -> time       (mile ÷ mile/hour = hour)   [quantity must be the rate numerator]
```

## Per-fixture ledger (12 fixtures)

| Fixture | Family | Reader | Solver | Answer |
|---|---|---|---|---|
| `r3-01-distance` | quantity = rate×time | ✅ | `180` | C ✅ |
| `r3-02-earnings` | quantity (dollars) | ✅ | `120` | A ✅ |
| `r3-03-widgets` | quantity (2 sentences) | ✅ | `60` | B ✅ |
| `r3-04-items` | quantity (per-box denom) | ✅ | `48` | B ✅ |
| `r3-05-speed` | rate = quantity÷time | ✅ | `60` | B ✅ |
| `r3-06-runtime` | time = quantity÷rate | ✅ | `5` | A ✅ |
| `r3-07-non-integer-rate` | inverse | ✅ | ⛔ `non_integer_solution` | — |
| `r3-08-non-integer-time` | inverse | ✅ | ⛔ `non_integer_solution` | — |
| `r3-09-unit-mismatch` | minutes vs /hour | ⛔ `rate_unit_mismatch` | — | — |
| `r3-10-missing-time` | underdetermined | ⛔ `missing_time` | — | — |
| `r3-11-combined-rates` | two rates | ⛔ `combined_rates` | — | — |
| `r3-12-temporal-state` | clock time | ⛔ `temporal_state` | — | — |

The two `solver_refuses` fixtures read **setup_correct** (the setup is valid; the inverse just
has no integer solution) — the reader owns the setup, the solver owns solvability, same division
of labor as R2.

## Covered (v1) and deferred (R3.2 / R3.3)
**Covered:** distance/speed/time, earnings/wage/hours, widgets/rate/minutes, items/rate/boxes —
forward + both inverses, exact integer, exact compound-unit composition.

**Deferred (refused now, named for later):** combined/multi-rate (`combined_rates`), elapsed
clock-time (`temporal_state`), unit conversion (minutes→hours; refused as `rate_unit_mismatch` —
v1 never converts), work-rate merging, schedules, relative speed, acceleration. These are R3.2/R3.3.

## Failure-family wiring (R3e)
The N4 registry makes `unsupported_rate_duration` **reachable and precise**, applying the same
anti-over-proposing discipline as the N6 fix:

- **Growth surface (`proposal_allowed = true`) — `unsupported_rate_duration`:** `rate_unit_mismatch`
  + `combined_rates`. Both are emitted ONLY after a rate clause is recognized, so they are
  always rate-like — a proposal targets a genuine future rate feature (unit conversion / multi-rate),
  never arbitrary text.
- **Correct boundaries (`must_remain_refused`, no proposal):** `missing_rate` / `missing_time` /
  `missing_quantity` (underdetermined → `rate_underdetermined`); `temporal_state` (the clock-marker
  detector can fire on non-rate text, so it is NOT a safe growth surface →
  `unsupported_temporal_state`, boundary).
- Non-rate text remains `input_shape` (`query_target_unrecognized` / `no_query`).

## Decision
R3 v1 is the off-serving single-rate compound-unit organ, complete on the R3a→R3e ladder, with
`setup_wrong = 0` / `answer_wrong = 0`. Claim narrowly: **R3 v1 supports explicit single-rate
integer problems with exact compound-unit composition.** Next: R3.2 (combined rates / simple
unit conversion) once the dimensional substrate proves stable.
