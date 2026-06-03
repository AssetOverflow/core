# Proof-Chain Fixture Scaffold

**Status:** ADR-0202 grammar filled; not wired into the live suite  
**Scope:** data-only fixture scaffold; not wired into the live test suite

This directory is the independent validation scaffold for the propositional
canonicalizer and first `modus_ponens` proof-chain rule. The formula grammar,
atom declaration shape, and atom-to-FeatureBundle binding convention are governed
by `docs/decisions/ADR-0202-proposition-representation-contract.md`.

The fixture inventory in `propositional_cases.json` records concrete formula
strings, per-case `atoms` blocks, expected behaviors, and rationale. It is ready
for a future proof-chain harness to wire, but it is intentionally not part of the
live test suite yet.

## Atom Bindings

Where a case atom maps to a recognizable fact, the atom records the intended
ADR-0144/ADR-0143 `FeatureBundle` binding as `binding.features`. The corpus does
not author `EpistemicNode.node_id`; that is assigned at recognition time.
Schematic budget atoms use `binding: null`.

## Validation Boundaries

The three `modus_ponens` cases are validated at entailment only. Their typed rule
reasons (`conclusion_mismatch` / `missing_implication`) are marked pending phase
2.3 / ADR-0205, when the rule checker lands.

The two out-of-regime cases assert `out_of_decidable_regime` and record that this
is the `LogicRegimeError` reason produced by merged main after ADR-0201.1.

## Required Categories

- `equivalent_key`: propositions that must reduce to identical canonical keys.
- `different_key`: near-miss propositions that must not collapse.
- `tautology_or_contradiction`: formulas that reduce to TRUE/FALSE leaves.
- `modus_ponens`: proof-chain admission and refusal examples.
- `acyclicity`: circular dependency refusal cases.
- `out_of_regime`: quantified or predicate input outside propositional logic.
- `budget`: scalable ROBDD blowup cases that must refuse when over budget.

## Interface Assumptions

- Formula grammar: ADR-0202 section 1.
- Atom declaration and FeatureBundle binding: ADR-0202 section 2.
- TRUE/FALSE leaf identity: `T` / `F`.
- Budget refusal reason: `canonicalization_budget_exceeded`.
- Proof-chain rule and DAG fields are fixture data only until `proof_chain`
  lands.

## Non-Goals

- No runtime wiring.
- No second canonicalizer implementation.
- No CNF/DNF fallback expectations.
- No predicate-logic equivalence claim.
- No repo capability claim.
