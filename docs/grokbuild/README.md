# Using Grok 4.3 + Grok Build with CORE — Mastery Guide

This document defines the canonical, high-discipline way to use Grok 4.3 and Grok Build on the AssetOverflow/core repository.

The goal is not to make the model "smarter." The goal is to make the **engineering process** more disciplined, reproducible, and resistant to architectural drift while leveraging powerful agentic tooling.

Grok Build is treated as a **bounded engineering laboratory**, not an autonomous architecture mutator.

---

## 1. Philosophy & Mental Model

- Grok 4.3 is fast, high-context, and agentic. This is both its strength and its primary risk on CORE.
- The system must remain **coherent by construction**. Any change that weakens `||F * reverse(F) - 1||_F < 1e-6`, epistemic rigor, or trust boundaries is a defect, not an optimization.
- Human judgment remains the final authority. Grok proposes, sweeps, verifies, and documents. Humans decide.
- Statelessness is a feature, not a bug. We compensate for it structurally (bootstrap skill + handoff docs + prompt library).

**Core Principle**: Prefer refusal over wrong. Prefer small, verifiable diffs over large ambitious changes.

---

## 2. Initial Setup (One-Time)

1. Clone the repo and checkout `main`.
2. Copy `docs/examples/grok43.env.example` to your local `.env` and fill in your `XAI_API_KEY`.
3. Install Grok Build CLI using the current official xAI instructions.
   Do not pipe installer scripts into a shell unless the source and any available checksum/signature have been verified.
4. Run `grok inspect` inside the repo root to confirm skills are discovered.
5. (Optional but recommended) Create a personal `skills/` override directory if you want local custom skills.

---

## 3. Standard Session Workflow (Recommended Loop)

Every productive session follows this pattern:

### Phase 0: Bootstrap + Workspace Hygiene (Mandatory)

- Invoke `/core-bootstrap` or run the skill manually through Grok Build.
- Read `GROK.md` + `AGENTS.md` + `docs/runtime_contracts.md`.
- Confirm the current directory and repository root before any operation:
  ```bash
  pwd
  git rev-parse --show-toplevel
  test -f GROK.md
  test -f AGENTS.md
  ```
- Inspect the local tree before any branch movement:
  ```bash
  git status --short --branch
  git diff --stat
  git diff --name-status
  git diff --cached --name-status
  git stash list
  git worktree list
  ```
- If the tree is dirty, classify every loose file/change before switching branches:
  - current task work;
  - likely prior PR/branch work;
  - accidental generated artifact;
  - evidence/report file that should be restored;
  - unknown.
- For unknown work, inspect history and open PR state before stashing or restoring:
  ```bash
  git diff -- <path>
  git log --oneline --decorate --all -- <path>
  git branch --sort=-committerdate | head -20
  gh pr list --state open --limit 20
  gh pr status
  ```
- Preserve unknown work with a descriptive stash; never destroy it blindly:
  ```bash
  git stash push -m "WIP unknown before <task-slug>: <short file summary>" -- <paths>
  ```
- Establish a clean, current baseline:
  ```bash
  git fetch origin --prune
  git switch main
  git pull --ff-only origin main
  git status --short --branch
  ```
- For non-trivial implementation, create a fresh worktree from current `origin/main`:
  ```bash
  git worktree add ../core-<task-slug> origin/main -b <branch-name>
  cd ../core-<task-slug>
  ```
- Run smoke suite, or record the exact local failure and use repo-native pytest lanes if the `core` CLI is unavailable.
- Read the most recent relevant `HANDOFF-*.md`.

### Phase 1: Context & Scope

- Paste the **Session Entry / Context Load** prompt from `docs/core-rd-base-prompts.md`.
- Clearly state the exact scope and the invariant(s) you will preserve.

### Phase 2: Planning (Plan Mode Preferred)

- Use **Plan Mode** for anything non-trivial.
- Produce a clear plan with:
  - Modules affected
  - Invariants touched
  - Tests/evals that will be impacted
  - Risk assessment

### Phase 3: Sweep

- Run full import/call-site/eval sweep before any edit (use `pre-edit-sweep` skill when available).
- Use the 1M context window aggressively.

### Phase 4: Implementation

- Make minimal, load-bearing changes.
- Write failing tests *before* behavior changes when possible.
- Prefer explicit refusal over silent wrong answers.

### Phase 5: Verification

- Run relevant test suites (smallest relevant first).
- Run **Versor Coherence Guardian** checks on any algebra/field/vault/generate changes.
- Run the **Standing Loop Axiom Check** (#7 from prompt library).
- Verify PR hygiene before opening:
  ```bash
  git status --short
  git diff --check origin/main...HEAD
  git diff --name-status origin/main...HEAD
  git log --oneline --reverse origin/main..HEAD
  ```

### Phase 6: Documentation, PR Summary & Handoff

- Write/update the handoff document using `docs/handoff_template.md`.
- Record exact invariants verified, tests run, and open tasks.
- Every PR summary must include:
  - branch name;
  - commit list in order;
  - exact changed files;
  - exact tests/evals run and outputs;
  - whether `wrong_total == 0` applies and held;
  - known caveats;
  - explicit non-goals;
  - handoff content or handoff file path.

---

## 4. Using Grok Build Features at Mastery Level

### Plan Mode

- Default for any change touching `algebra/`, `field/`, `vault/`, `generate/`, `teaching/`, `core/cognition/`, or `calibration/`.
- Use it even for "small" refactors in sensitive areas.
- Review the plan carefully before approval — this is your main defense against drift.

### Arena / Parallel Subagents

- Powerful but high-risk if not structured.
- Recommended pattern: Role separation
  - **Agent A**: ADR / invariant auditor
  - **Agent B**: Import + call-site sweeper
  - **Agent C**: Test/eval designer + verifier
  - **Agent D**: Minimal implementation proposer
  - **Agent E**: Adversarial reviewer / confuser generator
- All subagent outputs are treated as **independent proposals**.
- Human (or a final reconciliation agent) merges the reconciled result.
- Every subagent must independently satisfy core invariants before its output is considered.

### Skills System

- Prefer skills over ad-hoc prompting for repeated patterns.
- Currently available high-value skills:
  - `/core-bootstrap`
  - `/versor-coherence-guardian`
  - `/pre-edit-sweep`
  - `/claim-proposal-guardian`
- Use `/skillify` after successful sessions to capture new reusable workflows.

---

## 5. Prompt Library (`docs/core-rd-base-prompts.md`)

This is the canonical set of phase-specific guardrails.

**Key sections to use regularly**:
- #1 Session Entry / Context Load (start of almost every session)
- #7 Standing Loop Axiom Check (end of every session before commit)
- #8 PR Merge-Readiness Audit (before opening or merging any PR)
- #9 Grok Build Implementation Session (structured session protocol)

The other sections (#2–#6) are used situationally depending on the type of work.

---

## 6. Anti-Patterns to Avoid

- Treating Grok as the final authority on architecture
- Running large changes without Plan Mode on sensitive modules
- Letting Arena subagents edit without role separation and reconciliation
- Skipping the bootstrap + smoke + handoff loop
- Switching branches before inspecting dirty state
- Deleting, resetting, or restoring unknown local work without classifying it
- Pulling `main` without first fetching/pruning and verifying fast-forward state
- Reusing stale branches for new tasks that should start from current `origin/main`
- Using statistical/approximate solutions for exact CGA or epistemic requirements
- Bypassing review gates for claim/pack/policy/identity mutations
- Assuming "it probably didn’t touch the invariant" without verification

---

## 7. PR & Merge Discipline

Before opening or merging any PR:

1. Run the **PR Merge-Readiness Audit** prompt (#8).
2. Ensure the diff is minimal and load-bearing.
3. Verify all touched invariants have explicit checks.
4. Confirm relevant tests/evals are green with exact outputs recorded.
5. Write a high-quality handoff document.
6. Include a complete PR summary: branch, commits, changed files, tests/evidence, invariants, caveats, non-goals, and handoff.

For docs/config/agent-governance PRs (like this one), smoke is usually sufficient. For runtime changes, full validation is required.

---

## 8. Long-Term Maintenance of This Governance Layer

- The files in this setup (`GROK.md`, `AGENTS.md`, skills, prompt library, handoff template) are living documents.
- When CORE’s architecture evolves (new invariants, new modules, new boundaries), update the relevant governance files in the same PR or a follow-up.
- Periodically review whether new high-value skills should be extracted from successful sessions.
- Treat this layer with the same rigor as runtime code — it protects the architecture.

---

## 9. Quick Reference

```text
# Bootstrap (in Grok Build TUI or via skill invocation)
/core-bootstrap

# Confirm root
pwd
git rev-parse --show-toplevel

# Inspect local state before branch movement
git status --short --branch
git diff --stat
git diff --name-status
git diff --cached --name-status
git stash list
git worktree list

# Establish clean current main
git fetch origin --prune
git switch main
git pull --ff-only origin main

# Create fresh worktree for non-trivial work
git worktree add ../core-<task-slug> origin/main -b <branch-name>
cd ../core-<task-slug>

# Verify core invariant
core test --suite algebra -q

# Start Grok Build
grok

# Inspect current skills and config
grok inspect
```

---

This document, combined with the files it references, represents the current best-known method for using Grok 4.3 + Grok Build on CORE with high discipline and low risk of architectural regression.
