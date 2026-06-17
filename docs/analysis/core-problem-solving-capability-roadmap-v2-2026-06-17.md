# CORE Problem-Solving Capability Roadmap v2 — 2026-06-17

**Status:** Living document (post-Gate-A1 calibration update)
**Date:** 2026-06-17
**Context:** Post PR #797 (rate injection), #798 (Grok governance), #799 (Inc3 rate connector), #801–#805 (Inc3 evidence closure, practice-lane monotonic counts, Gate A1 ratification + implementation).

## Overview

This v2 roadmap refines the GSM8K Workstream A path and the broader capability sequencing after the rate and comparative injector closures.

As of 2026-06-17 on `main` @ `bb083004`:

| PR | Status | Role |
|---|---|---|
| #797 | merged | Inc2 narrow rate injection |
| #798 | merged | Grok governance |
| #799 | merged | Inc3 `"one"` rate connector |
| #801 | merged | Inc3 evidence closure lookback |
| #802 | merged | Practice-lane monotonic counts |
| #803 | merged | Gate A1 multiplicative comparative ratification |
| #804 | merged | Test doctrine: score vs truth preservation |
| #805 | merged | Gate A1 multiplicative comparative injection (`bb083004`) |

Live ephemeral train_sample (current code, no `report.json` write): **6 correct / 44 refused / 0 wrong**. Pinned `report.json` remains historical **6/44/0**.

## GSM8K Workstream A — closed increments

- **Inc 1:** reader/recognizer baseline lift (discrete etc.)
- **Inc 2:** frontier measurement + stale doctrine repair + narrow rate injection (PR #797)
- **Inc 3:** `"one"` connector for `rate_with_currency` (PR #799) — **closed** (#801 evidence)
- **Gate A1:** multiplicative entity-comparison comparative injection (PR #805) — **closed**

Injector-frontier closures verified live:

- `rate_with_currency` recognized_no_injection = **0** (Inc3)
- `comparative_with_unit` recognized_no_injection = **0** (Gate A1)

Aggregate proxy unchanged at 6/44/0; refusal reclassification downstream is expected.

## Gate naming (do not conflate)

| Name | Meaning | Status |
|---|---|---|
| **Gate A1** | Multiplicative comparative recognizer injection (`compare_multiplicative` v1 template) | **Closed** (#803 ratification, #805 implementation) |
| **Gate A1b / Comparative-A2** | Additive comparative injection (`compare_additive`, “X more/less than Y”) | Deferred — not Gate A2 |
| **Gate A2 (roadmap)** | Partition / chunking (`unit_partition`, split-into-sections, aggregate-then-divide) | **Ratification candidate pending microscope (Gate A2a)** |
| **Inc4 denom-state** | Rate denominator / hour-kg-cup Initial production | Deferred — not started |

Additive comparative is **not** roadmap Gate A2. Roadmap Gate A2 remains partition/chunking.

## Current hygiene step (this PR)

**Post-Gate-A1 frontier microscope** — docs/tooling only:

- Ephemeral `build_report(cases)` classification of all 44 refusals
- Lookback: `docs/analysis/gsm8k-post-gate-a1-frontier-microscope-2026-06-17.md`
- Tool: `scripts/gsm8k_post_gate_a1_frontier_microscope.py`

**Next ratification candidate:** Gate A2a unit partition / chunking primitive (microscope recommendation; not an implementation decision in this PR).

## Success Criteria (Inc3 + Gate A1 — met)

- Inc3 ratified change merged (#799); evidence closure #801
- Gate A1 ratified (#803) and implemented (#805)
- Live ephemeral: `rate_with_currency` and `comparative_with_unit` no-injection = **0**; wrong = **0**
- Monotonic contract: `correct >= 6`, `refused <= 44`
- Pinned `report.json` historical; no rebaseline without separate ratification
- Inc3 lookback: `docs/analysis/gsm8k-workstream-a-increment-3-lookback-2026-06-17.md`
- Gate A1 lookback: `docs/analysis/gsm8k-workstream-a-gate-a1-comparative-multiplicative-lookback-2026-06-17.md`

## Out of Scope (held)

- Gate A2 partition/chunking **implementation** (microscope first)
- Gate A1b / Comparative-A2 additive comparative **implementation**
- Inc4 denominator-state production
- `report.json` rebaseline, broad recognizer work, sealed-lane movement
- Changes to serving sealed paths, identity, policy, or algebra invariants

## Sequencing after microscope

1. **Ratify** Gate A2a unit partition / chunking primitive (shared narrow primitive — see lookback evidence). Implementation follows ratification only.
2. Preserve wrong=0 and monotonic counts on every future slice.
3. Gate A1b / Comparative-A2 (additive comparative) and Inc4 denom-state remain deferred until separately ratified.
