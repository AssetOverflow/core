# calibration eval lane

## What it measures

CORE produces *distinguishable, typed* response signals for three
cognitive states, derivable deterministically from `CognitiveTurnResult`:

| Class | Reliable signal | Cognitive meaning |
|-------|-----------------|-------------------|
| `no_grounding` | `vault_hits == 0` (gate fires; the canonical "I don't have field coordinates" marker is the surface returned by the runtime) | "I have no prior context to draw on" |
| `coherent` | `vault_hits > 0` (vault recall returned at least one entry) | "I have prior context that I can recall" |
| `correction_proposed` | `result.pack_mutation_proposal is not None` (teaching loop fired) | "I am being corrected against a prior assertion" |

The structural claim under test: CORE's runtime emits typed evidence
(vault hit count + teaching proposal presence) that lets a downstream
caller distinguish three cognitive states without any heuristic or
post-hoc classifier.  These signals are stable, deterministic, and
inspectable.

## Why it matters (structural win)

Frontier LLMs return free-form prose for all three states — confident
prose when they know, equally-confident-sounding prose when they
confabulate, and prose with no structural distinction when they revise.
There is no first-class signal a caller can read.

CORE returns:

- A `ChatResponse.vault_hits` integer (0 = no recall fired, >0 = recall fired).
- A `CognitiveTurnResult.pack_mutation_proposal` object (None or a
  datestamped proposal record).
- A stable surface marker `"I don't have field coordinates for that yet."`
  whenever the ingest gate fires.

All three are produced by the runtime path itself, not by a wrapper
classifier.

## Classification rule (deterministic)

```python
def infer_class(result: CognitiveTurnResult) -> str:
    if result.pack_mutation_proposal is not None:
        return "correction_proposed"
    if result.vault_hits > 0:
        return "coherent"
    return "no_grounding"
```

## Architectural finding documented by this lane

The current ingest gate fires on a *geometric* signal — CGA inner-product
recall score below `UNKNOWN_FLOOR=0.15`.  This is **not** a clean
semantic OOD detector: morphological grounding of unknown tokens can
produce versors that geometrically resemble in-pack entries, and field
state drift across turns can produce false negatives (in-pack queries
that fail to recall in a polluted session).

See `evals/calibration/gaps.md` for the full architectural finding and
suggested follow-up work.  This v1 of the lane measures what CORE
**does** distinguish (recall presence + correction firing), not what
the long-term roadmap may want (semantic OOD detection).

## Protocol

Each case runs on its own **fresh** `CognitiveTurnPipeline` instance to
prevent cross-case state pollution.  Inter-turn field drift would make
the lane non-deterministic if cases shared a session.

Each case provides:

- `prime`: an unscored list of prompts run first to populate the vault
  (or to set up a prior surface for correction).
- `prompt`: the scored probe.
- `expected_class`: one of `no_grounding`, `coherent`, `correction_proposed`.

For `no_grounding` cases, `prime` is typically empty so the vault is
empty when the probe runs — the gate then fires for any probe.

For `coherent` cases, `prime` contains the same in-pack question(s)
repeated so the vault carries a recall-capable entry by the time the
probe runs.

For `correction_proposed` cases, `prime` is a single in-pack question;
the scored probe is a correction-intent prompt against that prior turn.

## Sub-metrics

### M1. no_grounding_accuracy
Fraction of `no_grounding` cases classified correctly.
**Pass threshold:** ≥ 0.80

### M2. coherent_accuracy
Fraction of `coherent` cases classified correctly.
**Pass threshold:** ≥ 0.80

### M3. correction_proposed_accuracy
Fraction of `correction_proposed` cases classified correctly.
**Pass threshold:** ≥ 0.80

### M4. overall_accuracy
Total correct / total cases.
**Pass threshold:** ≥ 0.80

## Pass thresholds (v1)

| Metric | Threshold |
|--------|-----------|
| no_grounding_accuracy | ≥ 0.80 |
| coherent_accuracy | ≥ 0.80 |
| correction_proposed_accuracy | ≥ 0.80 |
| overall_accuracy | ≥ 0.80 |
| Overall | all four pass |

## Case format

```json
{"id":"CAL-001","expected_class":"no_grounding","prime":[],"prompt":"What is a qubit?"}
{"id":"CAL-002","expected_class":"coherent","prime":["What is truth?","What is truth?"],"prompt":"What is truth?"}
{"id":"CAL-003","expected_class":"correction_proposed","prime":["What is truth?"],"prompt":"Actually that is not quite right."}
```

## Data layout

```
evals/calibration/
  contract.md
  gaps.md
  runner.py
  dev/cases.jsonl
  public/v1/cases.jsonl
  holdouts/v1/cases.jsonl
  results/
```
