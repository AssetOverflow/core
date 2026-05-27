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
  -> deterministic eval/calibration replay
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
- `evals/*` — deterministic cognition eval harness.
- `calibration/*` — bounded replay-based calibration.
- `docs/runtime_contracts.md` — response, telemetry, memory, identity, and testing contracts.

## Efficiency and Performance Doctrine

Performance is part of correctness for this project because slow feedback hides
regressions and encourages unsafe shortcuts.  Do not defer obvious hot-path or
validation-lane issues until “later.”

Before changing hot paths, identify whether the change touches:

- algebra backend dispatch
- versor application / closure
- propagation
- injection / OOV grounding
- vault recall/storage
- session turn loop
- runtime/eval loops

Required approach:

1. Prefer semantics-preserving cleanup before new knobs.
2. Use `algebra.backend` for hot-path algebra when semantics are identical.
3. Hoist repeated imports and repeated structure-building out of tight loops.
4. Cache deterministic immutable data only, or return safe copies.
5. Keep exact CGA recall exact; use batching/vectorization, not approximation.
6. Validate speed-oriented changes through CLI lanes and `core eval cognition`.

Never improve speed by weakening closure thresholds, skipping construction
checks, adding hot-path repair, replacing exact CGA with approximate metrics, or
mutating shared cached state unsafely.

For test speed, prefer curated CLI lanes, small-case eval tests, safe fixture
reuse, and immutable pack/load caching.  Do not delete meaningful tests just
because the full suite is slow.

## Security and Trust Boundaries

Any change that touches user-controlled text, filesystem paths, dynamic imports,
reports, pack validators, or logs must state the trust boundary.

High-risk surfaces:

- `core pack validate` dynamic validator execution.
- language/source pack loading.
- OOV token grounding and error messages.
- CLI commands that echo user content.
- eval/report output paths.
- pack mutation proposals.
- future file/network/database integrations.

Required approach:

1. Make arbitrary-code execution explicit and opt-in.
2. Reject path traversal and unsafe pack IDs before filesystem access.
3. Centralize safe display/log handling before increasing logging.
4. Keep pack mutation proposal-only unless a reviewed path applies it.
5. Avoid leaking raw sensitive tokens unless the command is explicitly local/debug.
6. Preserve deterministic replay evidence for security-relevant decisions.

Do not add hidden background execution, dynamic imports from untrusted paths,
shell passthroughs, or broad filesystem writes without tests and a documented
trust boundary.

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

## Documentation Discipline

ADRs, session docs, audit artifacts, and handoff briefs stay as Markdown
(GitHub-flavored).  Plain-text artifacts are diffable, greppable, and
readable by every agent in the dispatch pipeline.

Within Markdown, two GitHub-rendered features are sanctioned and otherwise
sparingly used:

- Mermaid fenced blocks (` ```mermaid `) when a state machine, sequence,
  or dependency graph genuinely communicates more than prose.  Inline,
  not in a sidecar file.
- `<details>` / `<summary>` collapsibles to fold long proofs, large
  tables, or generated logs without losing single-file context.

Out of scope:

- Standalone HTML artifacts with embedded CSS / inline SVG / sidebar
  navigation.  The "open in browser" model breaks `git diff`, breaks
  determinism (CSS regen ordering, SVG element ordering), and breaks
  cross-agent legibility.
- Dashboards, status pages, or visualizers as a substitute for a
  pinned data artifact.  If a visualization is load-bearing, the
  underlying data must live in a deterministic JSON/JSONL/Markdown
  artifact first; any rendering is a read-only view of that artifact.

Diagrams go inside the doc that needs them.  Specs do not become
single-file applications.

## Schema-Defined Proof Obligations

When a schema, type, or struct exists for the sole purpose of naming a
structural property the architecture claims to hold
(``HolonomyAlignmentCase``, ``RoundTripFilter``, the various ``Result``
discriminants), the obligation is real only when an executing test can
**meaningfully fail** under the violations it is written to catch.

A test that passes under conditions that bypass the obligation it
nominally proves is decoration, not proof.  Before treating a schema
type as a verified property:

1. Identify the violations the schema is written to catch.
2. Confirm an existing test would fail if exactly one of those
   violations were silently introduced (e.g. by mutating a weight,
   skipping a step, swapping a fallback).
3. If no such test exists, the obligation is asserted but not proven —
   record the gap in a follow-up doc rather than treating the schema
   as load-bearing.

This rule generalises the wrong=0 invariant.  ``wrong == 0`` holds
because the admissibility gate, the round-trip filter, and the
multi-branch disagreement check are all wired to fail loudly when
violated.  The same discipline applies to every other "this design
guarantees X" claim in the codebase.

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
core eval cognition
```

Run the smallest relevant suite first, then `full` before merge when practical.

## Work Sequencing

Current near-term sequence:

1. Keep CLI lanes and `core eval cognition` green.
2. Tighten hot-path backend consistency and semantics-preserving performance.
3. Harden pack/OOV/logging trust boundaries.
4. Add exact vault recall indexing/batching without approximate search.
5. Add Rust backend parity only after Python semantics are locked by tests.
6. Expand curriculum teaching after replay/eval/calibration remain deterministic.

Avoid broad docs-first churn, dashboard work, or large infrastructure unless it
unlocks one of these steps.

## PR Checklist

Before opening or merging, answer:

```text
What capability, performance property, or security boundary did this add/protect?
Which invariant proves the field remains valid?
Which CLI suite/eval proves the lane?
Did this avoid hidden normalization, stochastic fallback, approximate recall, and unreviewed mutation?
If it touches user input, files, dynamic imports, or logs, what trust boundary was enforced?
```

Prefer small, load-bearing PRs with clear evidence.
