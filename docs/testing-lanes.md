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

## Dedicated CLOSE Flywheel Regression Surface (Claim-B Level)

This is the **clearly named, intentional, high-signal regression surface** for the CLOSE flywheel at full Claim-B strength. It is positioned exclusively for heavier determinism regressions and teaching/anti-regression verification flows — **not** for fast local development or default CI runs.

### Invocation (the dedicated surface)
```bash
make test-close-flywheel
```

Or the equivalent explicit commands (the make target is the canonical named surface):
```bash
uv run python -m evals.close_derived_climb
uv run python -m pytest tests/test_derived_close_proposals.py tests/test_architectural_invariants.py tests/test_anti_regression_demo.py -q
```

The inclusion of the anti-regression test ensures the hermetic embedding of the yardstick (from #792) participates, so the surface exercises both the direct yardstick and the integrated teaching demo path.

### Purpose
Provide a coherent, auditable regression target that exercises the full lived CLOSE flywheel (comprehend → realize → determine → CLOSE consolidate → proposal emission under the review_derived_close_proposals flag → measured climb) using the hardened Claim-B yardstick (`evals/close_derived_climb`). This surface makes the improved measurement (post-#791) a first-class, recurring part of heavy verification without polluting fast or generic lanes.

### What the surface exercises and measures (Claim B)
- Real `ChatRuntime.idle_tick()` + `IdleTickResult.derived_close_proposals_emitted` (proposal flag gating via the *lived* runtime path, not simulation).
- Explicit `determine()` calls on post-fixed-point positive probes, asserting `Determined(True, rule='direct')` ("semantic_positives_determined_direct").
- `content_replay_checksum` covering canonical closure sets (structure_key + Derivation with premise_structure_keys) and proposal bodies for exact-trajectory fidelity.
- Retained Claim A guarantees: strict/monotone growth (1→5→8 on is-a + relational-transitive scenarios), `wrong_total == 0` (negatives and excluded predicates refused), full determinism and replayability, hermetic execution (no serving, no ratification, SPECULATIVE-only realization, proposal-only boundaries, all INV-21/29/30/31 etc. preserved).

Scenarios: is-a (member/subset) climb, less_than relational climb, before_event temporal climb, parent/sibling negatives refused.

### Expected runtime characteristics
Heavyweight (~60s+ on 10-core macOS with CORE_BACKEND=numpy; driven by multiple real `ChatRuntime` constructions + idle_tick to fixed point + climbs). Comparable to other proof-scale fixtures (e.g. the 975s inner-loop phase2 outlier). Intended for deliberate, post-change verification in heavier determinism reruns and teaching/anti-regression flows — not for rapid iteration or every push.

### Hermeticity guarantees
- Fresh `ChatRuntime(no_load_state=True)` per scenario.
- Internal `TemporaryDirectory` only for proposal sink isolation during the flag test (DEFAULT_SINK patch is restored).
- Zero writes to `engine_state/`, active teaching corpus, `teaching/proposals/`, or shared evals reports.
- All existing anti-regression demo guarantees (active corpus byte-identical pre/post) continue to hold.
- Complies with the hermeticity rules in this document (see "Follow-ups (separate PRs)" and xdist notes). The surface itself introduces no new race surfaces.

### Alignment with Engineering Pillars (Whitepaper.md §IV)
- **Mechanical Sympathy**: Understands and respects the cost model. The surface does real runtime work (ChatRuntime turns, consolidation, derivation). It is kept out of fast paths, generic suites, and CI so the machine is not forced to pay the price for every build.
- **Semantic Rigor**: The surface has a precise, non-negotiable name and contract. "CLOSE Flywheel (Claim-B)" means exactly the lived behaviors listed above — no approximations, no "good enough" inclusion, no silent embedding of the yardstick into unrelated lanes. Every term (IdleTickResult, rule='direct', content_replay_checksum, proposal_only, etc.) retains its defined meaning.
- **Third Door**: The world offered two obvious doors — (1) add the yardstick to fast/full/slow or a generic "determinism" suite (violates positioning, mechanical sympathy, and out-of-scope rules), or (2) invent a new CLI command or heavy test infrastructure. This surface takes the third door: a minimal, composable `make test-close-flywheel` target (using the project's existing lane mechanism) + authoritative documentation that elevates the yardstick and the #792 embedding into a named, intentional regression surface built from first principles.

See the ratification for the full justification of why this (and only this) approach satisfies the brief while aligning with the pillars:
- `docs/analysis/close-flywheel-dedicated-regression-surface-ratification-2026-06-16.md`

### References
- Yardstick contract + implementation: `evals/close_derived_climb/contract.md` (run with `uv run python -m ...`; metrics, scenarios, "no side effects")
- Claim-B hardening: `docs/analysis/close-derived-climb-yardstick-claim-b-ratification-2026-06-16.md` (#791)
- Prior integration (foundation for the embedding): `docs/analysis/integrate-hardened-close-yardstick-determinism-teaching-regression-ratification-2026-06-16.md` (#792)
- Anti-regression demo (the primary high-value teaching/anti-regression flow that now participates in the surface): `docs/evals/anti_regression_demo.md`, `evals/anti_regression/run_demo.py`, `tests/test_anti_regression_demo.py`
- Determination surface exercised by the semantic asserts: `docs/runtime_contracts.md`
- `Makefile` (the `test-close-flywheel` target is the named entry point)
- Related heavy determinism context: the "Finding: the 975s `test_inner_loop_phase2` outlier" and inner-loop suite discussion above

The surface remains hermetic and additive. All prior invariants and the #792 embedding are unchanged.

### How the surface builds on prior work
The #792 "recommended invocation" and hermetic embedding into the anti-regression demo provided the recurring protection. This dedicated surface gives that work a clear name, a primary make target, full pillar-aligned documentation, and explicit positioning as the heavy CLOSE flywheel regression lane. The anti-regression test is deliberately included in the surface so that running `make test-close-flywheel` also verifies the integrated teaching path.

(Operators doing heavy CLOSE-related work after #788/#789/#791 should run this surface as part of their determinism and teaching verification.)
