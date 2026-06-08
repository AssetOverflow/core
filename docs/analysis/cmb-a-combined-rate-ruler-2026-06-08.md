# CMB-a — combined-rate setup ruler (model + gold + oracle)

**As of:** CMB-a, on `main` + `feat/cmb-a-combined-rate-oracle`.

CMB-a is the first rung of the combined-rate ladder. It claims **exactly one thing**: *the
combined-rate setup ruler is defined and gold-valid.* No reader (CMB-c), no solver (CMB-b), no
router/contemplation wiring (CMB-d) — and therefore **no capability claim yet**.

Combined rate is a new semantic object, not single-rate with a bigger parser: two explicit rates
over one shared unit, combined by an explicit mode, then single-rate algebra over the result —

```text
effective_rate = rate_a + rate_b   (sum        — cooperation: "working together")
effective_rate = rate_a - rate_b   (difference — opposing flow: "fills ... drains")
quantity = effective_rate × time | time = quantity ÷ effective_rate | effective_rate
```

so it gets its own organ (`generate/combined_rate_comprehension/`) and its own ruler
(`evals/combined_rate_oracle/`), deliberately **not** folded into `rate_comprehension`. If the rate
organs converge later, a shared rate algebra can be extracted then (the local `RateUnit` copy is
the seam).

## Lane state
- combined-rate gold **17 / 17 valid** — **6 solved** (the full `combine_mode × query` grid),
  **4 solver_refuses**, **7 reader_refuses**.
- R1 **7/0/3** · R2 **10/0/0** · R3 gold **13/13** / reader **9/0/4** — all unchanged.
- router-organ-hygiene invariant **green** · off-serving (imports no `generate.derivation` /
  `core.reliability_gate`, AST-checked) · GSM8K serving **unchanged**.

```bash
.venv/bin/python -m evals.combined_rate_oracle          # 17/17 valid
.venv/bin/python -m pytest tests/test_combined_rate_oracle.py -q   # 25 passed
```

## Model — `CombinedRateProblem`

Two rates are **always known** (that is what makes it combined-rate); `rate_unit` is the single
unit slot for both (so two different units is a *reader* refusal, not representable). The query
selects the unknown:

| query | known | unknown |
|---|---|---|
| `quantity` | `time` | `quantity` |
| `time` | `quantity` | `time` |
| `effective_rate` | — | both `time` and `quantity` |

`effective_rate` is a derived property and **may be `<= 0`** for `difference` (`rate_a <= rate_b`);
the model does **not** refuse that — a non-positive net rate is the *solver's* boundary
(`non_positive_net_rate`, CMB-b), not a malformed setup.

## The 2×2 domain-entry grid (load-bearing for CMB-c/d hygiene)

Domain entry is **two-dimensional** (rate-count × combination cue), not cue-gated:

| | combination cue | no cue |
|---|---|---|
| **two rates** | solved (sum/difference) | `combine_mode_ambiguous` |
| **one rate** | `missing_second_rate` | `not_combined_rate_shaped` |

Two rates alone make it CMB's domain even with no cue (→ `combine_mode_ambiguous`, a substantive
refusal). A single rate needs a combination cue to be CMB's *substantive* domain
(`missing_second_rate`); without one it is single-rate R3 territory and CMB must step aside with
`not_combined_rate_shaped` (→ the `input_shape` family, the router-organ-hygiene invariant). This
is the CMB analogue of R3.1's `missing_rate`-only-when-duration-present fix.

## Closed taxonomies

- `combine_mode ∈ {sum, difference}`; `query ∈ {quantity, time, effective_rate}`.
- **solver_reasons**: `non_positive_net_rate`, `non_integer_solution`.
- **reader_reasons**: `rate_unit_mismatch`, `combine_mode_ambiguous`, `missing_second_rate`,
  `three_or_more_rates`, `reciprocal_work_rate_deferred`, `clock_interval_deferred`,
  `not_combined_rate_shaped`.

## The validator is non-vacuous (adversarial-verification finding)

A 5-lens adversarial pass (independent recompute, hygiene-boundary refutation, model/signature
holes, proof-obligation rigor, forward wrong=0 hazards) + an adjudicator returned **`fix_first`**.
The real hazard: the first-draft `validate_fixture` accepted *any* fixture labelled
`solver_refuses` regardless of the arithmetic — a positive net rate (`5−2=3`) labelled
`non_positive_net_rate`, or a `quantity` query (always integral) labelled `non_integer_solution`,
would have been certified as valid gold and fed a wrong target to CMB-b. That is precisely the
"schema obligation that can't meaningfully fail = decoration, not proof" case CLAUDE.md forbids
(and the **solved** branch had the identical latent hole: a wrong `gold` with a self-consistent
answer key).

**Fix:** a single canonical-outcome reference (`_canonical_outcome`) inside the oracle now
validates *both* the solved gold and the solver_refuses reason against the real arithmetic — a
mislabelled or arithmetically-impossible fixture is rejected (`solver_refuses_is_actually_solvable`
/ `solver_reason_mismatch:…` / `gold_does_not_match_computed_answer`). Each new branch has a
dedicated meaningful-fail test.

> **Scope note (surfaced deliberately):** the slice was scoped "oracle = canonical structure, not
> solving." Computing the canonical answer *purely to validate gold coherence* is slightly more
> than structure-only — but the meaningful-fail doctrine is a hard CLAUDE.md invariant, and a ruler
> that cannot check its own gold is decoration. `_canonical_outcome` is **not** a runtime solver
> (that is CMB-b) and does not touch reader-independence (which lives in text→setup, CMB-c).

Two coverage fixtures were also added for the `eff<0` (`cmb-07b`) and `eff=0/time` (`cmb-07c`,
which would otherwise divide by zero) cells, the dead determinism self-comparison was removed, and
three uncovered validator branches got dedicated tests.

> **Sibling follow-up (noted, not fixed here):** R3's `evals/rate_oracle` has the *same* latent
> vacuity — its `solver_refuses` branch does not cross-check `non_integer_solution` against the
> arithmetic. A later PR should port `_canonical_outcome`-style validation to the R3 oracle.

## CMB ladder

```text
CMB-a (this slice)  model + gold + setup oracle           "the ruler is defined and gold-valid"
CMB-b               exact solver (effective_rate algebra, int-or-refuse)
CMB-c               reader (prose -> CombinedRateProblem | Refusal), graded by this oracle
CMB-d               router/contemplation wiring + failure-family update (hygiene proven)
CMB-e              capability ledger entry
```

## Deferred (named)

`reciprocal` work-rate (`1/(1/a + 1/b)`), 3+ rates, mixed-unit combined rates (cross with R3.2 time
conversion), clock intervals, relative speed with opposite directions — each has a `reader_reason`
in the ruler so it refuses cleanly until built.
