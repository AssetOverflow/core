# Warmed-Session Consistency Eval Lane — Contract

**Lane:** `warmed_session_consistency`
**Version:** v1
**Created:** 2026-05-19

## What this lane measures

Pipeline / runtime / telemetry surface consistency across a *warmed*
session — i.e. a single `CognitiveTurnPipeline` running multiple turns
through the same `ChatRuntime`, where vault state, prior-turn context,
and session-level memory accumulate.

This is the asymmetric counterpart to `cold_start_grounding`.  Cold
start measures routing on fresh runtimes.  Warmed session measures
whether accumulated state, pipeline overrides, or telemetry-vs-final-
result drift can corrupt an answer that was correctly grounded at the
runtime level.

The 2026-05-19 design review surfaced the bug this lane pins:

> first pipeline run:  truth - pack-grounded (...).
> second pipeline run: Truth is defined as ...
> second walk:         Truth infer.
> runtime turn log:    Truth infer.

The pipeline's `realized_plan.surface` overrode a perfectly good
runtime-level pack-grounded surface with a `<pending>`-rendered
placeholder.  Telemetry recorded yet a third surface.

## Scoring rubric

Each case runs **N turns** through one `CognitiveTurnPipeline` /
`ChatRuntime` pair.  After every turn the lane checks:

| Signal | Definition |
|---|---|
| `no_placeholder`        | surface contains none of: `...`, `<pending>`, `<prior>`, ` placeholder ` |
| `pipeline_match_telemetry` | `result.surface` equals the surface in the most recent `runtime.turn_log` entry |
| `pipeline_match_walk`   | `result.surface` is either equal to `result.walk_surface` (when the pipeline did not override) OR is the realized-plan output (when it did and the override was a *useful* surface) |
| `grounded_holds_on_warm` | a turn that grounded as `pack`/`teaching` on turn 1 must not regress to `none`/`vault`/walk-fragment on subsequent turns *for the same prompt* |

Lane-level metrics (rates over all (case × turn) pairs):

| Metric | Definition | v1 pass threshold |
|---|---|---|
| `no_placeholder_rate`         | fraction of turns whose surface contains no placeholder | 1.00 |
| `telemetry_consistency_rate`  | fraction of turns where pipeline-final == turn_log-emitted | 1.00 |
| `warm_grounding_stability`    | fraction of replayed prompts whose grounding_source is byte-identical across all replays | >= 0.95 |

`no_placeholder_rate` and `telemetry_consistency_rate` are hard 1.00
because either failure is a doctrine violation, not a tunable metric.

## Why cold-start alone is not enough

`cold_start_grounding` constructs a fresh `ChatRuntime` per case to
isolate routing logic.  That is correct for what it measures.  But it
hides every bug class that requires accumulated state:

- pipeline overriding a good runtime surface with a worse realizer one
- telemetry emitting a surface that doesn't match the final pipeline
  return value
- vault accumulation winning over pack grounding on later turns
- correction-pass injecting a backward perturbation that mis-attributes
  to the wrong turn

The warmed-session lane runs these exact paths and asserts they hold.

## Cold-start invariant — INVERTED here

Unlike `cold_start_grounding`, this lane DOES NOT construct a fresh
runtime per case.  Each case explicitly carries a *turn sequence*; the
runner constructs one runtime and one pipeline, then plays the
sequence through them.  Each turn's expected behavior may reference
prior-turn state (e.g. "after a CORRECTION on turn 2, turn 3's surface
must still ground correctly on a fresh DEFINITION prompt").

## Case schema

```jsonl
{
  "id": "warm_replay_truth_001",
  "category": "pipeline_override_no_placeholder",
  "turns": [
    {"prompt": "What is truth?", "expected_grounding_source": "pack"},
    {"prompt": "What is truth?", "expected_grounding_source": "pack"}
  ],
  "warm_invariants": ["no_placeholder", "pipeline_match_telemetry"]
}
```

Each case carries a `turns` list (ordered).  Optional
`warm_invariants` names the subset of contract checks to enforce on
this case (default: all four).
