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
- `evals/*`
- `calibration/*`
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

## Efficiency and Performance

Treat performance as part of the architecture.  Slow feedback causes poor
engineering decisions and hides regressions.

When touching hot paths, prefer:

- backend-dispatched algebra when semantics match
- import hoisting and removal of repeated structure-building
- deterministic immutable caches or safe copied data
- exact CGA batching/vectorization instead of approximate search
- small validation lanes and bounded eval cases for iterative work

Do not improve speed by weakening invariants, skipping construction checks,
adding hot-path repair, using approximate recall, or mutating shared cached state
unsafely.

## Security and Trust Boundaries

When touching user-controlled text, dynamic imports, filesystem paths, CLI
reports, pack validators, or logs, enforce and test the trust boundary.

Required defaults:

- arbitrary-code execution must be explicit and opt-in
- unsafe pack IDs and path traversal must be rejected
- raw user text should not be leaked in expanded logging unless local/debug is explicit
- pack mutations stay proposal-only unless a reviewed path applies them
- report/file writes must be bounded to caller-specified paths with clear behavior

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

Before starting any task, run the startup guard to ensure a fresh base:

```bash
source scripts/agent_startup.sh
# For PR-resume tasks: CODEX_ALLOW_NON_MAIN_BASE=1 source scripts/agent_startup.sh
```

Then use CLI suites to validate your work:

```bash
core test --suite smoke -q
core test --suite cognition -q
core test --suite teaching -q
core test --suite packs -q
core test --suite runtime -q
core test --suite algebra -q
core test --suite full -q
core eval cognition
```

For a feature PR, run the smallest relevant suite and then `full` when
practical.

## Current Work Sequence

1. Keep CLI lanes and `core eval cognition` green.
2. Tighten hot-path backend consistency and semantics-preserving performance.
3. Harden pack/OOV/logging trust boundaries.
4. Add exact vault recall indexing/batching without approximate search.
5. Add Rust backend parity only after Python semantics are locked by tests.
6. Expand curriculum teaching after replay/eval/calibration remain deterministic.

## PR Standard

Every change should state:

```text
Capability/performance/security boundary added or protected:
Invariant protected:
CLI suite/eval run:
No hidden normalization / stochastic fallback / approximate recall / unreviewed mutation:
Trust boundary enforced when relevant:
```

Prefer small PRs.  Do not combine baseline repair, feature work, and broad
reorganization unless unavoidable.
