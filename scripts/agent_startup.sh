#!/usr/bin/env bash
# =============================================================================
# scripts/agent_startup.sh
#
# Codex / Gemini environment startup guard for CORE.
#
# PURPOSE
#   Catch stale-base worktrees before they create replay/conflict PRs.
#   Every new implementation task must run from HEAD == origin/main on a
#   clean tree.  PR-resume tasks may run from a branch, but only when
#   origin/main is a proper ancestor of HEAD.
#
# USAGE
#   source scripts/agent_startup.sh        # default (strict)
#   CODEX_ALLOW_DIRTY=1 source ...         # allow dirty worktree (debug only)
#   CODEX_ALLOW_NON_MAIN_BASE=1 source ... # allow HEAD ahead of origin/main
#                                          # (PR-resume; ancestry still checked)
#
# EXIT CODES
#   0   All checks passed — safe to proceed.
#   1   Guard failed — do NOT start the task.
#
# ENVIRONMENT CONTROLS
#   CODEX_ALLOW_DIRTY=1           Bypass dirty-tree check (debug/wip only).
#   CODEX_ALLOW_NON_MAIN_BASE=1   Allow HEAD ahead of origin/main, but only
#                                 when origin/main is a strict ancestor of HEAD.
#
# NON-GOALS
#   This script does NOT touch runtime, evals, reports, teaching proposals,
#   packs, policy, identity, recall, vault, field, algebra, or serving paths.
# =============================================================================

set -euo pipefail

# ── helpers ──────────────────────────────────────────────────────────────────

_PASS="✓"
_FAIL="✗"
_WARN="!"

_ok()   { printf '%s %s\n' "$_PASS" "$*"; }
_fail() { printf '%s %s\n' "$_FAIL" "$*" >&2; }
_warn() { printf '%s %s\n' "$_WARN" "$*" >&2; }
_sep()  { printf '%s\n' "────────────────────────────────────────────────────────────────────────"; }

_die() {
    _fail "$*"
    _fail "Aborting. Fix the issue above, then re-run this script."
    # Use 'return' rather than 'exit' so sourced scripts don't kill the shell.
    return 1
}

# ── header ───────────────────────────────────────────────────────────────────

_sep
printf 'CORE agent startup guard  |  %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
_sep

# ── 0. repository root ────────────────────────────────────────────────────────

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    _die "Not inside a git repository."
}
_ok "repo root: $REPO_ROOT"

# ── 1. fetch origin --prune ───────────────────────────────────────────────────

printf 'Fetching origin --prune …\n'
if git fetch origin --prune --quiet; then
    _ok "fetch origin --prune"
else
    _die "git fetch origin --prune failed.  Check network / remote config."
fi

# ── 2. diagnostic: HEAD, branch, origin/main, merge-base ──────────────────────

HEAD_SHA="$(git rev-parse HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
ORIGIN_MAIN_SHA="$(git rev-parse origin/main 2>/dev/null)" || {
    _die "origin/main does not exist.  Ensure origin is correctly configured."
}
MERGE_BASE="$(git merge-base HEAD origin/main 2>/dev/null)" || {
    _die "Could not compute merge-base between HEAD and origin/main."
}

printf '\n'
printf '  HEAD         : %s\n' "$HEAD_SHA"
printf '  branch       : %s\n' "$BRANCH"
printf '  origin/main  : %s\n' "$ORIGIN_MAIN_SHA"
printf '  merge-base   : %s\n' "$MERGE_BASE"
printf '\n'

# ── 3. dirty-tree check ────────────────────────────────────────────────────────

DIRTY="$(git status --porcelain)"
if [ -n "$DIRTY" ]; then
    if [ "${CODEX_ALLOW_DIRTY:-0}" = "1" ]; then
        _warn "Dirty worktree detected (CODEX_ALLOW_DIRTY=1, continuing in debug mode)."
    else
        _fail "Dirty worktree detected.  Uncommitted changes are present:"
        printf '%s\n' "$DIRTY" >&2
        _die "Set CODEX_ALLOW_DIRTY=1 only for explicit debug sessions.  For a new task, start from a clean tree."
    fi
else
    _ok "working tree is clean"
fi

# ── 4. base guard: HEAD == origin/main (default) or ancestry check (resume) ───

if [ "$HEAD_SHA" = "$ORIGIN_MAIN_SHA" ]; then
    _ok "HEAD == origin/main (fresh base, new task allowed)"
else
    if [ "${CODEX_ALLOW_NON_MAIN_BASE:-0}" = "1" ]; then
        # PR-resume mode: origin/main must be an ancestor of HEAD.
        if [ "$MERGE_BASE" = "$ORIGIN_MAIN_SHA" ]; then
            _ok "CODEX_ALLOW_NON_MAIN_BASE=1 — origin/main is ancestor of HEAD (PR-resume allowed)"
        else
            _fail "CODEX_ALLOW_NON_MAIN_BASE=1 is set, but origin/main is NOT an ancestor of HEAD."
            _fail "  HEAD         : $HEAD_SHA"
            _fail "  origin/main  : $ORIGIN_MAIN_SHA"
            _fail "  merge-base   : $MERGE_BASE"
            _die "Your branch has diverged from origin/main.  Rebase onto origin/main before resuming."
        fi
    else
        _fail "HEAD is not origin/main."
        _fail "  HEAD        : $HEAD_SHA  (branch: $BRANCH)"
        _fail "  origin/main : $ORIGIN_MAIN_SHA"
        _fail ""
        _fail "For a new implementation task, the worktree must start from origin/main."
        _fail "If you are resuming a PR, set CODEX_ALLOW_NON_MAIN_BASE=1 and ensure"
        _fail "origin/main is an ancestor of your branch."
        _die "Stale base detected.  This is the condition that caused #844 conflict PRs."
    fi
fi

# ── 5. changed files vs origin/main ───────────────────────────────────────────

printf '\nChanged files vs origin/main:\n'
DIFF_FILES="$(git diff --name-status origin/main HEAD 2>/dev/null)"
if [ -z "$DIFF_FILES" ]; then
    printf '  (none — HEAD is origin/main)\n'
else
    printf '%s\n' "$DIFF_FILES" | sed 's/^/  /'
fi
printf '\n'

# ── 6. uv availability ────────────────────────────────────────────────────────

if command -v uv >/dev/null 2>&1; then
    UV_VERSION="$(uv --version 2>/dev/null || echo 'unknown')"
    _ok "uv found: $UV_VERSION"
else
    _die "uv is not installed or not in PATH.  Install uv before proceeding: https://docs.astral.sh/uv/"
fi

# ── 7. uv sync --frozen (only when uv.lock exists) ────────────────────────────

LOCKFILE="$REPO_ROOT/uv.lock"
if [ -f "$LOCKFILE" ]; then
    printf 'Running uv sync --frozen …\n'
    if uv sync --frozen; then
        _ok "uv sync --frozen succeeded"
    else
        _die "uv sync --frozen failed.  The lock file may be out of date or the environment is broken."
    fi
else
    _warn "uv.lock not found — skipping uv sync (expected for projects without a lock file)"
fi

# ── 8. final git status ────────────────────────────────────────────────────────

_sep
printf 'Final git status:\n'
git status --short --branch
_sep

_ok "Startup guard passed — safe to begin task."
printf '\n'
