# ADR-0151 — Auto-Proposal Pipeline at Load

Status: Accepted
Date: 2026-05-25

## Context
ADR-0150 stores enriched `DiscoveryCandidate` records in engine state at
checkpoint. Those candidates can already be converted into
`TeachingChainProposal` records through `teaching.proposals.propose_from_candidate`,
which applies the existing eligibility gate, replay-equivalence gate, and
append-only `ProposalLog`.

## Decision
When `RuntimeConfig.auto_proposal_enabled` is true, `ChatRuntime._load_engine_state()`
attempts to propose from loaded pending discovery candidates. The pipeline runs
at load, not checkpoint, so turn completion remains a pure engine-state
checkpoint and proposal construction happens when persisted candidates re-enter
the runtime.

Each auto-generated proposal is stamped with:

```text
source.kind = "contemplation"
source.source_id = candidate.candidate_id
```

The proposal remains in `review_state="pending"` unless the replay gate rejects
it for regression. Operators still ratify accepted memory through
`core teaching review`; this path never auto-accepts.

## Determinism Contract
`TeachingChainProposal.proposal_id` is deterministic over
`(candidate_id, proposed_chain)`. Re-loading the same engine state therefore
reaches the same proposal id, and `ProposalLog` idempotency prevents duplicate
`created` events.

## Trust Boundary
Auto-proposal writes only to the append-only proposal log. It never writes the
active teaching corpus. Corpus mutation remains review-gated through
`accept_proposal`.
