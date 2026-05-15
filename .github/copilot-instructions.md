# CORE Agentic Coding Instructions

Use these instructions for Copilot/Codex-style repository work.

## Mission

CORE is a deterministic cognitive engine.  The near-term goal is basic
teachable cognitive chat:

```text
listen -> comprehend -> recall -> think -> articulate -> learn from reviewed correction -> replay deterministically
```

Do not treat the repository as a normal chatbot wrapper or transformer project.
Do not add hidden LLM fallbacks, stochastic generation, or broad infrastructure
that bypasses the geometric cognitive path.

## Current Architecture

The cognitive path is centered on:

- `core/cognition/pipeline.py`
- `generate/intent.py`
- `generate/graph_planner.py`
- `generate/realizer.py`
- `teaching/correction.py`, `teaching/review.py`, `teaching/store.py`
- `language_packs/data/en_core_cognition_v1`

The runtime response contract is documented in `docs/runtime_contracts.md`.
Follow it.

## Hard Invariants

Runtime field states must satisfy:

```text
versor_condition(F) < 1e-6
```

Allowed construction/closure sites:

- `ingest/gate.py`
- `language_packs/compiler.py` / vocabulary construction
- `algebra/versor.py`

Forbidden hot-path repair sites:

- `generate/stream.py`
- `field/propagate.py`
- `vault/store.py`
- telemetry/logging shell code

Do not add grade monitors, drift timers, watchdog repair functions, ANN/HNSW,
cosine similarity, or approximate recall.

## Surface Contract

Keep these separate:

- `surface`: selected user-facing response.
- `walk_surface`: raw generation/manifold evidence.
- `articulation_surface`: proposition/realizer surface.

Current policy:

```text
surface = articulation_surface
walk_surface = retained telemetry/evidence
```

## Teaching Safety

Learning is reviewed mutation:

- Session memory can be immediate.
- Reviewed memory must use `teaching/*`.
- Pack mutation is proposal-only until reviewed.
- Identity override attempts are rejected.
- User text cannot mutate identity axes, runtime policy, or operator code.

## Validation

Use CLI suites:

```bash
core test --suite smoke -q
core test --suite cognition -q
core test --suite teaching -q
core test --suite packs -q
core test --suite runtime -q
core test --suite algebra -q
core test --suite full -q
```

For a feature PR, run the smallest relevant suite and then `full` when
practical.

## PR Standard

Every change should state:

```text
Capability added/protected:
Invariant protected:
CLI suite run:
No hidden normalization / stochastic fallback / unreviewed mutation:
```

Prefer small PRs.  Do not combine baseline repair, feature work, and broad
reorganization unless unavoidable.
