# AMR Decision Substrate Demo

This demo is robotics-adjacent, not a robotics stack.

It uses simulated abstract situation records to show CORE as a decision and
accountability substrate around a bounded AMR-style proceed / stop / refuse
choice. The inputs are not camera, LiDAR, odometry, SLAM, localization, motor,
or fleet-control data.

What is real CORE here:

- `ChatRuntime`
- `CognitiveTurnPipeline.run(...)`
- recognition-side typed refusal propagation
- `CognitiveTurnResult.trace_hash`
- CORE Trace Protocol canonical JSONL events
- `verify_chain(...)` replay validation

What is simulated:

- the AMR situation record
- the tiny policy reducer that maps already-abstracted facts to
  `PROCEED`, `STOP`, or `REFUSE`

The demo refuses under-determined input instead of guessing. It also runs the
same scenarios twice through fresh runtime instances and asserts byte-identical
trace JSONL.

Run from the repository root:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/core-amr-decision-uv uv run python demos/amr_decision_substrate/run_demo.py
```

Artifacts are written to:

```text
demos/amr_decision_substrate/out/
```

The important artifact is `summary.json`; `trace_a.jsonl` and `trace_b.jsonl`
are the two replay runs that must match byte-for-byte.
