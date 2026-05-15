# CORE Agent Instructions

This repository is building a deterministic cognitive engine, not a transformer
wrapper and not a demo chatbot.  Every agent must preserve the geometric
runtime while moving the system toward teachable cognitive chat.

## North Star

CORE should become capable of:

```text
listen -> comprehend -> recall -> think -> articulate -> learn from reviewed correction -> replay deterministically
```

The current path is intentionally staged:

1. Maintain algebra/runtime invariants.
2. Use `CognitiveTurnPipeline` as the spine.
3. Classify intent and build proposition graphs.
4. Plan articulation targets and realize them deterministically.
5. Capture reviewed teaching corrections safely.
6. Seed compact semantic packs for cognition vocabulary.
7. Evaluate through CLI lanes, not ad hoc test fragments.
8. Calibrate bounded operators only from replayable evidence.

Do not skip ahead by adding opaque models, stochastic generation, or broad
infrastructure that hides whether CORE itself is improving.

## Philosophical and Architectural Stance

Truth is coherent.  CORE's work is to preserve coherent structure from input to
field state to articulation to memory.  Treat identity, truthfulness, and
replayability as architectural commitments rather than prompt preferences.

The system's intelligence should come from inspectable geometric state,
structured propositions, deterministic recall, reviewed teaching, and bounded
calibration.  Avoid nihilistic or purely statistical framing in code comments,
agent plans, and docs.  Prefer responsibility, provenance, and stable meaning.

## The Hard Field Invariant

Every runtime field state `F` must satisfy:

```text
versor_condition(F) < 1e-6
```

This is checked by `algebra/versor.py::versor_condition()`.

If a propagation path violates this invariant, fix the operator path or the
explicit algebra/construction boundary that owns the transition.  Do not hide
violations by changing tests, silently weakening thresholds, or normalizing in
hot-path modules.

## Normalization and Closure Rules

Allowed closure/construction boundaries:

- `ingest/gate.py` for raw prompt injection.
- `language_packs/compiler.py` / vocabulary construction.
- `algebra/versor.py` where algebraic sandwich output closure belongs.

Forbidden hot-path repair sites:

- `generate/stream.py`
- `field/propagate.py`
- `vault/store.py`
- runtime telemetry/logging layers

Do not add normalization, unitization, grade projection, drift monitors, repair
timers, or watchdog functions outside a documented construction/algebra boundary.
If you think you need one, an upstream operator is unclosed.

CGA null vectors are geometric points and must remain null.  Do not force null
vectors into unit-versor closure.

## The Two Core Primitives

Field transition:

```text
algebra/versor.py::versor_apply(V, F) -> V * F * reverse(V)
```

Distance/recall metric:

```text
algebra/cga.py::cga_inner(X, Y)
```

Do not add ANN, HNSW, cosine similarity, approximate nearest-neighbor recall,
or non-CGA ranking to runtime memory.  Vault recall is exact and deterministic.

## Current Runtime/Cognition Shape

The live cognitive path is now:

```text
ChatRuntime / CognitiveTurnPipeline
  -> tokenize / OOV policy / inject
  -> intent classification
  -> PropositionGraph
  -> ArticulationTarget
  -> deterministic realizer / articulation surface
  -> generation walk telemetry
  -> identity + energy telemetry
  -> reviewed teaching capture when correction intent appears
  -> deterministic trace hash
```

Important modules:

- `core/cognition/pipeline.py` — cognitive turn spine.
- `core/cognition/result.py` — canonical turn result shape.
- `core/cognition/trace.py` — deterministic trace hashing.
- `generate/intent.py` — deterministic intent classification.
- `generate/graph_planner.py` — proposition graph and articulation target planning.
- `generate/realizer.py` / `generate/templates.py` — deterministic realization.
- `teaching/*` — reviewed teaching/correction lifecycle.
- `language_packs/data/en_core_cognition_v1` — compact cognition seed pack.
- `docs/runtime_contracts.md` — runtime response, memory, identity, and testing contracts.

## Chat Surface Contract

Do not collapse these fields:

- `surface` — selected user-facing response.
- `walk_surface` — raw manifold/token-walk evidence.
- `articulation_surface` — proposition/realizer surface.

Current policy:

```text
surface = articulation_surface
walk_surface = retained telemetry/evidence
```

If this changes, update `docs/runtime_contracts.md` and contract tests in the
same PR.

## Teaching and Memory Safety

Learning is controlled mutation, not storing everything.

Rules:

- Session memory can be immediate and local.
- Reviewed memory must go through the teaching loop.
- Pack mutation is proposal-only until reviewed.
- User correction must not mutate identity axes, runtime policy, or operator code.
- Identity override attempts must be rejected, not learned.

Use the teaching modules for correction capture/review/store.  Do not invent a
parallel correction mechanism inside chat runtime or generation.

## Semantic Pack Rule

Use compact, curated semantic packs.  Do not dump broad corpora into runtime.
The core cognition seed pack is meant to provide thought vocabulary, operations,
and relation predicates, not to impersonate large-scale pretraining.

Manifest checksums must be computed from bytes actually written to disk:

```python
checksum = hashlib.sha256(Path(lexicon_path).read_bytes()).hexdigest()
```

Never compute a manifest checksum from a pre-serialization Python string.

## Development Priorities

Current capability sequence:

1. Keep CLI test suites green.
2. Integrate semantic seed surfaces into realizer/cognition quality.
3. Add cognitive eval harness.
4. Add operator calibration from deterministic replay evidence.
5. Expand curriculum teaching only after the loop remains deterministic.

Do not add dashboards, broad infra, or large test matrices unless they directly
protect or unlock one of the above capabilities.

## Test Discipline

Use the CLI lanes as the standard validation interface:

```bash
core test --suite smoke -q
core test --suite cognition -q
core test --suite teaching -q
core test --suite packs -q
core test --suite runtime -q
core test --suite algebra -q
core test --suite full -q
```

For targeted work, run the smallest relevant suite first, then `full` before
merge when practical.

Good tests protect:

- versor closure
- deterministic replay / trace hash stability
- runtime surface contracts
- exact memory/recall behavior
- identity protection
- reviewed correction safety
- semantic pack loadability and deterministic ordering

Bad tests preserve private helper shapes, stale constructors, punctuation trivia
outside documented contracts, or legacy behavior that contradicts the current
architecture.

## PR Standard

Every PR must answer:

```text
What cognitive capability did this add or protect?
What invariant proves it did not corrupt the field?
Which CLI suite proves the relevant lane?
Did it avoid hidden normalization, stochastic fallback, and unreviewed mutation?
```

Prefer small, load-bearing PRs.  Do not mix baseline fixes, feature work, and
large reorganization unless the coupling is unavoidable.

## Architecture in One Sentence

Raw input becomes a closed versor field once; thought evolves through exact
versor transitions and CGA recall; cognition is structured as intent,
proposition graph, articulation target, deterministic realization, reviewed
memory, and replayable trace.
