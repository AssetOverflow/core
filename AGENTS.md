# CORE Agent Instructions

This is the canonical governance file for this repository.

If any provider-specific file (`CLAUDE.md`, `GEMINI.md`, or future agent files) overlaps with this document, `AGENTS.md` wins. Provider files should only contain minimal startup and workflow notes, not alternate architecture or alternate invariants.

## Mission

CORE is a deterministic cognitive engine under construction.

It is:
- inspectable
- replayable
- evidence-governed
- coherence-first

It is not:
- a transformer wrapper
- a generic chatbot
- an infrastructure playground
- a stochastic fallback shell

## North star

CORE should become capable of:

```text
listen -> comprehend -> recall -> think -> articulate -> learn from reviewed correction -> replay deterministically
```

The live path is:

```text
CognitiveTurnPipeline
-> tokenize / OOV policy / inject
-> intent classification
-> PropositionGraph
-> ArticulationTarget
-> deterministic realizer / articulation surface
-> telemetry / trace
-> reviewed teaching capture when applicable
-> deterministic replay / eval / calibration
```

Improve CORE by strengthening this path, not by bypassing it.

## Non-negotiable invariants

### Field invariant
Every runtime field state `F` must satisfy:

```text
versor_condition(F) < 1e-6
```

Do not weaken this threshold to make code or tests pass.
Fix the operator or construction boundary that violated it.

### Allowed normalization boundaries
Normalization / closure / canonicalization belongs only at explicit construction or algebra boundaries, such as:
- `ingest/gate.py`
- `language_packs/compiler.py`
- `algebra/versor.py`
- `sensorium/*/canonical.py`
- `session/context.py` for session-scoped **semantic anchoring** of the field toward the session concept-attractor (the anchor pull, hemisphere consistency). Allowed ONLY because every such op (1) preserves `versor_condition` BY CONSTRUCTION — composed from `rotor_power` / `word_transition_rotor` / `versor_apply` on the Spin manifold, never a post-hoc `unitize`/grade-projection — AND (2) carries semantic meaning in the cognitive model.
- other explicitly documented construction boundaries

Forbidden in hot paths and repair layers, including:
- `generate/stream.py`
- `field/propagate.py`
- `vault/store.py`
- logging / telemetry / shell glue

**The bright line — semantic anchoring vs. drift repair.** An op is *semantic anchoring* (allowed at the sites above) iff it preserves `versor_condition` by construction AND expresses a relation in the cognitive model. It is *drift repair* (forbidden) iff its purpose is to restore a numerical invariant a prior function should have preserved. Closure of field transitions is owned solely by `algebra/versor.py` (`_close_applied_versor`); no other site may "fix" it. Naming must not disguise the distinction: an op that anchors semantically must not be named or documented as a "drift fix".

Do not add drift repair, watchdog normalization, hidden unitization, or post-hoc algebra fixes outside owned boundaries.

### Exact recall
Runtime recall remains exact and deterministic.
Do not add:
- cosine similarity
- ANN / approximate nearest neighbor
- HNSW
- embedding ranking as runtime memory truth

Use exact CGA recall primitives only.

### No opaque fallback cognition
Do not add stochastic generation, hidden LLM fallback logic, or probabilistic substitutes inside the deterministic cognitive path.

### Teaching and mutation safety
Learning is controlled mutation.
- session memory may be local and immediate
- reviewed/durable memory goes through the teaching path
- pack mutation is proposal-only until reviewed
- identity override attempts are rejected, not learned

Do not invent a parallel learning path.

#### The learning boundary is typed, not "everything is proposal-only"
A common misreading treats *all* learning as proposal-only. That is a false bottleneck. The real boundary is between **durable** standing and **provisional** standing, and it is already mechanically enforced:
- **Durable mutation stays reviewed or proof-carrying.** Corpus / pack / policy / identity changes, and any promotion to COHERENT/verified standing, go through the reviewed teaching loop (`teaching/*`, proposal-only) or the proof-carrying promotion gate.
- **Provisional state may update autonomously — iff typed, isolated, replayable, and unable to masquerade as ratified truth.** This covers session memory, sealed practice ledgers, SPECULATIVE idle consolidation of soundly-derived facts, reliability-ledger counts, proposal emission, and disclosed licensed estimates. Each is written SPECULATIVE (never COHERENT), through the same `VaultStore.store` path (no parallel memory), deterministically, and carries its standing honestly.

This boundary is a set of failing-when-violated invariants, not a convention:
- **INV-21** — only allowlisted modules may call `VaultStore.store(...)`.
- **INV-22 / INV-23** — an unmarked pack row and an unmarked `store()` default to SPECULATIVE; COHERENT requires an explicit stamp.
- **INV-24** — every `vault.recall` callsite is categorized; user-facing evidence must pass `min_status=COHERENT`.
- **INV-29** — only `vault/store.py` may transition an `epistemic_status`.
- **INV-30** — the open-world `determine()` gear constructs only `Determined(answer=True)` or refuses; it can never assert `answer=False`. Closed-world entailed-negation must use a distinct closed-world type and entry point.

### Kernel substrate rule
New derivation work should consume `KernelFacts` / `ProblemFrame` where the substrate can represent the meaning.
Do not introduce new local prose parsers inside derivation organs unless explicitly marked as legacy exception with migration rationale.

## Working doctrine

Before editing:
1. Read this file.
2. Read `docs/runtime_contracts.md`.
3. Read the latest recent `HANDOFF-*.md` if relevant.
4. Confirm repo root and inspect working tree state.
5. Run the smallest relevant validation lane.

For non-trivial edits:
- trace imports and call sites first
- identify the invariant being protected
- prefer semantics-preserving cleanup before new mechanisms
- keep changes small and load-bearing
- If working in Arena/parallel subagent mode, each subagent must independently satisfy `versor_condition` and results must be reconciled before merge. No subagent output becomes another subagent's unchecked input.

### Workspace Hygiene + Branch Protocol
Before branch movement or edits:
- Confirm cwd/repo root.
- Inspect dirty state (`git status`, `git diff`); classify loose files before stashing or deleting.
- Establish a clean current `main`.
- Prefer a fresh worktree from `origin/main` for non-trivial implementation.

### Pre-Edit Sweep & Versor Coherence Guardian Protocol
Before modifying any module in `algebra/`, `field/`, `vault/`, or `generate/`:
- Trace every import of the target module and identify all callers.
- Check `calibration/` and `evals/` for tests that exercise the changed path.
- Explicitly confirm the core invariant `||F * reverse(F) - 1||_F < 1e-6` holds for the affected state.

## Documentation Discipline

ADRs, session docs, audit artifacts, and handoff briefs stay as Markdown (GitHub-flavored). Plain-text artifacts are diffable, greppable, and readable by every agent in the dispatch pipeline.

Within Markdown, two GitHub-rendered features are sanctioned and otherwise sparingly used:
- Mermaid fenced blocks (` ```mermaid `) when a state machine, sequence, or dependency graph genuinely communicates more than prose. Inline, not in a sidecar file.
- `<details>` / `<summary>` collapsibles to fold long proofs, large tables, or generated logs without losing single-file context.

Out of scope:
- Standalone HTML artifacts with embedded CSS / inline SVG / sidebar navigation.
- Dashboards, status pages, or visualizers as a substitute for a pinned data artifact. If a visualization is load-bearing, the underlying data must live in a deterministic JSON/JSONL/Markdown artifact first.

## Validation lanes

Use the CLI lanes as the standard validation surface:

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

Run the smallest relevant suite first.
Run broader suites before merge when the change touches runtime, algebra, cognition, teaching, packs, or trust boundaries.

## Security and trust boundaries

Any change touching user-controlled text, files, dynamic imports, pack loading, validators, logs, or report output must state its trust boundary.

Required defaults:
- explicit opt-in for arbitrary execution
- reject unsafe paths before filesystem access
- centralize safe display/log handling
- no hidden background execution
- no broad filesystem mutation without explicit boundary and tests

## PR checklist

Before merge, answer:

```text
What capability, performance property, or security boundary did this add or protect?
Which invariant proves the field remained valid?
Which validation lane proves the change?
Did this avoid hidden normalization, stochastic fallback, approximate recall, and unreviewed mutation?
If it touched user input, files, dynamic imports, or logs, what trust boundary was enforced?
```

## Provider-file policy

`CLAUDE.md`, `GEMINI.md`, and any future provider file must:
- be short
- point here as canonical
- avoid duplicating architecture
- avoid introducing provider-only truth
- differ only where tool startup behavior genuinely requires it
