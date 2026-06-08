# Proposal-review idle integration — boundary ledger (IT)

**As of:** 2026-06-08 · `core/config.py` `review_pending_proposals` · `ChatRuntime.idle_tick`
**Builds on:** the read-only reporter (`core/proposal_review/`, RPT — see
`proposal-review-reporter-2026-06-07.md`).

Wires the read-only proposal-review reporter into the **existing** `ChatRuntime.idle_tick()` as
an **optional, gated, read-only sub-pass**, so an idle engine can surface pending
comprehension-failure review obligations alongside its existing learning passes — completing the
loop *without* crossing into self-modification:

```text
comprehension failure → proposal_only artifact → proposal-review report → idle_tick read-only visibility
```

## The boundary (pinned)

> **Existing `idle_tick` remains the only `idle_tick`. Proposal review is read-only. This is NOT
> the L10 always-on heartbeat. It does NOT advance learning. It only surfaces review obligations.**

| It DOES | It does NOT |
|---|---|
| run a read-only sub-pass when `review_pending_proposals` is on | exist as a second idle loop / daemon |
| surface `idle_summary()` in `IdleTickResult.proposal_review` | mutate / move / delete any artifact |
| capture a reporter failure as `safe=False` | set `did_work` → so it never checkpoints |
| stay disabled (field `None`) by default | advance learning / ratify / mount / modify readers |
| — | become the always-on heartbeat over real uptime |

## How it works (IT-b)

- **Gate:** `RuntimeConfig.review_pending_proposals: bool = False` (opt-in, same pattern as
  `consolidate_determinations` / `persist_session_state`).
- **Sub-pass:** after the consolidation pass, *iff* gated on, `idle_tick` calls the pure
  `core.proposal_review.idle_summary()` (scan → report → dry-check) and stores the result in the
  additive optional `IdleTickResult.proposal_review`.
- **Failure isolation:** a reporter exception is caught and surfaced as
  `ProposalReviewIdleSummary(safe=False, …, errors=("proposal_review_failed:<type>",))` — visible,
  never propagated, so it cannot corrupt the tick's state or return.
- **No state change:** the sub-pass never sets `did_work`, so the existing checkpoint logic is
  untouched; default-off leaves `IdleTickResult` byte-identical for existing callers.
- Contract documented in `docs/runtime_contracts.md`; contract tests in
  `tests/test_idle_proposal_review.py` (default-off shape, enabled summary, captured exception,
  no-checkpoint, other-passes-unperturbed) plus the unchanged existing idle suites.

## What this is NOT — and what's next

This is **L10-adjacent, not L10.** The always-on heartbeat over real indefinite uptime — a process
that *drives* `idle_tick` on its own — remains the separate, unbuilt lived-spine frontier and is
not claimed here. The agreed next capability step is **R3 (rates / time / state systems)**, not
more reporter plumbing. The chain now stands:

```text
R1/R2 organs → comprehension contemplation → proposal-review surface → idle_tick read-only visibility → R3
```
