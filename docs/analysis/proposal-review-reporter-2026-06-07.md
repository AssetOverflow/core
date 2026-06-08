# Proposal review reporter — boundary ledger (RPT)

**Module:** `core/proposal_review/` · **CLI:** `python -m core.proposal_review`
**As of:** 2026-06-07, on the contemplation-batch main (N1–N6 merged).

A **read-only** reporter that surfaces the comprehension-failure proposals emitted by the
contemplation pass (N5/N6) so they become a reviewable queue instead of inert files. It closes
the growth loop **without** crossing into self-modification:

```text
failure → family → proposal_only artifact → review visibility → human/actionable queue
```

## What it is — and is not

> **This is L10-adjacent, not L10. It is a proposal review reporter, not an idle loop.**

| It DOES | It does NOT |
|---|---|
| read `teaching/proposals/comprehension_failures/*.json` | advance the teaching loop |
| validate + report (deterministic summary) | ratify anything |
| **independently verify** every artifact is inert | mount anything |
| flag malformed / unsafe artifacts | modify any reader |
| exit non-zero on a safety violation | write/move/delete any file (it mutates nothing) |
| — | affect serving in any way |

## Relationship to `ChatRuntime.idle_tick`

`ChatRuntime.idle_tick()` (L11, chat/runtime.py) **remains the only `idle_tick`.** It *writes*
proposals over a **different** stream — the reviewed-learning flywheel's discovery backlog →
the persistent proposal log in the engine-state dir. This reporter *reads* the **comprehension_failures**
stream and reports. Different stream, different verb (write vs read). To avoid the ambiguity of a
second "idle tick" / parallel path, this is a standalone reporter with its own name.

A clean **future** PR may call this reporter from `idle_tick` as a **read-only sub-pass** (surface
pending comprehension-proposals alongside the learning passes) — writing only a summary to the
existing engine-state report surface, never mutating proposal artifacts, never ratifying.

## Components

| Phase | Module | Role |
|---|---|---|
| RPT-a | `scan.py`, `model.py` | read `*.json` → typed `PendingProposal`; flag `MalformedArtifact` |
| RPT-b | `report.py` | deterministic summary (total / by family / by status / malformed / review-needed) |
| RPT-c | `safety.py`, `__main__.py` | independent safety dry-check + read-only CLI |
| RPT-d | this doc | the boundary ledger |

## The safety dry-check (the load-bearing part)

The reporter's value is not just visibility — it is **verification**. The dry-check confirms,
without trusting the emitter, that every artifact is inert:

```text
status == "proposal_only"
mounted == false
requires_review == true
content-address consistent: filename == sha256(failure_family : problem_text_sha256)
path under the sink
no malformed (unverifiable) file
no serving-path module imports/reads the sink
```

Each assertion is proven meaningful-fail in the tests; the CLI exits non-zero on any violation.

## Determinism note

The proposal artifacts are **content-addressed and carry no timestamp** (the emitter is clock-free
so the same failure is idempotent). The report is therefore fully deterministic, and **time-based
"oldest/newest" is intentionally omitted** — an honest temporal order is not in the data, only in
non-deterministic filesystem mtime. If a temporal queue is ever wanted, it must come from a
separate, clearly-non-deterministic index, not from the report.

## After this lands

The natural next step is **Option A**: wire this reporter into `ChatRuntime.idle_tick()` as a
read-only sub-pass (summary only, no mutation, no ratify) — connecting the growth organ to the
already-existing idle mechanism without changing learning semantics. Option B (R3 capability
families: rates / time / state) is the other branch. The always-on heartbeat over real uptime —
the actual lived-spine gap — remains separate and unbuilt; this reporter does not claim it.
