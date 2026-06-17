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

## Recommended determinism / teaching regression invocation (post-Claim-B hardening of CLOSE yardstick)

After any change touching CLOSE flywheel, idle_tick, realize_derived, consolidate_determinations, vault recall of realized facts, determine(), or the derived close proposal bridge, run the hardened yardstick as part of your determinism regression and anti-regression verification:

```bash
uv run python -m evals.close_derived_climb
uv run python -m pytest tests/test_derived_close_proposals.py tests/test_architectural_invariants.py -q
```

(Also available via `core demo anti-regression` which now embeds the yardstick — see below.)

This is the canonical "standard verification story" invocation for the CLOSE autonomous growth surface. It is the direct follow-up to the Claim-B hardening (#791) and makes the improved measurement recurring rather than isolated.

**What the hardened yardstick now exercises and measures (Claim B):**
- Real `ChatRuntime.idle_tick()` + `IdleTickResult.derived_close_proposals_emitted` (proposal flag gating via the lived runtime path, not a simulation).
- Explicit `determine()` calls on the post-fixed-point positive probes, asserting `Determined(True, rule='direct')` ("semantic_positives_determined_direct").
- `content_replay_checksum` covering canonical closure sets (with structure_key, Derivation, and premise_structure_keys) and full proposal bodies for exact-trajectory fidelity.
- Retained Claim A guarantees: strict/monotone growth (1/5/8), wrong_total == 0, negatives and excluded predicates refused, full determinism, hermetic (no serving, no ratification, SPECULATIVE/proposal_only only, all INV-30/31 etc. preserved).

See:
- `evals/close_derived_climb/contract.md` (metrics, scenarios, "no side effects")
- `docs/analysis/close-derived-climb-yardstick-claim-b-ratification-2026-06-16.md` (the hardening ratification)
- `docs/analysis/integrate-hardened-close-yardstick-determinism-teaching-regression-ratification-2026-06-16.md` (this integration ratification + "why only correct path")
- `docs/runtime_contracts.md` (determination surface contract exercised by the semantic asserts)
- `docs/evals/anti_regression_demo.md` (the anti-regression demo now runs the yardstick)
- `tests/test_anti_regression_demo.py` (contract test that pins the embedding)
- `Makefile` (comments under test lanes point here)

The yardstick itself remains hermetic per the rules in this document (fresh runtimes, internal temps only for proposal sink during flag test). It introduces no new writers to engine_state/, teaching/proposals/, or evals reports.

This integration (documentation promotion into the lanes + hermetic execution inside the anti-regression demo) is the highest-leverage way to ensure the project actually benefits from the hardened Claim-B measurement surface on every relevant regression run.
