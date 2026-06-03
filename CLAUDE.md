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

### GSM8K math comprehension substrate (sealed; serving `6/44/0`, wrong=0 — moves only via ratified PRs)

- `core/reliability_gate/` — calibrated-learning ledger + gate (ADR-0175): `ClassTally` counts, `conservative_floor` (one-sided Wilson, N_MIN=10), θ ceilings.
- `generate/derivation/` — the comprehension composer: `extract.py` (lexeme quantity extraction, EX-1/4/5 + function-word unit filter), `clauses.py` (GB-1 segmentation), `compose.py` (GB-2a list-sum + GB-3a clause-scoped referent guard), `accumulate.py` (GB-3b.1 single-referent gain/loss chaining), `multistep.py`/`search.py` (bounded search), `verify.py` (the wrong=0 self-verification gate: grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness).
- `generate/cue_precision/` — `(cue, op, unit_shape)` reliability ledger + trainer (ADR-0177 CP-1/CP-2a); inert (consulted by no serving/gate path yet).
- `evals/gsm8k_math/` — `train_sample/` (real GSM8K, the capability metric), `practice/` (sealed attempt-and-eliminate lane + ADR-0163-F additive set), `confusers/` (ADR-0163-F2 discrimination probe — scored by `wrong→0` + pair-consistency, NOT flip-count).
- `scripts/verify_lane_shas.py`, `scripts/generate_claims.py --check` — the serving-frozen gate (pinned eval-lane SHAs + `CLAIMS.md`).

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

## Lookback Review Discipline

Multi-PR architectural work accumulates latent defects when each PR
is reviewed only against its own acceptance criteria.  A hazard
introduced in PR N can sit dormant until PR N+2 exercises it — by
which point the substrate is harder to fix and three PRs are
implicated rather than one.

**Mandatory lookback review** is triggered at three points:

1. **Before starting the next phase of a multi-phase ADR.**  Before
   any code on Phase N+1, audit Phase N's shipped substrate.  Check
   for: ADR-doc vs implementation drift, untested predicate paths,
   wrong=0 hazard surfaces, cross-phase trace/event/rank consistency,
   things the ADR says that didn't actually ship.

2. **Before merging a stacked PR sequence into main.**  When 2+ PRs
   stack (PR #420 stacked on #416, #423 stacked on #420), the
   review-each-PR-individually pattern misses cross-PR consistency
   issues.  Audit the whole stack as one unit before any merge.

3. **After any 3+ PR sequence on the same module or architectural
   surface.**  When work concentrates on one area, regression risk
   compounds.  Audit before claiming the surface is "stable" or
   "ready for the next layer."

**What a lookback review covers** (template — adjust per scope):

- **Documentation drift.**  Does what shipped match what the ADR / brief
  said would ship?  Signature differences, scope reductions, missing
  pieces — flag them.
- **Test coverage gaps.**  Run the test suite under coverage.  For every
  predicate/branch in a closed-set contract (like
  `VALID_PREDICATE_NAMES`), confirm at least one test asserts the
  specific elimination/admission path.  Vacuous tests (assertions
  that pass under broken impl) are coverage gaps.
- **Parity gaps.**  When a new implementation claims byte-equivalence
  with an existing one, exercise BOTH on the same inputs and confirm
  identical outputs — including failure modes, not just success.
- **wrong=0 hazard surface.**  Every new code path: under what input
  conditions could it admit a candidate the prior path would have
  refused?  Trace upstream to confirm no input class can trigger it.
  If a class CAN trigger it, build the defensive refusal NOW, before
  the next phase makes it load-bearing.
- **Cross-PR consistency.**  Trace event shapes, rank handling,
  determinism contracts, dataclass invariants — do they compose
  cleanly across PRs?
- **Honest LOC accounting.**  Did this phase net add or net remove
  lines?  ADR claims of "removes ~N lines" only count post-collapse;
  intermediate phases that ADD substrate before removal happens
  should be called out.

**Output.**  The review produces a structured report with findings
categorized as: solid, gaps (no risk), drift (need amendment), and
hazards (live wrong=0 risks).  Hazards require a fix-before-next-phase
decision.

**Cost.**  A lookback review on a 3-PR substrate typically takes
20-40 minutes of focused tool calls.  Skipping it costs more: every
PR built on an undetected hazard becomes implicated when the hazard
fires, and the fix has to land across multiple PRs instead of one.

## Architectural Scan Exclusions

The invariant tests in `tests/test_architectural_invariants.py` perform
full source-tree walks to enforce structural claims (INV-02, INV-21,
INV-24).  These scans **must** exclude `.claude/` from traversal.

**Why this matters:** Agent operators (Claude Code, Codex, Gemini) create
worktrees under `.claude/worktrees/`.  Those worktrees contain full copies
of the source tree — including `vault/`, `chat/`, `generate/`, etc. — and
will trip every structural invariant that scans for forbidden callsites.
The failures are silent killers: the tests report real-looking violations
against files that aren't in the live codebase, poisoning the smoke suite
and masking actual regressions.

**Maintained exclusion sets** (keep `.claude` in both):

```python
# INV-02  os.walk exclusion (test_normalize_not_called_outside_gate)
{".git", ".venv", "__pycache__", ".pytest_cache", ".hypothesis", ".claude"}

# INV-21 / INV-24  rglob exclusion (EXCLUDED_DIRS)
{"tests", "evals", "benchmarks", "scripts", "docs",
 "core-rs", ".venv", "__pycache__", ".claude"}
```

If you add a new source-tree scan to the invariant suite, add `.claude`
to its exclusion set before the first commit.  Never rely on worktrees
being pruned — they can persist across sessions and CI runs.

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
