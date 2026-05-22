# ADR-0080 — Contemplation Loop: self-interrogation without self-ratification

**Status:** Accepted
**Date:** 2026-05-20
**Accepted:** 2026-05-22
**Author:** Shay
**Builds on:** [ADR-0021](./ADR-0021-epistemic-grade-policy.md) (epistemic grade policy), [ADR-0055](./ADR-0055-teaching-corpus-audit.md) (reviewed teaching corpus), [ADR-0078](./ADR-0078-composer-graph-atom-equivalence.md) (composer/graph atom telemetry)
**Series:** L0 — learning safety / self-contemplation boundary

---

## Context

CORE already has a conservative learning boundary:

* reviewed corrections become `ReviewedTeachingExample` records;
* accepted examples emit `PackMutationProposal` objects;
* proposals do not mutate packs directly;
* epistemic status starts as `SPECULATIVE` and only coherence review may promote a claim;
* only `COHERENT` claims are admissible as downstream evidence.

That boundary is correct.  Self-contemplation must not bypass it.

The architectural temptation is to let the model think about its current knowledge, generate new statements, and then treat those statements as learned.  That is not learning; it is recursive self-confirmation.  It would reintroduce the same failure mode CORE is designed to avoid: ungrounded output hardening into future substrate.

The correct form is narrower:

> Self-contemplation may interrogate the current learned substrate and emit evidence-bearing `SPECULATIVE` findings.  It may not ratify, promote, or apply its own conclusions.

Contemplation is therefore a read-only scientific instrument, not an autonomous training loop.

---

## Decision

Introduce a deterministic, sandboxed contemplation loop whose first phase is read-only and report-driven.

The loop consumes explicit substrate snapshots and structured reports, then emits `ContemplationFinding` records.  A finding can represent a coverage gap, contradiction, weak surface, unproved relation, derivable relation, benchmark case, OOV gap, planner gap, or pack mutation candidate.  In ADR-0080 Phase 1, every emitted finding is `SPECULATIVE` by construction.

The initial implementation is intentionally small:

```text
core/contemplation/
  schema.py
  snapshot.py
  runner.py
  miners/frontier_compare.py
```

Phase 1 mines existing `frontier_compare` benchmark JSON reports and turns failed cases into reviewable findings.  This creates a safe path for self-contemplation to improve the test curriculum without mutating knowledge.

---

## Doctrine

### Contemplation may produce

```text
coverage gaps
contradiction candidates
weak-surface findings
unproved-relation findings
derivable-relation candidates
benchmark-case candidates
OOV-gap findings
planner-gap findings
pack-mutation candidates
```

### Contemplation may not produce

```text
COHERENT claims
applied pack mutations
ratified packs
runtime behavior changes
durable truth writes
silent teaching corpus writes
```

### Learning remains externalized

The only admissible durable-learning path remains:

```text
finding / proposal
  -> review
  -> coherence judgment
  -> pack mutation proposal
  -> ratification
  -> replay / eval
```

Contemplation can discover what should be reviewed.  It cannot review itself.

---

## Invariants

ADR-0080 Phase 1 requires the following hard invariants:

### 1. No self-ratification

Every `ContemplationFinding` emitted by the v1 loop must have:

```text
epistemic_status == SPECULATIVE
```

Constructing a finding with `COHERENT`, `CONTESTED`, or `FALSIFIED` is rejected.

### 2. No pack mutation

The contemplation runner must not write to `language_packs/`, ratification outputs, teaching corpora, or runtime pack manifests.

### 3. Replay determinism

The same substrate snapshot and the same report bytes must produce the same run hash and finding hashes.

### 4. Evidence-bearing output

Every finding must carry at least one `ContemplationEvidenceRef`.  A model may not emit an unsupported finding merely because it generated an interesting thought.

### 5. Read-only first wave

Phase 1 only reads explicit files passed by the operator.  It does not crawl the repo, call external APIs, or inspect live runtime mutable state.

---

## Phase 1 implementation boundary

Phase 1 may implement:

* immutable schema dataclasses;
* canonical JSON and stable hashes;
* substrate snapshot hashing;
* a `frontier_compare` report miner;
* a read-only runner;
* unit tests proving no promotion, no mutation, deterministic replay, and evidence requirements.

Phase 1 must not implement:

* autonomous curriculum generation;
* pack mutation writing;
* teaching-store writes;
* graph/proposition mutation;
* runtime integration;
* long-running self-play;
* external model calls;
* hidden background jobs.

---

## Report-mining behavior

Given a `frontier_compare` report JSON, the v1 miner emits one finding for every failed case.

A failed case becomes:

```text
kind: benchmark_case
subject: <suite>/<case_id>
predicate: failed_case
object: <prompt>
epistemic_status: speculative
evidence_refs: report path, suite, case id, failures
proposed_action: add or repair a benchmark/training case for the observed failure
```

The finding is not a claim about world truth.  It is a claim about system behavior under a recorded benchmark report.

---

## Consequences

### Positive

* Gives CORE a safe self-contemplation surface.
* Converts eval failures into structured, reviewable findings.
* Preserves the existing epistemic lattice.
* Prevents self-generated text from hardening into knowledge.
* Creates the first bridge from benchmarks to weakness-driven curriculum.

### Negative / costs

* Does not make CORE autonomously learn yet.
* Requires operator review before any durable learning occurs.
* Starts with benchmark-report mining only; deeper contradiction/derivation miners are deferred.

### Deferred follow-up

Later ADRs may add miners for:

* pack coverage gaps;
* teaching-chain gaps;
* graph contradiction candidates;
* derivable-relation candidates;
* OOV queue consolidation;
* long-form workbench failures;
* curriculum task generation.

Each follow-up must preserve the no-self-ratification invariant.
