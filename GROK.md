# CORE Agent Instructions for Grok 4.3

Read this file in full before touching any file in this repository.
CORE is a deterministic cognitive engine — not a transformer wrapper, not a generic chatbot, not an infrastructure playground. The rules here are architectural invariants, not suggestions.

> **You are stateless.** You have no memory of prior sessions.
> Complete the [Session Start Checklist](#session-start-checklist) before any edits. Do not skip it.

---

## Phase-Specific Prompt Library

For detailed, phase-oriented guardrails that are tightly coupled to CORE’s architecture, invariants, ADRs, and epistemic model, see:

**`docs/core-rd-base-prompts.md`**

These prompts are designed to be used as standing prefixes **in addition to** this file. The "Session Entry / Context Load" prompt is especially recommended at the start of most sessions. The "Standing Loop Axiom Check" is highly effective as a final self-audit before committing.

---

## Session Start Checklist

Run these steps in order, using your tool-call chains, before writing a single line of code:

1. **Read this file in full.**
2. **Read `AGENTS.md` in full.**
3. **Read `docs/runtime_contracts.md` in full.**
4. **Complete the [Workspace Hygiene + Branch/Worktree Protocol](#workspace-hygiene--branchworktree-protocol)** — confirm project root, inspect dirty state, classify loose files, fetch current refs, establish clean `main`, and create a fresh worktree for non-trivial work.
5. **Run the smoke suite and report pass/fail:**
   ```bash
   core test --suite smoke -q
   ```
   If the local environment does not expose `core`, report the exact failure and use the repo-native pytest lanes required by the task.
6. **Check for a recent handoff doc** — if a `HANDOFF-*.md` file exists dated within the last 3 days, read it. It contains state you would otherwise have no way to recover.
7. **State your task scope** — before editing, write one sentence naming the module(s) you intend to change and the invariant you will prove was not violated.

Do not treat conversation history as a substitute for steps 1–6. History does not survive context resets. Ground yourself in the repo.

---

## Workspace Hygiene + Branch/Worktree Protocol

Before any edit, branch switch, worktree creation, stash, or commit, establish the repository state. This protocol is mandatory for Grok 4.3 / Grok Build sessions on CORE.

### 0. Confirm project root

Run:

```bash
pwd
git rev-parse --show-toplevel
test -f GROK.md
test -f AGENTS.md
```

If the current directory is not the repository root, run:

```bash
cd "$(git rev-parse --show-toplevel)"
```

Do not proceed from a parent directory, sibling worktree, nested package directory, or generated-output directory.

### 1. Inspect local state before touching branches

Run:

```bash
git status --short --branch
git diff --stat
git diff --name-status
git diff --cached --name-status
git stash list
git worktree list
```

If the working tree is dirty, do **not** switch branches, pull, reset, overwrite, or stash blindly.

Classify every changed or untracked file first:

- Does it belong to the current task?
- Does it appear to belong to a recent branch or PR?
- Is it an accidental generated artifact?
- Is it an evidence/report file that should be restored rather than deleted?
- Is it unknown?

For unknown changes, inspect before stashing:

```bash
git diff -- <path>
git log --oneline --decorate --all -- <path>
git branch --sort=-committerdate | head -20
gh pr list --state open --limit 20
gh pr status
```

If the origin remains unknown, preserve it with a descriptive stash instead of deleting it:

```bash
git stash push -m "WIP unknown before <task-slug>: <short file summary>" -- <paths>
```

Never use `git reset --hard`, broad `git checkout .`, broad `git restore .`, `git clean`, or destructive cleanup unless the user explicitly approves or every affected file has been classified as disposable.

### 2. Establish a clean, current baseline

**Run the startup guard first** — it automates steps 2–4 and will hard-stop if the worktree is stale:

```bash
source scripts/agent_startup.sh
```

For a new task (default, no env vars) the script requires `HEAD == origin/main` and a clean tree.
For a PR-resume task, set `CODEX_ALLOW_NON_MAIN_BASE=1`; the script then verifies `origin/main` is a strict ancestor of `HEAD`.

If you cannot source the script, perform the equivalent steps manually:

```bash
git fetch origin --prune
git switch main
git pull --ff-only origin main
git status --short --branch
```

If `main` cannot fast-forward, stop and report the exact state. Do not merge, rebase, or resolve conflicts unless explicitly instructed.


### 3. Prefer a new worktree for non-trivial implementation

For non-trivial runtime, reasoning, eval, teaching, pack, or multi-file work, create a fresh worktree from current `origin/main`:

```bash
git worktree add ../core-<task-slug> origin/main -b <branch-name>
cd ../core-<task-slug>
```

Use a normal branch in the same worktree only for small docs/config work or when the user explicitly requests it. Do not reuse stale branches for new work unless the task is explicitly a continuation of that branch.

### 4. Branch naming

Use scope-bounded branch names:

```text
feat/gsm8k-workstream-a-gate-a1-comparative-injection
docs/<area>-<purpose>
fix/<area>-<specific-bug>
chore/<area>-<specific-cleanup>
```

The branch name should encode the capability slice, not an agent name or vague intent.

### 5. Completion protocol

Before opening a PR:

```bash
git status --short
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline --reverse origin/main..HEAD
```

Run the relevant focused tests and record exact outputs. For every PR summary include:

- branch name;
- commit list in order;
- exact changed files;
- exact tests/evals run;
- whether `wrong_total == 0` applies and held;
- known caveats;
- explicit non-goals;
- handoff content or handoff file path.

---

## Reasoning Effort Requirement

You must operate at **high reasoning effort** for all tasks that touch:

- `algebra/`
- `field/`
- `generate/realizer.py`, `generate/graph_planner.py`, `generate/intent.py`
- `vault/store.py`
- `calibration/`
- `core/cognition/`
- `teaching/`

If you were invoked at default or low effort and the task touches any of these modules, **stop and request re-invocation at high effort.** Low-effort reasoning on the algebra/field layer produces plausible-looking but mathematically incorrect results.

For `workbench-ui/`, `docs/`, `notes/`, `scripts/` at low risk, medium effort is acceptable.

---

## Versor Coherence Guardian Protocol

Before proposing or executing **any** change that could affect versor closure, field propagation, or exact CGA recall:

1. Explicitly confirm that the core invariant holds: `||F * reverse(F) - 1||_F < 1e-6` for the affected `FieldState`.
2. Verify that `versor_apply(V, F)` and `cga_inner(X, Y)` paths remain exact and untouched except through the allowed modules (`algebra/versor.py` and permitted callers).
3. Re-run the relevant invariant checks from `tests/test_versor_closure.py` (or current equivalent) on the modified paths.
4. Only after the above may you proceed with edits or proposals.

This protocol is mandatory for any work in `algebra/`, `field/`, `vault/`, or `generate/`.

---

## NON-NEGOTIABLE INVARIANTS

These are **hard architectural constraints enforced by construction**. Violating any one of them is a bug that must be reverted before merge.

**Versor & CGA Level (Exact Algebraic Coherence)**
- `||F * reverse(F) - 1||_F < 1e-6` must hold identically for **every** runtime `FieldState` and every application of `versor_apply(V, F)`.
- All state is represented as versors. All transitions are exact versor products. No exceptions, no approximations.
- Multivector representation in `algebra/` uses fixed `(32,)` float32 arrays for Cl(4,1). No dynamic resizing or external library types in the hot path.
- `cga_inner(X, Y) = -d²/2` is the sole exact recall primitive. It must remain exact and deterministic.

**Normalization & Approximation Boundaries**
- Normalization is allowed **ONLY** at the explicitly listed locations:
  - `ingest/gate.py`
  - `language_packs/compiler.py`
  - `algebra/versor.py`
  - `sensorium/*/canonical.py` (signal canonicalization, pinned only)
  - `session/context.py` (semantic anchoring)
- Forbidden everywhere else, including `generate/stream.py`, `field/propagate.py`, `vault/store.py`, and all logging/telemetry paths.

**No Approximate or Stochastic Mechanisms**
- No cosine similarity, HNSW, ANN indexes, embedding-based recall, or any approximate nearest-neighbor mechanism anywhere in the deterministic cognitive path.
- Vault recall is **exact** `cga_inner` only.
- No stochastic generation, sampling, opaque LLM fallbacks, or probabilistic mechanisms in the core deterministic reasoning, teaching, recognition, or realization pipelines.

**Claim Schema & Epistemic Rigor**
- Claim status transitions (SPECULATIVE → COHERENT → CONTESTED → FALSIFIED) may only occur through the defined review-gated TeachingChainProposal mechanism.
- A claim may not move to COHERENT without passing all applicable review gates and producing a reproducible evidence bundle.
- No direct mutation of epistemic status. Only `vault/store.py` may transition status (INV-29).
- User-facing `vault.recall` must enforce `min_status=COHERENT` (INV-24).

**Safety & Identity Packs**
- Safety packs (`packs/safety/`) are **unmodifiable at runtime**. They are fail-closed and reviewer-signed.
- Identity packs are swappable only via the defined PersonaMotor + proposal mechanism. Runtime mutation is forbidden.
- Any attempt to relax or bypass a safety axis must be rejected and logged as a protocol violation.

If you believe one of these must change for correctness or performance reasons, **STOP**. Write a proposal in `notes/` or `docs/decisions/` and do not implement the change. CORE’s architecture is not negotiated inside a coding session.

---

## Pre-Edit Sweep Protocol

Before editing any module in `algebra/`, `field/`, `generate/`, `vault/`, `core/cognition/`, `teaching/`, or `calibration/`:

1. Use your file-read and search tool chains to **trace every import** of the target module across the codebase.
2. Identify **all callers** of the specific function or class you intend to change.
3. Check `calibration/` and `evals/` for tests that exercise the changed path.
4. Only then propose edits.

Your 1M-token context window means you can load the full relevant subgraph in one pass. Do this. Do not guess at call sites.

---

## Agentic Tool-Call Discipline

Grok 4.3's multi-step tool-call chains are an asset here. Use them to:
- Load the full affected module graph before proposing changes.
- Run CLI validation lanes and report actual output, not assumed output.
- Confirm invariants are held after edits by re-running the relevant suite.

Do not use tool chains to:
- Probe for statistical or ML-based workarounds to exact CGA constraints.
- Discover "alternative" normalization sites not listed above.
- Chain edits across multiple modules before verifying the first one.

---

## Arena / Parallel Subagent Mode

If running in Arena mode (parallel subagents):

- Each subagent **receives its own copy of this file and AGENTS.md**.
- Each subagent must **independently satisfy** `||F * reverse(F) - 1||_F < 1e-6` before reporting results.
- Do not share mutable runtime state between subagents.
- Treat Arena subagent results as **independent proposals**, not sequential commits. Reconcile them before any merge.
- No subagent output becomes another subagent's unchecked input.

---

## End-of-Session Handoff Requirement

At the end of every session, write a handoff document to the repo using the template at `docs/handoff_template.md`. Name it:

```
HANDOFF-grok43-YYYY-MM-DD.md
```

This is not optional. It is the only continuity mechanism across your stateless sessions. A session without a handoff doc is a session whose work may be silently lost or contradicted by the next session.

---

## Kernel Substrate / ProblemFrame Doctrine

New derivation capabilities must consume `KernelFacts` / `ProblemFrame` facts where the
substrate can represent the needed meaning (`generate/problem_frame_builder.py`).

```text
raw problem text → KernelFacts → ProblemFrame → contract-backed derivation organs
```

New raw-prose/local-regex parsing inside a derivation organ requires an explicit
`LEGACY_EXCEPTION` note and a migration rationale. Guard:
`tests/test_kernel_no_new_legacy_derivation_surfaces.py`.

Do not add isolated benchmark organs with local prose parsers. Do not treat #829
substrate modules as optional helpers.

---

## Architecture Summary

Raw input becomes a closed versor field once; thought evolves through exact versor transitions and CGA recall; cognition is structured as intent, proposition graph, articulation target, deterministic realization, reviewed memory, eval/calibration replay, and traceable evidence.

```text
CognitiveTurnPipeline
  -> tokenize / OOV policy / inject
  -> intent classification
  -> PropositionGraph
  -> ArticulationTarget
  -> deterministic realizer / articulation surface
  -> generation walk telemetry
  -> identity + energy telemetry
  -> reviewed teaching capture (when correction intent appears)
  -> deterministic trace hash
```

Key modules:
- `core/cognition/pipeline.py` — cognitive turn spine
- `core/cognition/result.py` — canonical turn result shape
- `core/cognition/trace.py` — deterministic trace hashing
- `generate/intent.py` — deterministic intent classification
- `generate/graph_planner.py` — proposition graph and articulation target
- `generate/realizer.py` / `generate/templates.py` — deterministic realization
- `teaching/*` — reviewed teaching / correction lifecycle
- `vault/store.py` — epistemic store with INV-21/22/23/24/29 guards
- `evals/*` — deterministic eval harness
- `calibration/*` — bounded replay-based calibration
- `docs/runtime_contracts.md` — runtime response, memory, identity, and testing

---

## PR Checklist

Before opening or merging, answer:

```text
What capability, performance property, or security boundary did this add/protect?
Which invariant proves the field remains valid?
Which CLI suite/eval proves the relevant lane?
Did this avoid hidden normalization, stochastic fallback, approximate recall, and unreviewed mutation?
If it touches user input, files, dynamic imports, or logs, what trust boundary was enforced?
Was the smoke suite green before and after?
```

Prefer small, load-bearing PRs.

For runtime/algebra/cognition/teaching/pack changes: run full suite before merge.
For docs/config-only agent-governance changes: smoke is sufficient unless the PR touches CLI, tests, generated docs, or executable scripts.

---

## CLI Validation Lanes

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
For runtime/algebra/cognition/teaching/pack changes, run full before merge.
For docs/config-only agent-governance changes, smoke is sufficient unless the PR changes CLI, tests, generated docs, or executable scripts.
