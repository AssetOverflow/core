# ADR-0093 — Domain Pack Contract v1 Implementation

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092

---

## Context

ADR-0091 defines the Domain Pack Contract but explicitly states:

> The validator remains proposal-only until the schema change is
> implemented. … Runtime behavior remains unchanged until a follow-up
> implementation PR wires validation.

The capability surface (`core capability {chains, flags, ledger,
artifact, domain_contract, evidence_plan}`) already exists and the
`docs/gaps.md` registry shows extensive structural work landed. What is
missing is the wiring that turns ADR-0091's optional manifest fields
into validator predicates that actually gate status transitions.

Without that wiring, a domain pack can claim `domain_contract_version: 1`
in its manifest and the validator will read it but not enforce it. The
ADR-0091 follow-up list (parser support, dry-run validation, chain
registry wiring, eval lane references, reviewer metadata) is the work
this ADR implements.

---

## Decision

Implement ADR-0091's five follow-up items as a single, evidence-bearing
PR. Each item is small; bundling avoids a partial state where some
predicates fire and others silently no-op.

### Items

1. **Manifest parser support for `domain_contract_version=1`.**
   Extend `language_packs/compiler.py` (or its loader sibling) to recognize
   the optional fields enumerated in ADR-0091. Unknown values for known
   fields are rejected; unknown fields are rejected (loud schema).

2. **Dry-run validation for domain contract fields.**
   New command `core capability domain-contract validate <pack_id> --dry-run`
   runs the nine predicates from ADR-0091 §"Validation Semantics" and
   reports per-predicate pass/fail without mutating state. Exit code is
   non-zero on any failure.

3. **Domain-specific chain registry wiring.**
   Extend `chat/teaching_grounding.py`'s `TEACHING_CORPORA` registration
   to consult pack manifest's `teaching_chains` field at mount time.
   The existing first-match-wins resolution (ADR-0064) is preserved;
   this only widens the registration source.

4. **Eval lane references in capability artifact metadata.**
   `core capability artifact <pack_id>` includes per-lane split paths
   (dev/public/holdout) from the manifest's `eval_lanes` field, plus the
   most recent report SHA for each. Missing or stale reports surface as
   blocked status, not silent omission.

5. **Reviewer metadata resolution.**
   `core capability domain-contract validate` consults the registry from
   ADR-0092 and refuses ratification on any unresolved or
   out-of-scope reviewer.

### What is deliberately not in scope

- No new capability status tier beyond ADR-0091's five.
- No automatic mutation of pack manifests. Manifests are still
  hand-authored and reviewed.
- No retrofitting of linguistic packs that don't claim domain status.
  ADR-0091's optionality is preserved.

---

## Invariant

`domain_contract_v1_predicates_enforced` — for every pack with
`domain_contract_version: 1`, running `core capability domain-contract
validate <pack_id>` either passes all nine ADR-0091 predicates or emits
a typed error naming each failing predicate. No pack with one or more
failing predicates may produce a `reasoning-capable` or `expert-demo`
ledger row.

---

## Lane

`evals/domain_contract_validation/` (new):

- positive: pack with all predicates satisfied → validator pass + ledger row eligible
- negative (per predicate): nine cases, one per predicate from ADR-0091 §"Validation Semantics", each minimally broken to confirm the validator catches it
- replay: validator output is deterministic across runs
- coincidence: pack without `domain_contract_version` field still passes ordinary `core pack validate` unchanged

---

## Trust Boundary

The validator reads pack manifests, the reviewer registry, the gaps
registry, and eval report files. All paths are sanitized via
`core/_safe_display.safe_pack_id` and existing pack-validation traversal
rejection (ADR-0051). No dynamic imports. No filesystem writes outside
deterministic report emission.

---

## Consequences

- ADR-0091 advances from `Proposed` to `Accepted` once the implementation
  PR lands and this ADR's lane passes.
- The first pack ratification under ADR-0091 (ADR-0097) becomes
  mechanically possible. Until then, it is blocked by missing
  enforcement, not by missing content.
- Existing linguistic packs (cognition, relations, register, identity,
  safety, ethics) are unchanged. Their lack of `domain_contract_version`
  remains valid.

---

## PR Checklist

- Capability added: ADR-0091 enforcement wired into validator and ledger.
- Invariant proved: `domain_contract_v1_predicates_enforced`.
- Lane proving it: `evals/domain_contract_validation/`.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none.
- Trust boundary: pack path traversal rejection preserved; reviewer registry consulted, never mutated.
