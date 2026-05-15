# CORE Agent Instructions for Claude

Read this before modifying the repository.  CORE is a deterministic cognitive
engine under construction, not a transformer wrapper, not a generic chatbot, and
not an infrastructure playground.

## End Goal

CORE should become capable of:

```text
listen -> comprehend -> recall -> think -> articulate -> learn from reviewed correction -> replay deterministically
```

The working design is now:

```text
CognitiveTurnPipeline
  -> intent classification
  -> PropositionGraph
  -> ArticulationTarget
  -> deterministic realizer
  -> generation walk telemetry
  -> reviewed teaching loop
  -> deterministic trace hash
```

The system should become more capable by strengthening this path, not by adding
opaque LLM fallbacks, stochastic sampling, hidden normalization, or broad
infrastructure.

## Philosophical Stance

Truth is coherent.  Preserve coherence in algebra, memory, articulation, and
teaching.  Identity, truthfulness, and replayability are architectural
commitments, not soft prompt preferences.

Code and tests should make illegal states difficult to represent.  Prefer
inspectable state, provenance, and deterministic replay over impressive-looking
but ungrounded outputs.

## Non-Negotiable Field Invariant

Every runtime field state `F` must satisfy:

```text
versor_condition(F) < 1e-6
```

Do not weaken this threshold to make tests pass.  Fix the operator/construction
boundary that violated it.

## Normalization Rules

Allowed sites:

- `ingest/gate.py` for raw input injection.
- `language_packs/compiler.py` and vocabulary construction.
- `algebra/versor.py` for algebra-owned sandwich closure.

Forbidden sites:

- `generate/stream.py`
- `field/propagate.py`
- `vault/store.py`
- logging/telemetry/runtime shell code

Do not add drift repair, grade projection, watchdogs, timers, hot-path
normalizers, or monitoring functions whose only purpose is to repair another
function.

CGA null vectors are not unit versors.  Preserve null vectors as null vectors.

## Core Primitives

Field transition:

```text
versor_apply(V, F) = V * F * reverse(V)
```

Metric/recall:

```text
cga_inner(X, Y)
```

Do not add cosine similarity, HNSW, ANN indexes, or approximate recall to the
runtime path.  Vault recall is exact and deterministic.

## Current Key Modules

- `core/cognition/pipeline.py` — cognitive turn spine.
- `core/cognition/result.py` — result object for pipeline evidence.
- `core/cognition/trace.py` — deterministic trace hashing.
- `chat/runtime.py` — user-facing runtime contract.
- `generate/intent.py` — deterministic intent classification.
- `generate/graph_planner.py` — proposition graph and articulation target planning.
- `generate/realizer.py` and `generate/templates.py` — deterministic surface realization.
- `teaching/correction.py`, `teaching/review.py`, `teaching/store.py` — reviewed teaching loop.
- `language_packs/data/en_core_cognition_v1` — core cognition semantic seed pack.
- `docs/runtime_contracts.md` — response, telemetry, memory, identity, and testing contracts.

## Runtime Surface Contract

Keep these distinct:

- `surface`: selected user-facing response.
- `walk_surface`: raw manifold/token-walk evidence.
- `articulation_surface`: proposition/realizer surface.

Current policy:

```text
surface = articulation_surface
walk_surface = retained telemetry/evidence
```

Any change must update `docs/runtime_contracts.md` and contract tests in the
same PR.

## Teaching Safety

Learning must be reviewed and auditable.

- Session memory may be immediate.
- Reviewed memory must go through `teaching/*`.
- Pack mutation is proposal-only until reviewed.
- Identity override attempts are rejected.
- User text must not mutate identity axes, runtime policy, or operator code.

Do not create a parallel correction/learning path.

## Semantic Pack Discipline

Prefer compact, curated packs.  Do not bulk-ingest corpora into runtime.
`en_core_cognition_v1` supplies thought vocabulary, operations, and relation
predicates.  Extend it cautiously, with deterministic ordering and pack tests.

Manifest checksums must hash the bytes actually written to disk:

```python
checksum = hashlib.sha256(Path(lexicon_path).read_bytes()).hexdigest()
```

## Validation Through CLI

Use CLI lanes instead of ad hoc pytest fragments:

```bash
core test --suite smoke -q
core test --suite cognition -q
core test --suite teaching -q
core test --suite packs -q
core test --suite runtime -q
core test --suite algebra -q
core test --suite full -q
```

Run the smallest relevant suite first, then `full` before merge when practical.

## Work Sequencing

Current near-term sequence:

1. Keep CLI lanes green.
2. Integrate semantic seed relations into realizer/cognition quality.
3. Add cognitive eval harness.
4. Add deterministic operator calibration from replay evidence.
5. Expand curriculum teaching after the loop is stable.

Avoid broad docs-first churn, dashboard work, or large infrastructure unless it
unlocks one of these steps.

## PR Checklist

Before opening or merging, answer:

```text
What capability did this add or protect?
Which invariant proves the field remains valid?
Which CLI suite proves the lane?
Did this avoid hidden normalization, stochastic fallback, and unreviewed mutation?
```

Prefer small, load-bearing PRs with clear evidence.
