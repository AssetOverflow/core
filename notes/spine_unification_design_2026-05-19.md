# Cognitive-Spine Unification — Deferred RFC

**Date:** 2026-05-19
**Status:** Design proposal — NOT implemented.  Deferred from the
2026-05-19 fluency push because the change crosses public-API
entrypoints and depends on the SurfaceSelector landing.
**Companion RFC:** `notes/surface_selector_design_2026-05-19.md`

## Motivation

The 2026-05-19 design review's Finding P0 #2:

> The live cognitive spine is fragmented across public entrypoints.

| Entrypoint | Today's spine | Affected by intent fixes? | Affected by pipeline fixes? |
|---|---|---|---|
| `core chat` (REPL)        | `ChatRuntime.chat()` direct | ✓ yes | ✗ no |
| `core trace` (single turn)| `ChatRuntime.chat()` direct | ✓ yes | ✗ no |
| `core pulse` (research)   | `scripts/run_pulse.py` graph diffusion + GloVe-seeded | ✗ no | ✗ no |
| `evals/cognition/runner.py`| `CognitiveTurnPipeline.run()` | ✓ yes | ✓ yes |
| `evals/cold_start_grounding/runner.py` | `ChatRuntime.chat()` direct | ✓ yes | ✗ no |
| `evals/warmed_session_consistency/runner.py` | `CognitiveTurnPipeline.run()` | ✓ yes | ✓ yes |
| `evals/deterministic_fluency/runner.py` | `ChatRuntime.chat()` direct | ✓ yes | ✗ no |

Three separate cognitive spines exist:

1. `ChatRuntime.chat()` direct — the simplest path, used by `core chat`
   and `core trace`.
2. `CognitiveTurnPipeline.run()` — wraps `ChatRuntime.chat()` and adds
   a graph-realizer override step + transitive walk + frame compose.
3. `scripts/run_pulse.py` — independent path with GloVe seeding,
   graph constraint correction, top-k recall.

Effects of fragmentation:

- A fix to the pipeline's override behaviour does not reach the
  user via `core chat`.
- A fix to the runtime reaches the user but is masked under the
  pipeline-wrapped eval lanes.
- Pulse can "prove" capabilities the user never experiences.
- Tests can be green while user behaviour is broken (and vice versa).

## Proposed direction

### One canonical chat spine

`ChatRuntime.chat()` becomes the single canonical entrypoint.  The
pipeline's value-add (transitive walks, frame composition) moves
INSIDE the runtime as opt-in passes consulted by the selector:

```python
class ChatRuntime:
    def chat(self, text, *, max_tokens=None, mode="full"):
        # mode="full"   — runtime + pipeline-equivalent passes
        # mode="bridge" — runtime only (today's bridge path)
        # mode="walk"   — walk evidence only (research / introspection)
        ...
```

The pipeline becomes a thin convenience wrapper that selects a mode:

```python
class CognitiveTurnPipeline:
    def run(self, text, *, max_tokens=None):
        # Equivalent to ChatRuntime.chat(text, mode="full").
        # Retained as the API the cognition eval harness was built
        # against; new code calls ChatRuntime.chat() directly.
        ...
```

### Pulse demoted to research harness

`scripts/run_pulse.py` keeps existing for the geometry-research path
but is labeled non-canonical.  It does not contribute to "fluent
chat" claims; the eval lanes that rely on it (if any) are renamed.

### Single selector consumed everywhere

The SurfaceSelector (companion RFC) is the only path that emits the
user-facing surface.  All entrypoints route through it:

```
user input
  ─▶ ChatRuntime.chat(text, mode=…)
        ─▶ collect_candidates(intent, subject, field_state, mode)
        ─▶ SurfaceSelector.select(candidates, context)
        ─▶ ChatResponse(surface=chosen.surface, …)
```

`core chat`, `core trace`, every eval lane, and the pipeline shim
all call `ChatRuntime.chat()` with different modes.  One emission
point, one telemetry record, one trace hash.

## What this fixes

| Today | After |
|---|---|
| Pipeline override invisible to `core chat` | Pipeline's value-add is opt-in modes inside the runtime; visible everywhere or nowhere |
| Eval-vs-user behaviour drift | Same code path; can't drift |
| Pulse "proves" things the user doesn't see | Pulse explicitly labeled non-canonical |
| Tests asserting `r.surface == r.walk_surface` | Surface is the selector's output; walk_surface remains audit telemetry |
| Three places to add a fluency surface | One: register a SurfaceProvider |

## Sequencing

This RFC is **dependent on** `surface_selector_design_2026-05-19.md`.
Land in this order:

1. SurfaceSelector + provider registry (the companion RFC)
2. Wrap each existing dispatcher branch as a provider
3. Re-implement pipeline override as a provider (or remove if the
   selector handles it via ordering)
4. Move `core chat` to `ChatRuntime.chat(mode="full")`
5. Move `core trace` to `ChatRuntime.chat(mode="full")` with trace
   instrumentation
6. Audit eval lanes — every lane explicitly declares its mode
7. Label `scripts/run_pulse.py` as non-canonical in its docstring
   and any eval lane that depends on it

## What does NOT change

- Pack content (already correct authoring path)
- Teaching chains (already correct authoring path)
- Intent classification (already canonical via `generate.intent`)
- Telemetry schema (one emitter, one shape)
- Trace-hash stability (intra-session; hashes are still per-run)

## Risk register

- **Public API stability** — `CognitiveTurnPipeline.run()` cannot
  be removed without a deprecation cycle.  Migration step is a
  wrapper, not a removal.
- **Mode semantics** — the three modes (`full` / `bridge` / `walk`)
  must be documented in `docs/runtime_contracts.md` BEFORE the
  refactor so users can rely on them.
- **Eval invariant** — `cognition` eval expects pipeline-level
  behaviour.  The wrapper preserves that; verifiable byte-identity
  on the eval is a hard prerequisite to commit.

## When to land

After the SurfaceSelector RFC.  Spine unification without the
selector would just move the fragmentation; with the selector it
collapses the spines onto a single, observable, replayable path.
