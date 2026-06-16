# Testing lanes — fast / slow / full

The full pytest suite is ~10,600 tests and ~73 min serial.  A small set of
heavyweight tests dominates that wall-clock, so we classify them and offer a
**fast lane** for local development.  Classification is empirical
test-infrastructure metadata, so it lives in one auditable place
(`conftest.py`), beside the `QUARANTINE` registry — not as `@pytest.mark.slow`
decorators spread across ~24 files.

## Lanes

| Lane | Command | What it runs |
|---|---|---|
| **fast** | `make test-fast` → `pytest -m "not quarantine and not slow"` | everything except the slow registry |
| **slow** | `make test-slow` → `pytest -m "slow and not quarantine"` | only the heavyweight registry |
| **full** | `make test-full` → `pytest -m "not quarantine"` | everything (what CI runs) |

The marker is **classification only** — it never skips.  `-m slow` *selects* the
slow tests; you choose a lane with an explicit marker expression.  Plain
`pytest` (no `-m`) still runs the full suite.

CI is unchanged: `.github/workflows/smoke.yml` and `full-pytest.yml` both run
`-m "not quarantine"`, which includes the slow tests — so the split costs no CI
coverage.

## Measured timings (10-core macOS, `CORE_BACKEND=numpy`)

| Lane | Serial | Parallel (`-n auto`) |
|---|---|---|
| full | 73 min | 25 min |
| fast | ~26 min | **9.5 min** (9,590 passed) |

Combined (split + parallel) = **73 → 9.5 min (7.7×)**.  The parallel fast lane
scales ~5.7× because it excludes the 975s parallel-floor monster (see below);
the full suite only reaches 2.9× because that one test pins a worker for 16 min.

`-n auto` is **not** wired into the `make` targets yet — see *Follow-up: xdist*.

## The slow registry (`conftest.py`)

Two registries, by cost shape:

- **`SLOW_FILES`** — whole-file: the cost is carried by a module/session-scoped
  fixture, so marking one test is insufficient (skipping it just shifts the
  fixture cost to the next test that requests it).  10 files.
- **`SLOW_TESTS`** — exact nodeids: mixed files where only specific tests are
  soak/bench scale; the file's fast predicate/unit tests stay in the fast lane.
  26 tests across 14 files.

**Honest accounting** — the registry marks **912** of 10,596 tests slow.  801 of
those are `test_cognition_eval_register_matrix.py` (a per-register × invariant
eval matrix: many cheap parametrized assertions gated behind expensive
per-register module-fixture setups).  It is classified whole-file because the
cost is in the module fixture, but be aware the fast lane therefore omits the
register-matrix coverage; CI's full lane still runs it.

## Finding: the 975s `test_inner_loop_phase2` outlier

`test_inner_loop_phase2.py::TestCausalAttribution::test_null_control_matches_boundary_only`
showed a **975s (16 min) setup** — the single largest test, and the parallel
floor for the whole suite.

Probed: it is **expected proof-scale work, not a bug or runaway**.  The cost is a
module-scoped `phase2_report` fixture that runs the FSC corpus (9 cases: 1
`public/v1` + 8 `dev`) through `run_lane`, which executes **4 conditions + 4
determinism reruns = 8 full real-runtime pipeline turns per case**, plus a fresh
`ChatRuntime()` per case (~5s each).  9 × 8 heavy pipeline turns ≈ 975s.  The
fixture is shared across the file's 5 tests, so the cost is paid once.

A possible optimization exists — share the primed runtime across the 4 conditions
instead of reconstructing — but it touches the runner's determinism contract, so
it is deferred, not done here.

## Follow-ups (separate PRs)

1. **xdist by default.**  The fast/full lanes are *not* xdist-hermetic yet:
   fresh-env-dict subprocess tests (`tests/formation/*`, `test_identity_packs`)
   write to the repo `engine_state/` dir, and other tests write
   `evals/.../report.json` and `teaching/proposals/` — these **race** under
   parallel workers (e.g. `test_workbench_replay::test_replay_leaves_no_trace`
   fails under `-n auto`, passes serially).  Isolate those writers, then wire
   `-n auto` into `make test-fast` / `test-full`.  This is the same hermeticity
   theme as `docs/issues/default-engine-state-test-hygiene.md`.
2. **Warm-runtime fixture.**  The fast lane's remaining ~9.5 min (parallel) is a
   long tail of 1–15s `ChatRuntime` constructions, not outliers.  A
   shared/session-scoped warm-runtime fixture for read-only tests would cut this
   further.
