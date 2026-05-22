# ADR-0095 — Miner-Sourced Teaching Proposals

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers
**Depends on:** ADR-0094

---

## Context

Phase 5 of the contemplation arc landed three miners under
`core/contemplation/miners/`:

- `articulation_quality.py` (closed the articulation loop signal)
- `contradiction_detection.py`
- `frontier_compare.py`

Each miner emits observations. None of them currently produce
`PackMutationProposal` candidates. The loop is one-way: contemplation
sees the gap, but the only way to close it is for an operator to
read the miner output and manually file a proposal. That breaks the
"learn from reviewed correction" arc CLAUDE.md names as load-bearing:

> listen → comprehend → recall → think → articulate → learn from reviewed correction → replay deterministically

This ADR closes the loop without weakening the reviewed-teaching
discipline. The doctrine constraint is sharp: there must be exactly
one correction path, and miner-sourced proposals must traverse it.

---

## Decision

Introduce `teaching/proposals/from_miner.py` that translates miner
observations into `PackMutationProposal` candidates with
`source = ProposalSource(kind="miner", source_id=<miner_id>, …)` from
ADR-0094.

### Hard constraints

1. **Single review path.** Miner-sourced proposals enter
   `teaching/review.py` via the same entry point as operator proposals.
   No parallel reviewer, no auto-acceptance, no shortened review path.
2. **Default status `speculative`.** Miner-sourced proposals are never
   coherent at emission.
3. **Identity-pack defense.** Proposals touching identity-pack axes are
   rejected at proposal-construction time (before review), not at
   review time. This prevents the miner from ever filing an identity
   override candidate, even one that would fail review. ADR-0027's
   identity-override rejection rule extends upstream.
4. **Replay-equivalence pre-gate.** Before a miner-sourced proposal is
   review-eligible, replay the originating turn under the proposed
   mutation. If `trace_hash` changes on any non-target turn in the
   lane, the proposal is rejected at construction.
5. **Deterministic emission.** Same miner observations + same head SHA
   → byte-identical proposal stream. Proposal IDs are SHA-256 of
   `(miner_id, observation_canonical, emitted_at_revision)`.

### What miners do not gain

- Direct write access to packs.
- Ability to mark proposals coherent.
- Ability to mutate identity, safety, or ethics packs at all.

### Telemetry

Miner-sourced proposals emit a `"type": "proposal_emitted"` event to
the existing telemetry sink (ADR-0040), carrying the redacted
`source.serialize()` string and proposal ID. Content is redacted by
default per ADR-0040.

---

## Invariant

`miner_proposal_replay_equivalence` — for every miner-sourced proposal
that reaches review eligibility, replaying the originating lane with
the proposed mutation applied yields identical `trace_hash` on every
non-target turn. The lane gate refuses proposals that violate this.

`miner_proposal_single_review_path` — grep gate refuses any code path
that promotes a miner-sourced proposal to coherent outside
`teaching/review.py`.

---

## Lane

`evals/miner_loop_closure/` (new):

- positive: legitimate articulation gap → proposal emitted → reviewable
- negative: identity-override attempt via miner → rejected at construction
- negative: proposal that breaks replay-equivalence → rejected at construction
- negative: malformed miner observation → typed error, no proposal
- coincidence: random/noise observation → no proposal under threshold
- determinism: same observations across two runs → identical proposal stream

---

## Trust Boundary

Miners read turn telemetry only; they do not read user-controlled text
directly. The miner-to-proposal boundary sanitizes `source_id` via
`safe_pack_id` traversal rejection. The replay-equivalence gate is a
filesystem-only operation against the existing eval runners; no network
or shell.

---

## Consequences

- Phase 5 contemplation becomes a closed loop in code, not just in
  doctrine.
- The capability ledger gains a new evidence row class: "miner-sourced
  proposal accepted into coherent" — measurable, replayable.
- Learning-scale claims (the deferred 10k harness) become eventually
  defensible because every replayed proposal will have a real
  provenance, not a synthetic one.

---

## PR Checklist

- Capability added: closed contemplation loop through reviewed teaching.
- Invariants proved: `miner_proposal_replay_equivalence`, `miner_proposal_single_review_path`.
- Lane proving it: `evals/miner_loop_closure/`.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none. Single review path enforced by grep gate.
- Trust boundary: miner reads telemetry, never user text; identity-pack rejection at construction.
