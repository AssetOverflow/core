# evals/curriculum_loop_closure — Lane Contract

**ADR:** ADR-0104
**Invariants:**
- `curriculum_proposal_replay_equivalence`
- `curriculum_proposal_single_review_path`

## Purpose

Prove that curriculum-authored teaching items can emit
:class:`PackMutationProposal` candidates that traverse the existing
reviewed teaching path without violating ADR-0104 hard constraints.

The lane asserts:

1. A legitimate ``PACK_MUTATION_CANDIDATE`` curriculum finding produces
   a curriculum-sourced proposal with ``source.kind="curriculum"`` and
   ``epistemic_status=SPECULATIVE``.
2. Identity-override curriculum items are rejected at construction,
   before review, so the proposal never reaches the proposal log.
3. A finding whose replay-equivalence check fails is rejected at
   construction; its ``finding_id`` appears in the batch's
   ``rejections`` list with reason ``replay_equivalence_failed``.
4. A non-``PACK_MUTATION_CANDIDATE`` finding raises
   :class:`CurriculumProposalError`; curriculum import cannot promote
   diagnostic findings into pack mutations.
5. Same finding stream + same curriculum_id + same revision ->
   byte-identical proposal id stream across two runs.

## Cases

- **positive_basic** — single coherent ``PACK_MUTATION_CANDIDATE``
  finding -> proposal emitted with curriculum source.
- **identity_override_subject** — finding subject contains an
  identity-override pattern -> rejected at construction.
- **identity_override_action** — finding ``proposed_action`` contains
  an identity-override pattern -> rejected at construction.
- **replay_equivalence_failed** — finding sent through a checker that
  reports trace-hash divergence -> rejected at construction.
- **wrong_finding_kind** — non-``PACK_MUTATION_CANDIDATE`` finding ->
  raises ``CurriculumProposalError``.
- **determinism** — three findings emitted twice; proposal-id streams
  must be identical between the runs.

## Determinism

The runner emits ``results/v1_dev.json`` with case results and a
SHA-256 of the canonical report bytes. Two consecutive runs against
the same fixtures must produce identical bytes.

## Exit code

Non-zero on any divergence between expected and actual outcomes.
