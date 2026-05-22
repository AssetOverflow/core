# evals/miner_loop_closure — Lane Contract

**ADR:** ADR-0095
**Invariants:**
- `miner_proposal_replay_equivalence`
- `miner_proposal_single_review_path`

## Purpose

Prove that Phase-5 contemplation miners can emit
:class:`PackMutationProposal` candidates that traverse the existing
reviewed teaching path without violating ADR-0095 hard constraints.

The lane asserts:

1. A legitimate ``PACK_MUTATION_CANDIDATE`` finding produces a
   miner-sourced proposal with ``source.kind="miner"`` and
   ``epistemic_status=SPECULATIVE``.
2. Identity-override findings are rejected at construction, before
   review, so the proposal never reaches the proposal log.
3. A finding whose replay-equivalence check fails is rejected at
   construction; its ``finding_id`` appears in the batch's
   ``rejections`` list with reason ``replay_equivalence_failed``.
4. A non-``PACK_MUTATION_CANDIDATE`` finding raises
   :class:`MinerProposalError`; the miner cannot promote diagnostic
   findings into pack mutations.
5. Random/under-threshold observations (coincidence control) never
   produce proposals — they are filtered upstream by the miner's
   recurrence thresholds and never reach ``from_finding``.
6. Same finding stream + same miner_id + same revision → byte-identical
   proposal id stream across two runs.

## Cases

The runner iterates over case fixtures declared in :mod:`runner`:

- **positive_basic** — single coherent ``PACK_MUTATION_CANDIDATE``
  finding → proposal emitted with miner source.
- **identity_override_subject** — finding subject contains an
  identity-override pattern → rejected at construction.
- **identity_override_action** — finding ``proposed_action`` contains
  an identity-override pattern → rejected at construction.
- **replay_equivalence_failed** — finding sent through a checker that
  reports trace-hash divergence → rejected at construction.
- **wrong_finding_kind** — non-``PACK_MUTATION_CANDIDATE`` finding →
  raises ``MinerProposalError``.
- **determinism** — three findings emitted twice; proposal-id streams
  must be identical between the runs.

## Determinism

The runner emits ``results/v1_dev.json`` with case results and a
SHA-256 of the canonical report bytes. Two consecutive runs against
the same fixtures must produce identical bytes.

## Exit code

Non-zero on any divergence between expected and actual outcomes.
