# Scope: L11 — HITL Async Queue

**Status:** Draft v1 / scope-only (not a decision yet — prerequisite for one)
**Date:** 2026-05-26
**Author:** CORE agents
**Anchor:** [thesis-decoding-not-generating](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/thesis-decoding-not-generating.md) (memory)
**Discipline:** [feedback-adr-cross-reference-discipline](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-adr-cross-reference-discipline.md) (memory)
**Parent scope:** [L10 — Runtime Model](./L10-runtime-model-scope.md)
**Primary substrate:** [ADR-0057 — Teaching-Chain Proposal + Review + Replay-Equivalence Gate](./ADR-0057-teaching-chain-proposal-review.md)
**Current async path:** [ADR-0155 — CI contemplation runner](./ADR-0155-ci-contemplation-runner.md)
**Current mobile ratification surface:** [`ratify-proposal.yml`](../../.github/workflows/ratify-proposal.yml)
**Shelved-but-relevant:** [[project-engine-identity-candidate]] — engine identity continuity may become relevant to queue authorship and replay provenance, but this scope does not commit to it.

---

## Why this document exists

L10 named the runtime-model problem and explicitly surfaced the HITL async entrypoint as a load-bearing sub-question. L10b is now closed enough that the next architectural gap is no longer whether CORE needs a HITL queue, but what questions the queue ADR must answer before implementation.

CORE already has pieces of a proposal loop:

- ADR-0057 defines proposal eligibility, replay-equivalence, operator review, and the append-only proposal log.
- ADR-0155 defines a CI-driven contemplation path that can produce report artifacts asynchronously, through GitHub Actions and PR review.
- `.github/workflows/ratify-proposal.yml` gives the operator a mobile-feasible manual ratification surface through GitHub Actions workflow dispatch.

But these pieces do not yet constitute an async queue model. The operator can trigger and ratify specific artifacts, but the queue itself has no declared shape. There is no scoped answer for what persists, how states transition, how multiple proposal producers coexist, how the operator sees pending work from an iPhone, what the engine does while proposals are pending, or how queue pressure is bounded.

This document defines the L11 question. The answer belongs to a later ADR. This scope deliberately names architectural questions and constraints without choosing concrete implementation mechanics.

---

## Cross-reference audit

Per [[feedback-adr-cross-reference-discipline]], L11 must be drafted against the existing ADRs, workflow surfaces, and doctrine already present in the repository.

### Existing documents and surfaces

| Source | Relevance |
|---|---|
| [L10-runtime-model-scope](./L10-runtime-model-scope.md) | Names HITL async entrypoint as Sub-question 4 and states that runtime continuation must not depend on operator ratification. |
| [ADR-0057-teaching-chain-proposal-review](./ADR-0057-teaching-chain-proposal-review.md) | Defines proposal log shape, replay-equivalence precondition, pending/accepted/rejected/withdrawn review states, and operator review boundary. |
| [ADR-0155-ci-contemplation-runner](./ADR-0155-ci-contemplation-runner.md) | Defines the current async producer path: CI runs contemplation and proposes artifacts through PR review. |
| [`ratify-proposal.yml`](../../.github/workflows/ratify-proposal.yml) | Defines the current mobile-feasible manual ratification surface through GitHub Actions workflow dispatch. |
| [CLAUDE.md](../../CLAUDE.md) | Defines non-negotiable doctrine: deterministic replay, exact recall, no hidden state, no autonomous pack/corpus mutation, and proposal-only learning until reviewed. |
| [[project-engine-identity-candidate]] | Possible future mechanism for continuity of engine identity / authorship across long-running or rebooted queue producers. Mentioned only as a candidate, not a commitment. |

### Existing proposal machinery this scope must preserve

The HITL queue is not greenfield. Existing proposal machinery already commits to:

- append-only proposal history;
- replay-equivalence as a precondition, not permission;
- pending proposals remaining pending until explicit operator action;
- accepted proposals appending ratified content with typed provenance;
- rejected/withdrawn proposals remaining in the historical log;
- no autonomous mutation of active corpus, packs, identity, safety, or ethics state.

L11 does not replace that machinery. It scopes the async queue layer around it.

---

## The L11 queue question

> **What async HITL queue shape lets CORE continue running, proposing, and replaying while preserving the operator as the sole ratification gate, with a mobile-feasible review surface and deterministic audit trail?**

This question is not asking for a web app, a daemon, or a new mutation API. It is asking what an eventual ADR must decide before any such implementation is safe.

---

## Sub-questions

### Sub-question 1 — Persistent representation

What is the queue's durable representation?

The ADR must answer whether the queue is:

- an extension of `teaching/proposals/proposals.jsonl`;
- a separate append-only JSONL queue;
- a derived view over proposal logs plus CI run artifacts;
- a branch/PR-backed queue where GitHub objects are the queue surface;
- or some constrained combination of these.

The answer must preserve append-only replayability. A queue item cannot be a hidden in-memory task whose existence disappears after reboot. If queue state is derived, the ADR must name the source records and the deterministic derivation rule.

Questions the ADR must answer:

- What is the stable queue item identifier?
- Is queue identity the same as `proposal_id`, or does a queue item wrap one or more proposal/report artifacts?
- What minimal fields are required for replay: source kind, source path, proposal id, replay evidence, review state, operator note, producer identity, and provenance?
- What are valid queue states, and are they a strict extension of ADR-0057's `pending / accepted / rejected / withdrawn` states or a separate axis?
- How does the queue represent stale, expired, superseded, malformed, or duplicate items without deleting history?

This scope does not choose the representation. It names representation as the first load-bearing decision.

### Sub-question 2 — Operator interaction surface

How does the operator interact with the queue while often working from an iPhone?

The ADR must treat mobile feasibility as a first-class constraint. Any proposed interaction shape must be usable without a desktop terminal.

Candidate surfaces the ADR must compare:

- local CLI commands;
- GitHub Actions `workflow_dispatch` inputs;
- GitHub PR review and comments;
- GitHub mobile app interactions;
- a future Workbench or web surface;
- a TUI or daemon-local UI;
- generated copy/paste CLI commands surfaced in queue artifacts.

Questions the ADR must answer:

- What is the minimum operator action for accept/reject/withdraw?
- Can the operator inspect replay evidence and proposal content from a phone before ratification?
- Is ratification allowed through GitHub Actions only, or must local CLI remain authoritative?
- How are accidental taps, malformed workflow inputs, and wrong proposal ids handled?
- What audit record proves which operator performed which action?
- Does the surface support rejection notes and withdrawal notes, or only acceptance?

The ADR must not assume the operator is at a workstation. Desktop-only review is insufficient for L11.

### Sub-question 3 — Engine behavior while pending

What does CORE do while one or more proposals are pending?

L10 already states the core doctrine: the engine continues serving turns normally; pending HITL must not block runtime continuation. L11 must make that precise for queue semantics.

Questions the ADR must answer:

- Does a pending proposal affect live responses, retrieval, teaching-grounded surfaces, or contemplation?
- Can the engine continue producing more proposals while earlier ones are pending?
- Can multiple pending proposals target the same subject, chain, pack, recognizer, or corpus region?
- If a later proposal depends on an earlier pending proposal, how is that dependency represented without treating the earlier proposal as ratified?
- What happens when a pending proposal is accepted after the engine has already produced later proposals from the old substrate?
- What is the replay story for work produced before and after ratification?

The default scope assumption is conservative: pending proposals are observable but not active truth. The ADR must explicitly justify any stronger behavior.

### Sub-question 4 — Queue bounds and backpressure

How are async proposal queues bounded?

A forever-running or CI-assisted engine can produce more proposals than an operator can review. Without explicit bounds, "proposal-only" can still become an unbounded pressure surface.

Questions the ADR must answer:

- Is there a queue cap?
- Is there a per-producer rate limit?
- Is there a per-domain or per-substrate cap?
- Are duplicate proposals deduplicated, suppressed, coalesced, or merely marked as duplicates?
- Do queue items expire, and if so, does expiry mean a terminal append-only state rather than deletion?
- What happens when the queue is full: refuse new proposals, degrade to report-only, replace lower-priority candidates, or alert the operator?
- What is the operator-visible signal for backpressure?

The ADR must preserve determinism. Queue ordering, deduplication, and expiry cannot depend on unrecorded wall-clock behavior or race timing.

### Sub-question 5 — Trust boundary and ratification log

Who can ratify queue items, by what authority, and how is that logged?

ADR-0057 already forbids automatic acceptance. L11 must scope the async version of the same boundary.

Questions the ADR must answer:

- What identities are allowed to accept, reject, or withdraw queue items?
- Does GitHub actor identity suffice for Actions-triggered ratification?
- How does local CLI ratification record operator identity?
- How are notes, review date, source branch, commit SHA, workflow run id, and proposal id recorded?
- Can CI ever ratify, or only stage queue items?
- What prevents a workflow from accepting an item that failed replay-equivalence?
- What prevents broad filesystem mutation during ratification?
- What is the minimal audit record needed to replay the ratification history?

The ADR must make the ratifier identity and trust boundary inspectable. "The workflow ran" is not sufficient unless the workflow input, actor, commit SHA, and resulting file changes are bound into the audit trail.

---

## Constraints (non-negotiable)

The eventual ADR must satisfy these constraints.

### 1. Proposal-only until reviewed

No queue item may mutate ratified teaching corpus, packs, recognizer registry, identity, safety, ethics, runtime policy, or operator code until an explicit operator ratification path accepts it.

Replay-equivalence is never permission. It is only a precondition for review eligibility.

### 2. Runtime continuation must not depend on HITL

The engine must continue serving turns while proposals are pending. Pending queue items are not active truth. They may be visible as audit artifacts, but they must not silently alter answer generation, pack lookup, corpus grounding, or eval scoring.

### 3. Append-only history

Queue history must be append-only or derivable from append-only records. Rejection, withdrawal, expiration, malformed-state marking, and duplicate suppression must not delete or rewrite historical evidence.

### 4. Deterministic replay

Given the same queue history, proposal log, teaching corpus, packs, and input stream, the engine must reconstruct the same queue state and the same ratification history. No unrecorded wall-clock decisions, race-order decisions, or hidden worker state may affect deterministic queue reconstruction.

### 5. No hidden state

Any persisted queue state must be human-and-machine-readable, checksummable, and auditable. If queue state is derived from GitHub PRs, workflow runs, or report artifacts, the ADR must name those sources as part of the replay substrate.

### 6. Mobile-feasible operator path

The operator often works from an iPhone. The ADR must preserve at least one phone-usable path for inspect, accept, reject, or defer. A desktop-only CLI cannot be the sole L11 surface.

### 7. Narrow trust boundary

CI may stage artifacts, compute reports, and open PRs. CI must not autonomously accept proposals. Any workflow that writes ratified state must use the same review/accept codepath as local operator review and must fail closed when proposal preconditions are not met.

### 8. Exact scope separation

L11 scopes the queue. It does not decide the forever-running process shape, engine identity continuity, recognizer persistence, Workbench UI, queue database backend, or implementation API unless those are necessary to state queue constraints.

---

## Out of scope

This scope does not commit to:

- a web UI;
- a Workbench implementation;
- a TUI;
- a daemon process;
- database-backed queue storage;
- background workers;
- async Python tasks;
- automatic proposal acceptance;
- auto-merge;
- direct mutation from CI without operator review;
- pack, recognizer, identity, safety, or ethics ratification semantics;
- engine-state persistence across reboot;
- queue prioritization heuristics;
- final queue schema;
- migration strategy from current proposal logs;
- cross-device notification delivery;
- Slack, email, push notification, or mobile-app integrations.

Those may become future ADR topics. L11's job is only to name the async HITL queue questions and the constraints the future ADR must satisfy.

---

## Candidate ADR acceptance shape (not implementation)

The eventual ADR is ready only when it can answer, in prose and with testable invariants:

1. What durable records define the queue?
2. What state machine governs queue items?
3. What operator surfaces are valid, including mobile-feasible review?
4. What happens while items are pending?
5. How does backpressure work?
6. How is ratifier identity logged?
7. How does replay reconstruct the queue and ratification history?
8. What is explicitly forbidden?

This document does not answer those questions. It prevents the ADR from skipping them.

---

## Cross-references

- [L10 — Runtime Model](./L10-runtime-model-scope.md) — parent scope; Sub-question 4 names HITL async entrypoint.
- [ADR-0057 — Teaching-Chain Proposal + Review + Replay-Equivalence Gate](./ADR-0057-teaching-chain-proposal-review.md) — existing proposal log, replay-equivalence, and operator-review doctrine.
- [ADR-0155 — CI contemplation runner](./ADR-0155-ci-contemplation-runner.md) — current async producer path through GitHub Actions and PR review.
- [`ratify-proposal.yml`](../../.github/workflows/ratify-proposal.yml) — current GitHub Actions / mobile-dispatch ratification surface.
- [CLAUDE.md](../../CLAUDE.md) — deterministic replay, no hidden state, exact recall, proposal-only learning, and trust-boundary doctrine.
- [[feedback-adr-cross-reference-discipline]] — requires new ADR scopes to ground themselves in existing accepted ADRs and substrate, not rewrite history.
- [[project-engine-identity-candidate]] — shelved possible identity-continuity mechanism; relevant if queue producer identity or reboot continuity becomes load-bearing.

---

## Closure

After L11, the project has a bounded question for the HITL async queue: how to let proposals accumulate and await operator review without ever becoming active truth before ratification, without blocking runtime continuation, and without losing deterministic replay. The next ADR may choose a concrete queue representation and operator surface only after answering the sub-questions above.
