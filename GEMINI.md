# CORE Agent Instructions for Gemini

Read this file before modifying the repository.

`AGENTS.md` is the canonical governance file for this repo.
If this file conflicts with `AGENTS.md`, follow `AGENTS.md`.

## Session start

1. Read `AGENTS.md`.
2. Read `docs/runtime_contracts.md`.
3. Read the most recent `HANDOFF-*.md` from the last 3 days if one exists and is relevant.
4. Confirm repository root and inspect the working tree before editing.
5. Run:

```bash
core test --suite smoke -q
```

6. State the task scope before making changes:
   - which module(s) you will touch
   - which invariant or contract you must preserve

## Working rules

- Do not invent alternate architecture, alternate invariants, or alternate memory rules.
- Use the smallest relevant validation lane first, then broader lanes as required by change scope.
- For docs/config-only changes, smoke is usually sufficient unless the change affects executable paths, tests, CLI behavior, or generated artifacts.
- Prefer small, load-bearing changes.
- Use `AGENTS.md` as the source of truth for architecture, invariants, validation, and PR standards.

## Session end

When a session produced meaningful implementation or architectural analysis, write or update a handoff document using the repo’s handoff template and current naming convention.
