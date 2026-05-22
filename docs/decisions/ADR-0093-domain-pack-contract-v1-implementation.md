# ADR-0093 — Domain Pack Contract v1 Implementation

**Status:** Accepted
**Date:** 2026-05-21
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092

---

## Acceptance evidence

Accepted after Domain Pack Contract v1 was implemented as an enforced validator/ledger predicate path:

- `language_packs/domain_contract.py` parses `domain_contract_version=1` and contract fields.
- `core/capability/domain_contract_predicates.py` evaluates the nine ADR-0091 predicates.
- `core/capability/reviewers.py` and `docs/reviewers.yaml` provide ADR-0092 reviewer resolution for predicate P8.
- `evals/domain_contract_validation/contract.md` documents the validation lane.
- `tests/test_capability_cli.py` verifies the capability CLI and ledger surface.
- `tests/test_adr_0097_mathematics_logic_ratification.py` and `tests/test_adr_0100_0102_sibling_ratifications.py` verify predicate pass-through on ratified packs.

---

## Context

ADR-0091 defines the Domain Pack Contract but explicitly required a follow-up implementation to wire validation. The capability surface (`core capability {chains, flags, ledger, artifact, domain_contract, evidence_plan}`) already existed; this ADR wired the optional manifest fields into predicates that actually gate status transitions.

Without that wiring, a domain pack could claim `domain_contract_version: 1` in its manifest and the validator could read it without enforcing it. This ADR implements the follow-up list: parser support, dry-run validation, chain registry wiring, eval lane references, and reviewer metadata.

---

## Decision

Implement ADR-0091's five follow-up items as a single, evidence-bearing path. Each item is small; bundling avoids a partial state where some predicates fire and others silently no-op.

### Items

1. **Manifest parser support for `domain_contract_version=1`.**
   Contract fields are recognized and malformed values are rejected loudly.

2. **Dry-run validation for domain contract fields.**
   `core capability domain-contract` reports the nine predicates from ADR-0091 §"Validation Semantics" without mutating state.

3. **Domain-specific chain registry wiring.**
   Domain capability corpora are recognized by capability reporting without granting unreviewed runtime mutation authority.

4. **Eval lane references in capability artifact metadata.**
   Declared eval lanes surface split paths and report SHA evidence where present.

5. **Reviewer metadata resolution.**
   Domain contract validation consults ADR-0092 reviewer metadata and refuses ratification on unresolved or out-of-scope reviewers.

### What is deliberately not in scope

- No new capability status tier beyond ADR-0091's five.
- No automatic mutation of pack manifests. Manifests remain hand-authored and reviewed.
- No retrofitting of linguistic packs that do not claim domain status.
  ADR-0091's optionality is preserved.

---

## Invariant

`domain_contract_v1_predicates_enforced` — for every pack with
`domain_contract_version: 1`, running domain-contract validation either
passes all nine ADR-0091 predicates or emits a typed error naming each
failing predicate. No pack with one or more failing predicates may
produce a `reasoning-capable` or `expert-demo` ledger row.

---

## Lane

`evals/domain_contract_validation/`:

- positive: pack with all predicates satisfied → validator pass + ledger row eligible
- negative: one minimally broken case per ADR-0091 predicate
- replay: validator output is deterministic across runs
- coincidence: pack without `domain_contract_version` field still passes ordinary structural validation unchanged

---

## Trust Boundary

The validator reads pack manifests, the reviewer registry, the gaps
registry, and eval report files. Paths remain sanitized via the
trust-boundary discipline established by ADR-0051. No dynamic imports.
No pack mutation.

---

## Consequences

- ADR-0091 is enforceable.
- Domain ratification ADRs can be judged mechanically by the capability ledger.
- Existing linguistic packs remain valid without `domain_contract_version`.
