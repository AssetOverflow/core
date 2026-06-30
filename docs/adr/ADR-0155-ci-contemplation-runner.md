# ADR-0155 — CI contemplation runner (W-021)

Status: scoping
Date: 2026-05-25

## Context

ADR-0150 (W-018) made contemplation autonomous at checkpoint.
ADR-0151 (W-017) auto-proposes from enriched candidates at load.
ADR-0152 (W-019) closes the engine-authored proposal loop.
Operator (Shay) currently runs sessions from a single workstation
with intermittent connectivity.

A GitHub Actions runner is deterministic Linux compute that the
operator can trigger from anywhere. Running contemplation cycles on
that compute amortizes wall-clock contemplation cost without
sacrificing CORE's HITL doctrine — provided the output is gated
through pull-request review before any corpus mutation.

Budget on GitHub Pro (Student): 3,000 Actions minutes/month on
Linux runners (1× multiplier). A 10-min contemplation run every 4
hours costs ~1,800 min/mo (60% of budget); nightly costs ~900 min.

## Decision

Add `.github/workflows/contemplation.yml`:

- Triggers: `schedule:` (nightly at 09:00 UTC = 01:00 PST) and
  `workflow_dispatch:` (manual).
- Soft kill switch: skips when repo variable `CONTEMPLATION_ENABLED`
  is not `"true"`. Operator toggles in repo settings without
  editing the workflow.
- Runs `core demo learning-arc --json`, writes the report to
  `contemplation/runs/YYYY-MM-DD-HHMMSS.json`.
- Opens a PR against `main` with the new run via
  `peter-evans/create-pull-request@v7`. Operator review on the PR
  is the ratification gate.
- Concurrency group prevents overlapping runs.

The CI runner **never** commits directly to `main`, **never**
mutates `corpora/`, **never** registers recognizers, **never**
ratifies proposals. It only writes a report file under
`contemplation/runs/` and proposes the diff via PR.

## Invariants preserved

- ADR-0150 HITL gate: every proposal still passes through operator
  review. CI just stages the candidate.
- Determinism (CLAUDE.md): `ubuntu-latest` is consistent enough
  for trace_hash equality. First-run verification: compare a local
  `core demo learning-arc --json` against the CI output for the
  same commit SHA; they must byte-match on the
  `proposal_id` / `trace_hash` fields. If they diverge, the
  underlying determinism gap is a substrate bug to fix, not a
  reason to relax the invariant.
- No new trust boundary on disk: CI writes only to
  `contemplation/runs/` (a new directory dedicated to CI output);
  existing trust boundaries are unchanged.
- Acceptable Use Policy: output is a project artifact (proposals
  about CORE's corpus), so contemplation runs are defensibly
  "production, testing, deployment, or publication of the software
  project" per GitHub AUP §5. Idle / unbounded compute is not
  scheduled.

## Trust boundary

The CI workflow has `contents: write` and `pull-requests: write`
on a branch named `contemplation/<date>`. It cannot push to `main`
(protected branch). The HITL surface is the PR review UI —
identical to existing operator workflow for human-authored
proposals.

## Out of scope

- **Persisted engine state across CI runs.** Each run starts from
  the committed corpus and produces a one-shot report. A future
  ADR may track engine-state evolution across runs by committing
  `engine_state/` under a CI-only branch, but only after operator
  review on each step.
- **Auto-merge.** Never. Every CI proposal stays open until the
  operator merges or closes.
- **Cross-runner determinism.** Pinning to `ubuntu-latest` is
  acceptable; switching runner classes invalidates the
  trace_hash equality check.
- **Recognizer growth.** ADR-0154 enables the registry to grow
  from live traffic, but CI runs do not produce traffic the
  registry should learn from (they are synthetic exercises). The
  CI runtime sets the producer queue but does not persist
  derived recognizers to the committed engine_state.

## Validation

- First run (manual `workflow_dispatch`) produces a PR with a
  `contemplation/runs/<date>.json` file.
- Local + CI runs at the same SHA produce byte-identical
  `proposal_id` and `trace_hash` fields (manual check on first
  enable).
- Workflow exits 0 with no PR created when no proposal is
  produced (idempotent runs).
- Soft kill: setting `vars.CONTEMPLATION_ENABLED=""` causes the
  job to skip on the next scheduled tick.

## Operator runbook

1. Repo Settings → Secrets and variables → Actions → Variables:
   set `CONTEMPLATION_ENABLED=true`.
2. Actions tab → "contemplation" workflow → "Run workflow" once
   to verify.
3. Watch the resulting PR; review the proposal as you would any
   `core teaching proposals` entry.
4. Merge to accept (proposal becomes part of the audit trail) or
   close to reject.
5. Disable: set `CONTEMPLATION_ENABLED=""` (empty); the workflow
   exits early without consuming meaningful minutes.

## Closure

After this ADR, CORE has a remote compute path for contemplation
that preserves the operator-as-gate invariant. The operator gains
asynchronous contemplation cycles tied to the project's own audit
trail, with no new infrastructure to maintain beyond a single
workflow file.
