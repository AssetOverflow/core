#!/usr/bin/env bash
set -euo pipefail

cd "${CODEX_WORKTREE_PATH:?CODEX_WORKTREE_PATH must name the new worktree}"

echo "== CORE Codex environment setup =="
echo "Worktree: $CODEX_WORKTREE_PATH"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: CODEX_WORKTREE_PATH is not inside a git worktree."
  exit 1
fi

echo
echo "== Git identity / branch =="
CURRENT_BRANCH="$(git branch --show-current || true)"
HEAD_SHA="$(git rev-parse HEAD)"
echo "Branch: ${CURRENT_BRANCH:-DETACHED}"
echo "HEAD:   $HEAD_SHA"

echo
echo "== Fetching remote =="
git fetch origin --prune

ORIGIN_MAIN_SHA="$(git rev-parse origin/main)"
MERGE_BASE_SHA="$(git merge-base HEAD origin/main || true)"
echo "origin/main: $ORIGIN_MAIN_SHA"
echo "merge-base:  ${MERGE_BASE_SHA:-NONE}"

echo
echo "== Working tree status =="
git status --short

: "${CODEX_ALLOW_DIRTY:=0}"
if [ "$CODEX_ALLOW_DIRTY" != "1" ] && [ -n "$(git status --porcelain)" ]; then
  echo
  echo "ERROR: Worktree is dirty before task start."
  echo "Set CODEX_ALLOW_DIRTY=1 only for an explicit resume or setup-repair task."
  exit 1
fi

# Codex creates a detached worktree at the source snapshot selected by the app.
# Fetching here may move origin/main after that snapshot has been chosen, so Git
# topology is diagnostic setup evidence rather than an environment precondition.
if [ "$HEAD_SHA" != "$ORIGIN_MAIN_SHA" ]; then
  echo
  if git merge-base --is-ancestor HEAD origin/main; then
    TOPOLOGY="behind origin/main"
  elif git merge-base --is-ancestor origin/main HEAD; then
    TOPOLOGY="ahead of origin/main"
  else
    TOPOLOGY="diverged from origin/main"
  fi
  echo "WARNING: Worktree HEAD is $TOPOLOGY."
  echo "Review or reconcile the task base before publishing changes."
fi

echo
echo "== Changed files vs origin/main =="
git diff --name-only origin/main...HEAD || true

echo
echo "== Toolchain =="
if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required for AssetOverflow/core."
  echo "Install it locally first, e.g. brew install uv"
  exit 1
fi

if [ -f uv.lock ]; then
  echo "uv.lock found; syncing with frozen lockfile."
  uv sync --frozen
else
  echo "No uv.lock found; skipping uv sync to avoid generating a lockfile."
fi

python3 --version || python --version
uv --version

echo
echo "== Final status =="
git status --short

echo
echo "== Setup complete =="
