# ADR-0104 — Curriculum-Sourced Teaching Proposals

**Status:** Accepted
**Date:** 2026-05-22
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0094, ADR-0095

---

## Acceptance evidence

Accepted after curriculum-sourced proposals were wired through the reviewed teaching pipeline with a deterministic, SHA-pinned closure lane:

- `teaching/from_curriculum.py` converts curriculum-authored `PACK_MUTATION_CANDIDATE` findings into `PackMutationProposal` records carrying `ProposalSource(kind="curriculum", source_id=<curriculum_id>, ...)`.
- `evals/curriculum_loop_closure/runner.py` and `evals/curriculum_loop_closure/contract.md` define the closure lane; `evals/curriculum_loop_closure/results/v1_dev.json` is the canonical report.
- `tests/test_curriculum_proposals.py` exercises curriculum-to-proposal conversion, source-tagging, replay determinism, identity defense, telemetry redaction, and review-path parity with operator/miner proposals.
- `scripts/verify_lane_shas.py` pins `curriculum_loop_closure` and includes it in the lane verifier.

---

## Context

ADR-0094 reserved `ProposalSource(kind="curriculum")` as a sealed provenance value. ADR-0095 then proved that non-operator proposal sources can exist without gaining pack-write authority, coherence authority, or a parallel reviewer.

Curriculum ingestion is the next non-operator source. A curriculum may contain structured lessons, examples, and pack-extension candidates. Those candidates are not trusted merely because they came from a curriculum. They must enter the same proposal log and reviewed-teaching path as operator and miner proposals.

---

## Decision

Introduce `teaching/from_curriculum.py`, a structural sibling of `teaching/from_miner.py`, to translate curriculum-authored `ContemplationFinding(kind=PACK_MUTATION_CANDIDATE)` values into `PackMutationProposal` candidates.

Curriculum proposals carry:

```python
ProposalSource(
    kind="curriculum",
    source_id=<curriculum_id>,
    emitted_at_revision=<git_sha_or_revision>,
)
```

### Hard constraints

1. **Single review path.** Curriculum-sourced proposals enter the same review path as operator and miner proposals. No alternate reviewer and no auto-acceptance.
2. **Default status `speculative`.** Curriculum-sourced proposals are never coherent at emission.
3. **Identity-pack defense at construction.** A curriculum item whose subject or proposed action trips the identity-override detector is rejected before it can become a proposal.
4. **Replay-equivalence pre-gate.** A pluggable checker can reject curriculum proposals whose proposed mutation changes non-target turn `trace_hash` values.
5. **Deterministic emission.** Proposal IDs are SHA-256 derived from `(curriculum_id, finding_canonical, emitted_at_revision)` and truncated to 16 hex chars.
6. **Redacted telemetry.** Proposal-emitted events carry only proposal ID, source serialization, and epistemic status. Raw content is excluded.

---

## Invariants

`curriculum_proposal_replay_equivalence` — every curriculum-sourced proposal that reaches review eligibility must preserve non-target replay hashes under the proposed mutation.

`curriculum_proposal_single_review_path` — no code path may promote a curriculum-sourced proposal to coherent outside the allowed review/store path.

---

## Lane

`evals/curriculum_loop_closure/` proves:

- positive: legitimate curriculum item -> proposal emitted with curriculum provenance
- negative: identity override in subject -> rejected at construction
- negative: identity override in action -> rejected at construction
- negative: replay-equivalence failure -> rejection log entry
- negative: wrong finding kind -> typed error, no proposal
- determinism: same findings and revision -> identical proposal stream

---

## Consequences

- Curriculum import can now feed the learning loop without receiving trust elevation.
- Domain/course authors can supply structured proposal candidates while preserving review authority boundaries.
- The proposal-source lattice now has three active kinds: operator, miner, curriculum.
- SHA-pinned lane coverage expands from six to seven lanes.

---

## PR Checklist

- Capability added: curriculum-sourced proposal construction.
- Invariants proved: `curriculum_proposal_replay_equivalence`, `curriculum_proposal_single_review_path`.
- Lane proving it: `evals/curriculum_loop_closure/`.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none.
- Trust boundary: curriculum content can propose; only review/store can accept or promote.
