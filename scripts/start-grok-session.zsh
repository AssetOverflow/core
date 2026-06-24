#!/usr/bin/env zsh
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || return 2 2>/dev/null || exit 2

branch="$(git branch --show-current 2>/dev/null || true)"
main_sha="$(git rev-parse origin/main 2>/dev/null || true)"
head_sha="$(git rev-parse HEAD 2>/dev/null || true)"

if [[ -n "${branch}" && "${branch}" != "main" && -z "${CODEX_ALLOW_NON_MAIN_BASE:-}" ]]; then
  cat <<MSG
You are on branch '${branch}', not origin/main.

For a new task:
  git switch main && git pull --ff-only origin main && ./scripts/start-grok-session.zsh

For resuming this PR branch:
  CODEX_ALLOW_NON_MAIN_BASE=1 ./scripts/start-grok-session.zsh

Current:
  HEAD        ${head_sha}
  origin/main ${main_sha}
MSG
  return 2 2>/dev/null || exit 2
fi

source scripts/agent_startup.sh
