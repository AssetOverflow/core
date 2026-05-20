# realizer-guard holdout

## What it measures

The C1/C2 articulation safety boundary at the realizer:

- **Synthetic illegal candidates** must be rejected directly by
  `generate.realizer_guard.check_surface`.  The two patterns pinned
  today:
  - `R2_aux_neg_requires_verb`: "Right does not thought." — aux+neg
    construction without a finite verb.
  - `R3_be_neg_requires_predicate`: "Light is not reveal." — `is not`
    construction without a noun/adjective predicate.
- **Former runtime-bug prompts** (the confirmation-tag set that
  surfaced the original illegal articulation: "Light reveals truth,
  right?" / "no?" / "yes?", plus knowledge/light variations) must
  now produce accepted propositional surfaces when routed through
  `CognitiveTurnPipeline`, because C1+C2 fixes the upstream input
  shape before it reaches the realizer.

The cluster is reached by **priming** the vault with three
pack-known DEFINITION prompts first ("What is light?" / "Define
knowledge." / "What is truth?").  Without the priming, a fresh
runtime on the bug prompt alone routes to the stub path and never
exposes the original failure.  The eval is genuine only when the
prime → bug-prompt sequence reproduces the historical conditions.

## Why it matters (structural win)

A grammar guard fired in production *after* the realizer would be
defense-in-depth dressed up as a safety claim — by then the
illegal articulation has already been composed.  The C1/C2 work
moved the fix **upstream** to the input shape, so the realizer
never has to produce the illegal surface in the first place.

This eval pins both halves: the guard still rejects synthetic
illegal candidates (defense-in-depth intact) AND the previously-
failing runtime prompts now produce legal articulations
(upstream fix verified).  Either half regressing without the
other is a load-bearing failure signal.

## How to run

```bash
core eval realizer_guard
# or
python -m evals.realizer_guard.run_holdout
```

Exit code 0 iff `all_claims_supported` is true.

## How to read the output

JSON to stdout with shape:

```json
{
  "all_claims_supported": true,
  "synthetic_illegal_candidates": [
    { "surface": "Right does not thought.",
      "rule": "R2_aux_neg_requires_verb",
      "guard_fired": true,
      "passed": true }
  ],
  "runtime_bug_prompts": [
    { "prompt": "Light reveals truth, right?",
      "surface": "Yes — light reveals truth. pack-grounded (...).",
      "guard_fired_on_runtime_surface": false,
      "is_propositional": true,
      "passed": true }
  ]
}
```

## Pass criteria

| Property | Threshold | Current |
|----------|-----------|---------|
| every synthetic illegal candidate triggers `check_surface` rejection on the exact named rule | 100% | ✅ |
| every former-bug runtime prompt produces a propositional surface (no guard rejection) | 100% | ✅ |
| `all_claims_supported` is true (logical AND of both halves) | true | ✅ |

## When it has failed and why

- **Pre-C1 baseline** — bug prompts like "Light reveals truth,
  right?" produced surfaces that triggered the realizer guard
  *after* composition, which masked the upstream issue as a
  "guard catch" rather than a malformed input.
- **C1.5 (ADR-0075)** — moved guard checks to the input shape
  boundary; bug-set surfaces now compose legally.

## Runner

`evals/realizer_guard/run_holdout.py` — invoked by `core eval
realizer_guard`.  Uses `evals._parallel.run_cases_parallel` for
worker support.
