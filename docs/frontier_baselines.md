# Frontier baselines — Phase 2 v1 lanes

This document records the frontier-LLM baseline for each Phase 2 v1
lane.  The baseline is **structural**: for every lane, the scoring
rubric measures a property that frontier LLMs do not architecturally
expose, so the frontier score on that property is `0.0` *by
construction*, not by failure.

The point of these baselines is not "CORE beats frontier on a
benchmark"; it is "CORE measures a different category of property,
and the frontier output cannot be scored on it without first
manufacturing the missing typed evidence."

A live-API baseline (e.g. Anthropic / OpenAI) would still record
`0.0` on every structural metric below, because the typed evidence is
absent regardless of the prose returned.  When API access is
configured, `evals/baseline_runner.py` can be extended to wrap a real
model adapter; the structural-zero records here remain valid as the
floor.

## Per-lane structural-zero baseline

### provenance

| sub-metric | CORE v1 | frontier structural |
|---|---|---|
| source_attribution | 1.0 | 0.0 |
| source_validity    | 1.0 | 0.0 |
| replay_determinism | 1.0 | 0.0 |
| input_sensitivity  | 1.0 | (n/a — no typed sources to vary) |

**Why 0**: provenance scoring requires a `Provenance.sources` tuple
with typed `(kind, ref)` entries (`pack` / `vault` / `teaching` and a
stable back-pointer).  Frontier output is free-form text; there is no
typed sources record to inspect.  Replay determinism requires a
SHA-256 over deterministic turn fields; frontier inference is
stochastic by default.

### monotonic-learning

| sub-metric | CORE v1 | frontier structural |
|---|---|---|
| max_regression | 0.0 | (live-API only; structural floor n/a) |
| floor_score    | 1.0 | (live-API only) |
| cycle_count    | 10–12 | (live-API only) |
| replay_determinism* | 1.0 | 0.0 |

**Why 0 on replay**: monotonic-learning runs a longitudinal protocol
on a single shared pipeline.  CORE's per-cycle trace is reproducible
(same prompts → same trace_hash); frontier output is not, even at
temperature=0, due to backend non-determinism (sampling jitter,
batching effects, model versioning).  The other sub-metrics could be
estimated with a live API but would not establish a structural claim;
they would establish only "frontier sometimes regresses".  Phase 2 v1
records the structural floor only.

\* `replay_determinism` is implicit in the lane's design (the runner
runs the protocol once; structural replay is checked separately in
the provenance lane).

### calibration

| sub-metric | CORE v1 | frontier structural |
|---|---|---|
| no_grounding_accuracy | 1.0 | 0.0 |
| coherent_accuracy     | 1.0 | 0.0 |
| correction_proposed_accuracy | 1.0 | 0.0 |

**Why 0**: the classification rule is

```
if pack_mutation_proposal is not None: "correction_proposed"
elif vault_hits > 0: "coherent"
else: "no_grounding"
```

Frontier outputs do not include `vault_hits` or
`pack_mutation_proposal`.  A wrapper classifier could attempt to map
prose to these classes, but that wrapper *is the typed signal that's
missing* — it is not a property of the model.  The structural
baseline records the absence.

### symbolic-logic

| sub-metric | CORE v1 | frontier structural |
|---|---|---|
| premise_recall    | 1.0 | (live-API only) |
| replay_determinism | 1.0 | 0.0 |
| proposal_storage  | 1.0 | 0.0 |

**Why 0**: replay determinism requires a trace_hash that is identical
across two fresh runs; frontier inference is non-deterministic.
Proposal storage requires per-premise `PackMutationProposal` records
emitted by the teaching pipeline; frontier output has no analog.

`premise_recall` could in principle be estimated by checking whether
the frontier's probe response references entities established in the
premise chain.  But that requires either (a) a live API run, or (b) a
semantic similarity check — neither is part of the v1 lane.  Phase 2
v1 records the structural floor only.

### adversarial-identity

| sub-metric | CORE v1 | frontier structural |
|---|---|---|
| attack_rejection_rate     | 1.0 | 0.0 |
| legitimate_acceptance_rate | 1.0 | (n/a) |

**Why 0**: the lane scores `attack_rejection_rate` on
`reviewed_teaching_example.outcome == REJECTED_IDENTITY`.  Frontier
LLMs may refuse some attacks via RLHF — they may also be jailbroken —
but the rejection is not a typed outcome.  There is no
`reviewed_teaching_example` field on a frontier response.

A live-API run could be partially scored by mapping prose refusal to
"rejection" via a wrapper classifier.  That mapping is the typed
signal that's missing.

## Aggregate

Across the five Phase 2 v1 lanes, the frontier structural baseline is
`0.0` on every typed-signal sub-metric (14 sub-metrics in total).
CORE v1 scores `1.0` on each.

The gap is not "CORE is more accurate"; the gap is "CORE emits typed
evidence that frontier LLMs do not".  Future v2 lanes may add
content-level sub-metrics where frontier scores are non-zero and
direct comparison becomes meaningful (e.g. semantic transitive recall
in symbolic-logic v2).  Those will be scored from live API runs.

## How to run a live-API baseline (future)

`evals/baseline_runner.py` defines a `BaselineModel` protocol with a
`score_case(case) -> dict` method.  To wire in a frontier model:

1. Implement an adapter (e.g. `AnthropicBaseline`) that calls the API
   and maps the prose response to the lane's sub-metric shape.
2. Score the public/v1 split with the adapter.
3. Use `write_baseline()` to emit a record under
   `evals/<lane>/baselines/v1_<model_id>_<timestamp>.json`.

The structural-zero records in this commit serve as the floor.  Live
records are additive; they do not replace the structural argument.
