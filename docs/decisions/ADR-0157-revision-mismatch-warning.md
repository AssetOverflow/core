# ADR-0157 — Revision-mismatch warning on engine-state load (W-023 / L10b.2)

Status: accepted
Date: 2026-05-26

## Context

ADR-0146 §Risks line 127 specified:

> "Compare `written_at_revision` in `manifest.json` with the current git
> SHA. If they mismatch, log a warning but continue startup (do not refuse
> to start, as a reboot is recovery, not control flow)."

W-008 and W-022 implemented the manifest write path but never implemented
the read-side comparison. After a `git pull` or a branch switch the engine
silently loads a checkpoint written by a different code version, which can
produce confusing behaviour if serialization formats changed.

## Decision

Inside `EngineStateStore.load_manifest()`, after parsing the JSON:

1. Read `manifest["written_at_revision"]` (stored revision).
2. Call `_git_revision()` to obtain the current HEAD short SHA.
3. If both values are non-empty and not `"unknown"`, and they differ,
   emit `warnings.warn(..., RuntimeWarning, stacklevel=2)`.
4. Always return the manifest — never raise, never clear state.

The warning message names both revisions and suggests clearing
`engine_state/` if unexpected behaviour is observed.

### Why `warnings.warn` not `logging`

`warnings` is already used in the codebase (`core/physics/identity.py`).
It is testable via `pytest.warns` without logger configuration, fits
`RuntimeWarning` semantics (a recoverable runtime anomaly), and respects
the standard Python warning filter so operators can suppress or escalate it
via `-W` flags or `PYTHONWARNINGS`.

### Why suppress when either side is `"unknown"`

`_git_revision()` returns `"unknown"` when `git` is unavailable (CI
containers, packaged builds, offline environments). Storing `"unknown"` or
comparing against it would always trigger a spurious warning in those
environments. Suppressing when either side is unknown is the
lowest-surprise behaviour.

## Invariants pinned by tests

`tests/test_adr_0157_revision_mismatch_warning.py` (8 tests):

- Matching revision → no `RuntimeWarning`
- Mismatched revision → `RuntimeWarning` emitted, manifest returned intact
- Warning message contains both the stored and current revisions
- `written_at_revision: "unknown"` in stored manifest → no warning
- `_git_revision()` returns `"unknown"` → no warning
- Missing manifest file → `None` returned, no warning
- Empty manifest file → `None` returned, no warning

## Out of scope

- **Schema-version migration.** A `schema_version` bump requires a
  migration or clear-slate fallback (ADR-0146 §Risks line 125). That is
  separate from the revision warning and deferred to a future ADR when
  `_SCHEMA_VERSION` is actually incremented.
- **`reboot_event` audit trail entry** — L10b.3 / W-024.

## Validation

- `tests/test_adr_0157_revision_mismatch_warning.py` (8 passed)
- `tests/test_adr_0146_engine_state.py` (8 passed — round-trip regression guard)
- `core test --suite smoke` (67 passed)
