---
name: core-bootstrap
description: Mandatory statelessness compensation, workspace hygiene, clean-baseline setup, smoke test, and recent handoff check for CORE. Auto-invoked on session/subagent start.
triggers: ["session_start", "new_subagent", "arena_spawn"]
auto_invoke: true
---

Execute the full **Session Start Checklist** from GROK.md in strict order, including the **Workspace Hygiene + Branch/Worktree Protocol**:

1. Read GROK.md in full.
2. Read AGENTS.md in full.
3. Read docs/runtime_contracts.md in full.
4. Confirm project root:
   - `pwd`
   - `git rev-parse --show-toplevel`
   - verify `GROK.md` and `AGENTS.md` exist.
5. Inspect local state before any branch movement:
   - `git status --short --branch`
   - `git diff --stat`
   - `git diff --name-status`
   - `git diff --cached --name-status`
   - `git stash list`
   - `git worktree list`
6. If dirty, classify every changed or untracked file before switching branches. Unknown work must be preserved with a descriptive stash, not destroyed.
7. Fetch current repository state:
   - `git fetch origin --prune`
8. If starting new work, establish clean current main:
   - `git switch main`
   - `git pull --ff-only origin main`
9. For non-trivial implementation, create a fresh worktree from `origin/main` unless the user explicitly requests same-worktree work.
10. Run `core test --suite smoke -q` and report pass/fail. If unavailable, report the exact failure and use repo-native pytest lanes.
11. Check for and read any `HANDOFF-*-YYYY-MM-DD.md` from the last 3 days.
12. Check recent open PRs if local changes or task continuity are ambiguous:
    - `gh pr list --state open --limit 20`
    - `gh pr status`
13. State task scope in one clear sentence before any further action.

This skill must complete successfully before any editing, proposal, or subagent work. It is non-bypassable for Grok 4.3 / Grok Build sessions on CORE.
