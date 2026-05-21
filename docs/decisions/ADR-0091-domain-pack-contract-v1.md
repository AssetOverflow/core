# ADR-0091 — Domain Pack Contract v1

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers

---

## Context

CORE is moving from compact cognition packs toward expert-domain
articulation. The risk is predictable: broad vocabulary can grow faster
than reviewed chains, eval lanes, reviewer coverage, and provenance. If
that happens, the system looks larger while the reasoning substrate stays
thin.

The capability ledger introduced in Phase A-C makes this visible. It
does not promote a domain because a pack exists. It promotes only when
manifest validity, closure, chain coverage, holdout presence, eval
evidence, and known-gap state all line up.

Domain packs need a contract that connects those artifacts without
forcing all existing linguistic packs into a reasoning-heavy schema.

---

## Decision

Introduce **Domain Pack Contract v1** as a pack discipline for packs that
claim domain capability status.

The contract extends pack manifests with optional fields. Existing
linguistic packs remain valid without these fields. A pack must provide
the reasoning fields only when it claims `reasoning-capable` or
`expert-demo` status in the generated capability ledger.

### Optional manifest fields

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "mathematics_logic",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["math_logic_chains_v1"],
  "eval_lanes": [
    {"lane": "mathematics_logic", "version": "v1", "splits": ["dev", "public", "holdout"]}
  ],
  "reviewers": ["reviewer_id"],
  "known_gaps": ["gap:math_logic_modal_chains_absent"],
  "provenance": "adr-0090:reviewed:YYYY-MM-DD"
}
```

| Field | Required for ordinary linguistic pack | Required for reasoning-capable domain claim | Purpose |
| --- | --- | --- | --- |
| `domain_contract_version` | no | yes | Version gate for domain-pack validation semantics. |
| `domain_id` | no | yes | Stable key used by `core capability ledger`. |
| `axioms` | no | yes when the domain uses explicit axioms | References an axioms/rules JSONL file or `null`. |
| `rules` | no | yes when the domain uses explicit rules | References inference-rule definitions or `null`. |
| `teaching_chains` | no | yes | Registered corpora that exercise claimed operator families. |
| `eval_lanes` | no | yes | Eval lanes and split paths that prove the domain claim. |
| `reviewers` | no | yes | Reviewer IDs resolved through `docs/reviewers.yaml`. |
| `known_gaps` | no | yes if blocked | Gap IDs resolved through `docs/gaps.md`. |
| `provenance` | no | yes | Review trail for the domain claim. |

`axioms` and `rules` are deliberately optional. Cognition, relations,
register, identity, safety, and many lexical packs legitimately do not
carry formal axiom sets. Requiring those fields globally would create
schema churn without adding reasoning evidence.

---

## Validation Semantics

The validator remains proposal-only until the schema change is
implemented. When implemented, a domain pack can affect capability claims
only if:

1. The base pack manifest is valid and checksums match bytes on disk.
2. Gloss checksum and definitional closure pass for packs that provide
   glosses or definitions.
3. `domain_id` maps to a known ledger domain.
4. Every `teaching_chains` corpus is registered and read-only.
5. Every claimed operator family has at least 8 reviewed active chains
   for that domain.
6. At least 3 intent shapes are present before `reasoning-capable`.
7. Every `eval_lanes` entry has `dev`, `public`, and `holdout` paths.
8. Every `reviewers` entry resolves to reviewer metadata.
9. Every open `known_gaps` entry blocks promotion until closed and the
   next status predicate passes.

No validator may mutate a pack. Mutation remains a reviewed proposal
flow.

---

## Capability Status

The generated ledger owns status. Manifest fields provide evidence and
links; they do not manually assert maturity.

| Status | Predicate |
| --- | --- |
| `seeded` | Manifest/schema valid, checksum valid, provenance present, no unsafe paths. |
| `grounded` | Gloss coverage threshold passes, closure passes, pack is mount-eligible, gaps are registered. |
| `reasoning-capable` | Claimed operator families each have at least 8 reviewed chains, at least 3 intent shapes are present, eval lane and holdout path exist. |
| `expert-demo` | Dev/public/holdout pass thresholds, provenance/replay pass, audit-tour or equivalent reports all claims supported. |
| `blocked` | A registered gap names the missing substrate, reviewer, or eval. |

`blocked` lifts only when the named gap closes and the next predicate
passes. Closing a gap never promotes a row by itself.

---

## Consequences

- Existing packs remain valid. No mass re-ratification is caused by this
  ADR alone.
- Expert-domain work becomes evidence-coupled: packs, chains, evals,
  reviewers, and gaps have one generated ledger surface.
- Operator work cannot drift away from chain authoring: a claimed
  operator family without chains remains below `reasoning-capable`.
- Hebrew/Greek textual reasoning cannot advance on pack names alone; it
  must close gloss coverage and chain foundation first.

---

## Follow-up Work

1. Add manifest parser support for `domain_contract_version=1`.
2. Add dry-run validation for domain contract fields.
3. Add domain-specific chain registry wiring.
4. Add eval lane references to capability artifact metadata.
5. Ratify domain packs only after reviewer metadata exists.

This ADR is the contract. Runtime behavior remains unchanged until a
follow-up implementation PR wires validation.
