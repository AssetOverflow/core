# ADR-0159 — Contemplation Quality Eval Lane (W-025)

Status: Accepted

## Context

ADR-0152 introduced the learning-arc demo proving that CORE can:

1. discover an engine-authored chain
2. enrich it through contemplation
3. emit a reviewable proposal
4. replay-check the proposal
5. ratify it through operator review
6. observe a grounded downstream change

ADR-0155 then added CI contemplation report generation.

Those ADRs proved the contemplation loop exists, but they did not create a
formal evaluation lane for judging the quality of contemplation artifacts.

Without a dedicated lane, the system could produce reports indefinitely
without measuring:

- replay integrity
- provenance correctness
- mutation-boundary preservation
- downstream usefulness
- review-boundary preservation

## Decision

Add a new eval lane:

```bash
core eval contemplation-quality
```

The lane evaluates the structured report emitted by:

```bash
core demo learning-arc --json
```

The lane is strictly read-only.

It MUST NOT:

- accept proposals
- mutate corpora
- mutate packs
- mutate engine_state
- bypass operator review
- upgrade epistemic status

Replay-equivalence remains a prerequisite for proposal review eligibility
only. It is never treated as permission for automatic acceptance.

## Metrics

The lane currently scores:

- scene_contract
- deterministic_replay_integrity
- typed_contemplation_provenance
- engine_authored_specificity
- grounding_transition
- downstream_gain_observed
- active_corpus_boundary
- pending_not_auto_accepted
- stable_proposal_identity_present

## Compatibility with prior ADRs

### ADR-0056

Contemplation remains enrichment-only and does not mutate active truth state.

### ADR-0057

Replay-equivalence is measured separately from operator acceptance.
The lane explicitly verifies that proposals remain pending before review.

### ADR-0152

The learning-arc demo remains the canonical contemplation-quality source.
Transient/tempdir semantics remain unchanged.

### ADR-0155

CI contemplation reports remain audit artifacts.
This lane scores those artifacts but does not ratify them.

### ADR-0157

Revision-warning/reboot discipline remains orthogonal.
The eval lane adds no persistence or recovery semantics.

## Consequences

CORE now has a measurable contemplation-quality corridor rather than relying
on subjective review of contemplation reports.

The lane strengthens the distinction between:

- autonomous proposal discovery
- and autonomous proposal acceptance

The latter remains forbidden.
