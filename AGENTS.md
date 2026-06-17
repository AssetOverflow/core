# CORE Agent Instructions

This repository is building a deterministic cognitive engine, not a transformer
wrapper and not a demo chatbot.  Every agent must preserve the geometric
runtime while moving the system toward teachable cognitive chat.

## Agent-Specific Instruction Files

Different agents read a supplementary file alongside this one.  Read yours
before touching any code:

| Agent | Supplementary file | Key differences |
|---|---|---|
| **Claude** | `CLAUDE.md` | Deep context; self-restraining; read for semantic anchoring rule nuance |
| **Grok 4.3 + Grok Build** | `GROK.md` | Stateless; requires high reasoning effort; Arena/parallel subagent rules; Plan Mode preferred; skills system |
| **GPT-5.5 (o3-class)** | `GPT55.md` | Stateless; fluency cautions; extended thinking for algebra/field work |

If you are Grok 4.3 or GPT-5.5, complete the Session Start Checklist in your
file before reading anything else in this file.

## Grok 4.3 / Grok Build Hard Stops (Mastery Level)

These apply to Grok 4.3 and Grok Build in addition to every rule below:

1. **You are stateless.** Read `GROK.md` in full, `docs/runtime_contracts.md`, and the most recent `HANDOFF-*.md` (if dated within 3 days) before any edits.
2. **High reasoning effort is mandatory** for all tasks touching `algebra/`, `field/`, `generate/realizer.py`, `generate/graph_planner.py`, `generate/intent.py`, `vault/store.py`, `calibration/`, `core/cognition/`, or `teaching/`.
3. **Use Plan Mode** (Grok Build) for any non-trivial change in the above modules. Direct edits are discouraged.
4. **Skills are the preferred mechanism** for repeated protocols. Use `/core-bootstrap`, `/versor-coherence-guardian`, `/pre-edit-sweep`, and `/claim-proposal-guardian` (or their auto-triggered versions).
5. **Sweep before you edit.** Use tool-call chains to trace imports and call sites.
6. **Write a handoff doc at session end** using `docs/handoff_template.md`.
7. **Arena / parallel subagents:** each subagent independently satisfies `||F * reverse(F) - 1||_F < 1e-6` before reporting. Reconcile results before any merge. No mutable state sharing.

---

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
- `evals/*` — deterministic cognition evidence harness.
- `calibration/*` — bounded replay-based operator calibration.
- `docs/runtime_contracts.md` — runtime response, memory, identity, and testing contracts.

## Efficiency and Performance Doctrine

Performance is an architectural property.  Do not treat it as an afterthought
that will be cleaned up after features land.

Before modifying hot paths, identify whether the change touches:

- algebra backend dispatch (`algebra/backend.py`)
- versor application / closure (`algebra/versor.py`)
- propagation (`field/propagate.py`)
- injection / OOV grounding (`ingest/gate.py`)
- vault recall/storage (`vault/store.py`)
- session turn loop (`session/context.py`)
- runtime/eval loops (`chat/runtime.py`, `core/cognition/*`, `evals/*`)

Required approach:

1. Prefer semantics-preserving cleanup before new knobs.
2. Route hot-path algebra through `algebra.backend` when semantics are identical.
3. Hoist repeated imports and repeated structure-building out of tight loops.
4. Cache only deterministic, immutable, or safely copied structures.
5. Keep exact CGA recall exact; optimize scans with batching/vectorization, not approximation.
6. Prove speed-oriented changes through existing CLI lanes and, when practical, small benchmark/eval evidence.

Never improve speed by:

- weakening `versor_condition` thresholds

- skipping closure checks at construction boundaries
- adding hot-path repair/normalization
- replacing exact CGA with cosine/ANN/HNSW
- hiding failures behind retry loops without telemetry
- mutating shared cached state unsafely

For test speed, prefer better validation lanes, small-case eval tests, fixture reuse where safe, and pack/load caching with immutability guarantees.  Do not delete meaningful tests just because the full suite is slow.

## Security and Trust-Boundary Doctrine

Every agent must identify user-controlled input and dynamic execution surfaces.
Security hardening should be built into the same PRs that touch those surfaces.

High-risk surfaces:

- `core pack validate` dynamic validator execution
- language/source pack loading
- OOV token grounding and logs
- CLI commands that echo user input
- report/eval output paths
- pack mutation proposals
- any future file/network/database integration

Required approach:

1. Make arbitrary-code execution explicit and opt-in.
2. Reject path traversal and unsafe pack IDs before filesystem access.
3. Centralize display/log handling for user-controlled strings when expanding logging.
4. Keep pack mutation proposal-only unless an explicit reviewed path applies it.
5. Avoid leaking raw sensitive tokens in errors/reports unless the command is explicitly local/debug.
6. Preserve deterministic replay evidence for security-relevant decisions.

Do not add hidden background execution, dynamic imports from untrusted paths, shell passthroughs, or broad filesystem writes without an explicit trust boundary and tests.

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

1. Keep CLI test suites and `core eval cognition` green.
2. Tighten hot-path backend consistency and semantics-preserving performance.
3. Harden pack/OOV/logging trust boundaries.
4. Add exact vault recall indexing/batching without approximate search.
5. Add Rust backend parity only after Python semantics are locked by tests.
6. Expand curriculum teaching only after replay/eval/calibration remain deterministic.

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
core eval cognition
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
- eval/calibration determinism
- hot-path performance semantics
- explicit security trust boundaries

Bad tests preserve private helper shapes, stale constructors, punctuation trivia
outside documented contracts, or legacy behavior that contradicts the current
architecture.

## PR Standard

Every PR must answer:

```text
What cognitive capability, performance property, or security boundary did this add or protect?
What invariant proves it did not corrupt the field?
Which CLI suite/eval proves the relevant lane?
Did it avoid hidden normalization, stochastic fallback, approximate recall, and unreviewed mutation?
If it touches user input, files, dynamic imports, or logs, what trust boundary was enforced?
```

Prefer small, load-bearing PRs.  Do not mix baseline fixes, feature work, and
large reorganization unless the coupling is unavoidable.

## Architecture in One Sentence

Raw input becomes a closed versor field once; thought evolves through exact
versor transitions and CGA recall; cognition is structured as intent,
proposition graph, articulation target, deterministic realization, reviewed
memory, eval/calibration replay, and traceable evidence.
