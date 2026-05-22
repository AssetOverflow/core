# evals/domain_contract_validation — Lane Contract

**ADR:** ADR-0093
**Invariant:** `domain_contract_v1_predicates_enforced`

## Purpose

Prove that ADR-0091's nine validation predicates fire under the
implementation in :mod:`core.capability.domain_contract_predicates`.

The lane verifies, against synthetic manifests built in the runner's
temp area:

- positive: a contract that satisfies all nine predicates passes
- one negative case per predicate (P3, P4, P5, P6, P7, P8, P9) where
  the relevant rule is minimally broken
- the legacy structural-only output remains shaped as it was, so
  existing callers don't break

P1 and P2 (manifest checksum / gloss closure) require a fully
compiled pack and are exercised against the in-tree
``en_mathematics_logic_v1`` pack rather than against synthetic fixtures.

## Cases

- ``positive_all_predicates_pass`` — synthetic pack with valid contract.
- ``p3_unknown_domain`` — domain_id outside the ledger registry.
- ``p4_unregistered_chain`` — teaching_chains references a non-existent
  corpus.
- ``p5_chain_shortfall`` — one claimed operator family has < 8 chains.
- ``p6_too_few_intents`` — domain has < 3 populated intent shapes.
- ``p7_incomplete_splits`` — eval_lanes entry missing ``holdout``.
- ``p8_unknown_reviewer`` — reviewer id not in the registry.
- ``p9_open_gap`` — known_gaps references an unknown gap id.
- ``determinism`` — same inputs across two runs → byte-identical report.

## Determinism

The runner emits ``results/v1_dev.json``. Two consecutive runs must
produce identical bytes (SHA-256 pinned). The chain inventory and
reviewer registry are injected so the lane does not depend on
git-state-sensitive sources.

## Exit code

Non-zero on any case whose actual outcome diverges from the case spec.
