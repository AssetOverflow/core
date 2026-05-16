# monotonic-learning eval lane

## What it measures

After teaching CORE about new domains across many cycles, competence on
previously taught domains must not regress. This tests the architectural
claim that learning is additive in CORE — new teaching extends the system
without overwriting prior competence.

This is the longitudinal counterpart to provenance: provenance proves a
single turn is grounded; monotonic-learning proves grounding *survives*
across teaching cycles.

## Why it matters (structural win)

Frontier LLMs, when fine-tuned on new domains, exhibit catastrophic
forgetting: competence on prior domains regresses as new ones are added.
This is a structural property of gradient-based weight updates over a
shared parameter pool.

CORE, by construction, adds teaching examples to a bounded append-only
store and grows the vault rather than overwriting weights. The structural
prediction: zero regression on prior domains as new ones accumulate.

## Protocol

A single longitudinal protocol per split, expressed as an ordered sequence
of operations:

```
cycle 0:        probe all domains (baseline)
cycle 1:        teach domain A; probe all
cycle 2:        teach domain A again; probe all
...
cycle N:        teach domain Z; probe all
```

Each *teaching step* is a sequence of prompts the runner feeds through
`CognitiveTurnPipeline` — typically a context prompt followed by a
correction-intent prompt, which triggers the reviewed teaching loop.

Each *probe* is a prompt with expected terms / expected intent. The probe's
pass status is recorded per cycle so we can detect regression.

## Sub-metrics

### M1. Per-domain non-regression

For every domain D and every cycle c after D was first taught, the
per-domain score at cycle c must be ≥ the score at the cycle when D was
first taught, minus a tolerance ε.

`regression(D, c) = max(score_first(D) - score(D, c), 0)`
`max_regression = max over (D, c) of regression(D, c)`

**Pass threshold:** `max_regression ≤ 0.05` (allow 5% noise floor).

### M2. Minimum competence floor

After all teaching cycles complete, every taught domain must score above a
floor.

`floor_score = min over domains D of score(D, final_cycle)`

**Pass threshold:** `floor_score ≥ 0.80`.

### M3. Cycle count discipline

The roadmap requires ≥10 teaching cycles. Lanes with fewer cycles are
shorter than the methodology contract allows.

**Pass threshold:** `cycle_count ≥ 10`.

## Pass thresholds (v1)

| Metric | Threshold |
|--------|-----------|
| max_regression | ≤ 0.05 |
| floor_score    | ≥ 0.80 |
| cycle_count    | ≥ 10 |
| Overall        | all three pass |

## Case format

The case file is a flat JSONL where each row is one operation in the
protocol. The runner sequences them by `cycle` and `op` fields.

```json
{"cycle": 0, "op": "probe",   "domain": "truth",    "id": "P-truth-1",
 "prompt": "What is truth?",  "expected_terms": ["truth"]}
{"cycle": 1, "op": "teach",   "domain": "truth",
 "prime": ["What is truth?"], "prompt": "Actually truth is coherent."}
{"cycle": 1, "op": "probe",   "domain": "truth",    "id": "P-truth-1",
 "prompt": "What is truth?",  "expected_terms": ["truth"]}
```

Operations:

- `probe`: scored prompt; passes if `expected_terms` all appear in the
  articulation surface (case-insensitive).
- `teach`: a sequence of `prime` prompts followed by a `prompt` (the
  correction). Not scored; updates session + teaching store state.

## Data layout

```
evals/monotonic_learning/
  contract.md
  runner.py
  dev/cases.jsonl
  public/v1/cases.jsonl
  holdouts/v1/cases.jsonl
  results/
```
