# Issue — tests sharing the default `engine_state/` dir (reproducibility hazard)

Status: open (hygiene; interim rule below, recommended fix deferred to a validated PR)
Date: 2026-06-15
Relates: ADR-0146 (engine-state persistence), ADR-0219 (generation-dir checkpoint),
ADR-0220 (identity/provenance reconcile — surfaced the symptom)

## Symptom

During ADR-0220 (PR C) verification, `tests/test_achat.py::test_achat_returns_non_empty_surface`
emitted a spurious:

```
RuntimeWarning: engine identity continuity break: checkpoint was written under
819c4364d599… but this build computes c9e5968ab1fe… — the ratified identity
substrate (packs) changed while the engine was down.
```

It was **not** a regression from the identity split. Re-running with an isolated
state dir made it vanish:

```
CORE_ENGINE_STATE_DIR=$(mktemp -d)/es pytest tests/test_achat.py   # 11 passed, no warning
```

## Root cause

`ChatRuntime(...)` with no `engine_state_path` resolves its store to
`EngineStateStore(None).path == engine_state._DEFAULT_DIR`, which is
`$CORE_ENGINE_STATE_DIR` or the in-repo `engine_state/` dir
(`engine_state/__init__.py:52-56`). That directory is **process-wide shared
state**:

- On construction, a runtime READS it (`store.exists()` → `_load_engine_state`),
  so any test reading a **stale checkpoint** left by an earlier test reconciles
  it (ADR-0220) and can emit a phantom identity-continuity warning.
- Tests that run a turn / checkpoint WRITE a generation-dir checkpoint into the
  same shared dir (the observed pollution was leftover `gen-0583/` `gen-0584/` +
  `current`), so test ordering and prior runs leak into later tests.

This is a classic non-hermetic-test hazard: behaviour depends on what other
tests (or prior local runs) left in `engine_state/`.

## Scope (it is systemic, not a one-off)

In `tests/` at `main@eed20749`:

| Metric | Count |
|---|---|
| `ChatRuntime(...)` constructions | **469** |
| test files constructing it | **123** |
| constructions passing `engine_state_path` (isolated) | 74 |
| constructions passing `no_load_state` (ephemeral, no persist) | 52 |
| **constructions defaulting to the shared dir** | **~340** |

Most defaulting constructions are *victims* (they read the shared dir on
construction); a subset that checkpoint are also *polluters*. CI runs in a clean
checkout so the shared dir starts empty there — which is exactly why this hides:
it bites local runs and ordering-sensitive sessions, not the gate.

## Interim rule (apply now, in review)

Any **new or edited** test that constructs a `ChatRuntime` which loads or
persists runtime state MUST isolate it:

```python
ChatRuntime(config=..., engine_state_path=tmp_path / "engine_state")
# or, for an ephemeral runtime that must not touch persisted state:
ChatRuntime(config=..., no_load_state=True)
```

Subprocess / CLI tests (which re-import in a child process) must set
`CORE_ENGINE_STATE_DIR` in the child env instead (see
`tests/test_l10_always_on_daemon.py::test_real_sigterm_stops_the_daemon_cleanly`
for the pattern).

Do **not** add a bare `ChatRuntime()` that reads/writes the default dir.

## Recommended fix (deferred — needs its own validated PR)

A single root `tests/conftest.py` **autouse** fixture that isolates the default
engine-state dir per test, fixing all ~340 sites at once instead of editing each:

```python
@pytest.fixture(autouse=True)
def _isolate_default_engine_state(tmp_path, monkeypatch):
    import engine_state
    # _DEFAULT_DIR is bound at import, so monkeypatch the module attribute (not
    # just the env var) for in-process runtimes:
    monkeypatch.setattr(engine_state, "_DEFAULT_DIR", tmp_path / "engine_state")
    # ...and set the env var for subprocess/CLI tests that re-import:
    monkeypatch.setenv("CORE_ENGINE_STATE_DIR", str(tmp_path / "engine_state"))
```

Fixture requirements / acceptance criteria for that PR:

1. **Monkeypatch `engine_state._DEFAULT_DIR`** — it is import-time bound, so an
   env var alone does not redirect already-imported in-process runtimes.
2. **Also set `CORE_ENGINE_STATE_DIR`** (or the equivalent) so subprocess/CLI
   tests that re-import in a child process inherit the isolation.
3. **Preserve tests that intentionally verify default-dir behaviour** — opt them
   out via a marker (e.g. `@pytest.mark.uses_default_engine_state`) or an explicit
   override, rather than silently changing their meaning.
4. **Broad/full-suite comparison against the known baseline reds** — the fixture
   changes default behaviour for all 469 constructions, so the PR must run the
   full suite and confirm it surfaces no *new* failures beyond the documented
   ~31 pre-existing reds on `main` (`core test --suite full`). Any genuinely new
   failure is a hidden inter-test dependency to fix, not to mask.

## Why deferred, not bundled

The brief is safe and immediately useful (documents the hazard + the rule). The
fixture, though small in code, changes default behaviour suite-wide and so must
be validated against the full suite — a deliberate cost that belongs in its own
PR rather than riding on identity-doctrine or hygiene-doc work.
