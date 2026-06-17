---
name: core-bootstrap
description: Mandatory statelessness compensation + smoke test + recent handoff check for CORE. Auto-invoked on session/subagent start.
triggers: ["session_start", "new_subagent", "arena_spawn"]
auto_invoke: true
---

Execute the full **Session Start Checklist** from GROK.md in strict order:

1. Read GROK.md in full.
2. Read AGENTS.md in full.
3. Read docs/runtime_contracts.md in full.
4. Run `core test --suite smoke -q` and report pass/fail.
5. Check for and read any HANDOFF-*-YYYY-MM-DD.md from the last 3 days.
6. State task scope in one clear sentence before any further action.

This skill must complete successfully before any editing, proposal, or subagent work. It is non-bypassable for Grok 4.3 / Grok Build sessions on CORE.