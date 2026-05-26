# Master plan — post-substrate-audit

**Authored:** 2026-05-24 (end-of-day, PST) — call it a night, fresh AM.
**Author intent:** carry the strategic plan + active-PR snapshot across the
session boundary so morning-self picks up cleanly.

> **2026-05-26 amendment** — Phases 1–5 substantially complete.  Math
> architecture corridor closed end-to-end (Phase A → B → C → D + operator
> ratification, ADR-0163); first measurable GSM8K lift produced
> (`correct: 0 → 3, wrong: 0 unchanged`).  Workbench surface operational
> end-to-end (W-026 API + W-027 shell + W-028 chat surface).  HITL queue
> read-only CLI shipped (ADR-0161 Step 1).  See
> [SESSION-2026-05-26-corridor-closure.md](sessions/SESSION-2026-05-26-corridor-closure.md)
> for the day's full ledger (15 merges + 1 issue).  Sections below remain
> as the historical 2026-05-24 plan; **next-moves are in the session
> recap, not here**.

---

## Three guiding rules

1. **"Fully wired"** = every `W-*` entry in [substrate-liveness-ratchet](audit/substrate-liveness-ratchet.md) CLOSED. When the registry is empty, the design executes as written.
2. **Thesis check on every move**: per [[thesis-decoding-not-generating]] — does this teach the engine to find better, or just store another found thing? Only the former clears the bar.
3. **L10 is the load-bearing decision.** It gates W-003, W-007, W-009, W-017, W-018, and the recognizer-storage ADR. Wrong shape locks in wrong architecture for the rest of the cascade.

---

## End-of-day snapshot (2026-05-24)

### Active in flight

| PR | Branch | State | Blocker |
|----|--------|-------|---------|
| **#261** (B speedup) | `chore/test-speed-b-extract-lane-runners` | CI rerunning after timeout bump + test_lane_sha_verifier fix | Wait for `verify pinned lane SHAs` to go green |
| **(unopened)** Gate | `ci/full-pytest-gate-quarantine-markers` (pushed, no PR) | Locally verified: 6657 pass / 0 unexpected fail / 76 skip / 49 quarantine | Open PR **after #261 merges** (otherwise gate's CI hits pre-fix lane-shas state) |

### Closed today (5 W-* + 5 PRs)

- **W-004** — vault E2 re-thaw (PR #251)
- **W-015** — `_slerp_toward` → rotor-geodesic anchor pull (PR #255)
- **W-016** — vault probe in discovery loop (PR #257)
- **W-011** — recognition refusal propagation (PR #258, paired)
- **W-012** — `InnerLoopExhaustion` caught in ChatRuntime (PR #258, paired)
- Ratchet v5 (PR #260) — registry updated

### Quarantine registry (49 tests)

Cluster A (4) — ADR ledger drift, one-token extensions, shape of W-002
Cluster B (15) — surface decoration drift (`pack-grounded (<pack>)` suffix)
Cluster C (27) — lane/runner metric drift (some are real regressions)
Cluster D (2) — CLI/internal API drift
Cluster E (1) — pytest-xdist parallel-execution incompatibility (`test_articulation_bench::test_footprint_emits_samples_and_bounds`)

All confirmed pre-existing via bisect against `c1a1b7a` (pre-W-*-work commit). Today's 5 closures introduced **zero** new failures. Cluster E is the lone xdist-induced regression — caused by gate's `-n 4` choice, not by today's substantive work.

### Resumption order in AM

1. **First**: check PR #261's CI re-run status. If green, merge. If red, debug from CI logs.
2. **Second**: rebase `ci/full-pytest-gate-quarantine-markers` onto post-#261 main; open as PR.
3. **Third**: read this plan top-to-bottom to re-load context.
4. **Fourth**: Phase 2 work — five operator decisions queued (W-006, W-010, W-013, W-014, W-019). Each ~30 min.

---

## Phase 1 — Hygiene & honesty (today, in flight)

- **B PR #261** — extract `math_teaching_corpus` lane from pytest into CI lane SHAs (−9 min suite time, ~30% reduction)
- **Gate PR** (pending #261) — `conftest.py` QUARANTINE registry of 49 known-failing tests + new `full-pytest.yml` workflow running `pytest -m "not quarantine" -n 4`
- **5 W-* closures** — W-004, W-011, W-012, W-015, W-016

**Outcome:** test debt is **visible and ratcheted**; speed recovered; the audit-derived registry is operational. We can ship the next dozen PRs without flying blind.

**Follow-up queued (task #7):** small PR migrating `lane-shas.yml` from plain `pip` to `uv` to match the gate's precedent. Per [[feedback-use-uv-consistently]].

---

## Phase 2 — Operator decisions (small, you-decide, fast)

Five short calls clear five `W-*` entries with minimal-to-no engineering.

| Item | Decision needed | Resolution paths |
|------|-----------------|------------------|
| **W-006** | Pack readback rules: wire or delete? | (a) wire `packs/<lang>/readback_rules.py` into surface generation per original intent; (b) accept that `generate/realizer.py` superseded the design and DELETE the dormant modules |
| **W-010** | L4 recognition vocab: intentional token-level or wire L3? | (a) document as intentional in ADR-0143 amendment (no code change); (b) wire `VocabManifold` consumption into `derive_recognizer()` via new ADR (larger) |
| **W-013** | `core/cognition/explain.py`: wire / relocate / delete | (a) wire into `core chat` for "explain this turn" REPL; (b) move to `evals/` if offline audit tool; (c) delete |
| **W-014** | `core/cognition/provenance.py`: wire / relocate / delete | (a) wire into live turn result for per-turn provenance; (b) relocate to `evals/`; (c) leave as-is, document as evals-only |
| **W-019** | `teaching/from_miner.py` + `from_curriculum.py`: CLI / runtime / library? | (a) wire CLI: `core teaching propose --from-miner <dir>` (smallest fix); (b) wire into W-017 promotion pipeline (later, larger); (c) leave as test-live library |

Each ~30 min thought + small PR. Mostly cleanup-as-you-find calls per [[feedback-cleanup-as-you-find]].

---

## Phase 3 — Test debt paydown

Goal: shrink `QUARANTINE` from 49 → 0. One PR per cluster.

### Sequence (easiest → hardest)

1. **Cluster A** (4 tests, ADR ledger drift) — one-token extensions, same shape as W-002 (#240). **~1 hour.**
2. **Cluster D** (2 tests, CLI/API drift) — quick reads, quick fixes. **~30 min.**
3. **Cluster E** (1 test, xdist incompatibility) — rewrite to measure only self-allocations OR mark `@pytest.mark.xdist_group("serial")`. **~30 min.**
4. **Cluster B** (15 tests, surface decoration drift) — mechanical: update assertions to use `in` containment or accept the `pack-grounded (<pack>)` suffix. **~3-4 hours.**
5. **Cluster C** (27 tests, lane metric drift) — **the dangerous one.** Each test needs investigation: stale threshold (re-pin) vs real quality regression (fix the regression). Some will surface honest engine-quality problems we've been blind to. Expect 1-3 PRs worth of work to surface what's stale vs what's broken.

By end of Phase 3, the gate enforces zero quarantine and every contract pinned in tests is a contract the engine actually holds.

---

## Phase 4 — THE load-bearing decision: L10 runtime model

This is the architectural commitment that gates W-003, W-007, W-009, W-017, W-018.
**Until L10 commits, the rest of the audit registry can't sequence.**

Scope already landed (#236). What's left:

- **Spike**: prove a long-lived process can hold field state + vault + session continuity without leak/drift across 24+ hours of turns
- **ADR (or cluster)**: pick process shape A/B/C, state partitioning, reboot recovery model, HITL async substrate
- **First implementation**: minimal long-lived runtime that survives the spike's stress test

This is the **riskiest single decision in the whole plan**. Wrong shape locks in wrong architecture for everything downstream.

**Discipline note** (per [[feedback-scope-time-is-cheap]]): treat L10's spike with the same rigor as the substrate-liveness audit — multi-resolution scope, agent-cross-checked, before writing any committing ADR. The audit just demonstrated what "do it right" looks like; L10 deserves the same.

**Open offer**: draft a v1 of the L10 *scope-of-scope* (what questions the spike must answer) once Phase 1 lands. Operator's call to take.

---

## Phase 5 — The L10 cascade (after Phase 4)

Each is small **once L10 commits process shape**:

| Item | What lands | Depends on |
|------|-----------|------------|
| **W-003** | `VaultPromotionPolicy` wired into runtime promotion path | L10 process shape |
| **Recognizer-storage ADR** | Where recognizers live across turns/sessions/reboots | L10 + W-003 |
| **W-007** | `DerivedRecognizer` integration into `CognitiveTurnPipeline` | Recognizer-storage ADR |
| **W-009** | HITL async queue (operator reviews while engine serves turns) | L10 + drop-off sibling ADR |
| **W-017** | Automated T1/T2 → T3 promotion | W-009 (W-016 portion already satisfied by #257) |
| **W-018** | Autonomous contemplation loop | L10 |

When all six land + recognizer-storage answers, **the audit registry is all CLOSED.** The design executes.

---

## Phase 6 — The "decodes, not generates" milestone

This is where smashing expectations actually lives. With Phase 5 done, CORE demonstrably:

- **Runs forever** (Phase 4) — capability accumulates across invocations, not per-turn
- **Recognizes deterministically** (W-007) — turn loop dispatches through anti-unifier
- **Promotes evidence automatically** (W-017) — T1 vault → T3 reviewed corpus on HITL ratification
- **Learns from refusals** (W-011 + recognizer wiring) — typed refusals become curriculum candidates
- **Contemplates autonomously** (W-018) — between-turn slack becomes hypothesis exploration

That set of behaviors is **not what a transformer-based chatbot can do**. That's the architectural distinctiveness moment. Patent territory.

---

## Phase 7 — Validation & projection

After Phase 6:

- **Patent filings** — operator deferred until cleanup complete; Phase 6 is the cue
- **Rust backend parity** — CLAUDE.md work-sequencing #5, was waiting on Python semantics being locked by tests; Phase 3 locks them
- **Curriculum expansion** — CLAUDE.md #6; now safe because eval/replay/calibration are deterministic
- **Long-context benchmarks** vs transformer baselines — NIAH probe exists at `evals/long_context_cost/`; concrete "we recall at N=100k where they hallucinate" demonstrations

---

## What "smashing expectations" honestly means

Two flavors, worth distinguishing:

1. **Architectural distinctiveness** (Phase 6) — CORE does things transformers structurally can't. Replay-equivalent, identity-preserving, audit-trailed, exact-recall. **This is achievable on the path above.**
2. **Benchmark wins** (GSM8k, etc.) — possible but requires Phase 7's curriculum expansion AND a real claim on what we're testing. Cluster C in Phase 3 will tell us whether current grounding accuracy is actually competitive or whether we've been measuring with stale thresholds.

**The thesis (decodes, not generates) makes (1) the legitimate target. (2) is downstream validation, not the goal. Aim at (1); (2) follows.**

---

## The one critical risk

**L10 is the single point of failure.** If we commit to the wrong process shape, every Phase 5 item gets re-done. Treat L10's spike with the same rigor as the substrate-liveness audit — multi-resolution scope, agent-cross-checked, before writing any committing ADR.

---

## Cross-references

- [substrate-liveness-ratchet](audit/substrate-liveness-ratchet.md) — wiring debt registry (v5)
- [substrate-liveness-registry](audit/substrate-liveness-registry.md) — per-layer audit evidence
- [test-debt-quarantine](test-debt-quarantine.md) — pytest QUARANTINE registry (49 tests, 5 clusters)
- [L10-runtime-model-scope](decisions/L10-runtime-model-scope.md) — gates W-003, W-007, W-009
- [recognizer-storage-scope](decisions/recognizer-storage-scope.md) — gates W-007
- [substrate-liveness-audit-scope](decisions/substrate-liveness-audit-scope.md) — defines audit shape

## Memory cross-references

- [[thesis-decoding-not-generating]] — load-bearing project thesis
- [[feedback-adr-cross-reference-discipline]] — grep ALL existing ADRs before any new scope
- [[feedback-cleanup-as-you-find]] — applies to Phase 2 W-006/W-013/W-014
- [[feedback-scope-time-is-cheap]] — applies to Phase 4 L10
- [[feedback-address-critiques-dont-waive]] — if a critique surfaces in any phase, fix don't waive
- [[feedback-parallel-agent-worktrees]] — for any parallel-agent dispatch
- [[feedback-use-uv-consistently]] — `uv venv` / `uv pip install` / `uv run`, never `python3 -m venv` / `--break-system-packages`
- [[project-engine-identity-candidate]] — DNA-analog concept SHELVED; un-shelve trigger = L10 sub-question 3 (cross-reboot identity verification)

## Tonight's lessons (in case they surface tomorrow)

1. **Lane subprocess timeout (300s) was too tight** for any lane that takes more than ~5 min on CI. Bumped to 900s in #261's third commit. Future lane additions should consider their CI-runtime cost.
2. **pytest-xdist `-n 4` surfaces parallel-execution incompatibilities.** First example was `test_articulation_bench` (memory-RSS measurement). Cluster E is the place to track these; consider whether the gate workflow should drop to `-n 2` if more parallel-flake surfaces.
3. **Wrong-branch PR pattern** continues to hit subagents. Seen earlier with #256 (Sonnet's W-016 on wrong branch) and earlier with Gemini's L2/L3/L5/L7. Every parallel-agent brief should emphasize the rebase-onto-current-main step before PR creation.
4. **`/tmp/<scratch-venv>`** was a workaround for PEP 668 — sourced [[feedback-use-uv-consistently]]. The CI uses uv (the gate workflow already sets the precedent); the existing lane-shas workflow still uses pip and gets migrated in task #7.
