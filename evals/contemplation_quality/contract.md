# Contemplation Quality Eval Contract (ADR-0159)

## Purpose

`contemplation-quality` is a read-only evaluation lane that scores the
structured output from:

```bash
core demo learning-arc --json
```

The lane exists to evaluate whether contemplation artifacts are:

- replay-safe
- provenance-correct
- review-boundary preserving
- downstream-effective
- non-mutating

without widening the trust surface.

## Non-goals

This lane MUST NOT:

- accept proposals
- mutate corpora
- mutate packs
- mutate engine_state
- mark contemplation coherent/true
- bypass operator review

## Source contract

The lane currently supports one invocation source:

```json
{"case_id":"learning_arc_demo","source":"learning_arc_demo"}
```

The invocation source is intentionally tiny because the lane evaluates the
runtime's own structured report rather than external benchmark corpora.

## Core metrics

- scene_contract
- deterministic_replay_integrity
- typed_contemplation_provenance
- engine_authored_specificity
- grounding_transition
- downstream_gain_observed
- active_corpus_boundary
- pending_not_auto_accepted
- stable_proposal_identity_present

## ADR compatibility

This lane preserves:

- ADR-0056 contemplation-loop constraints
- ADR-0057 proposal review boundaries
- ADR-0152 learning-arc demo invariants
- ADR-0155 CI contemplation report semantics
- ADR-0157 revision-warning/reboot discipline

Replay-equivalence remains a prerequisite for review eligibility only.
It is never interpreted as automatic proposal acceptance.
