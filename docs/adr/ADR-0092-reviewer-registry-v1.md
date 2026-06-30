# ADR-0092 — Reviewer Registry v1

**Status:** Accepted
**Date:** 2026-05-21
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091

---

## Acceptance evidence

Accepted after the reviewer registry trust root was implemented and wired into Domain Pack Contract v1 validation:

- `docs/reviewers.yaml` carries `schema_version: 1` and the bootstrap `shay-j` reviewer entry.
- `core/capability/reviewers.py` implements the immutable loader, unknown-key rejection, duplicate-id rejection, role/domain restrictions, and review-scope checks.
- `core/capability/domain_contract_predicates.py` consults the registry for ADR-0091 predicate P8.
- `evals/reviewer_registry/runner.py` contains the reviewer-registry lane.
- `tests/test_capability_cli.py` and the ratification tests exercise ledger rows that depend on successful reviewer resolution.

---

## Context

ADR-0091 defines Domain Pack Contract v1. Its validation semantics require
that every `reviewers` entry on a reasoning-capable pack resolve through
`docs/reviewers.yaml`.

The registry is also load-bearing for proposal review (`teaching/review.py`)
and capability ledger evidence rows. Treating it as a free-form list will
produce drift; treating it as schema-bearing data lets the validator
refuse malformed entries before they reach the runtime.

---

## Decision

Introduce **Reviewer Registry v1** as a structured, validator-checked
schema for `docs/reviewers.yaml`. The schema is small on purpose. It must
be the minimum that satisfies ADR-0091 predicates without inviting
identity inflation.

### Schema

```yaml
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: primary
    domains: ["*"]
    review_scope: ["pack", "proposal", "chain", "eval"]
    provenance: "adr-0092:bootstrap:2026-05-21"
```

| Field | Required | Purpose |
| --- | --- | --- |
| `schema_version` | yes | Version gate for registry parsing semantics. |
| `reviewer_id` | yes | Stable key referenced by pack manifests and proposals. |
| `display_name` | yes | Human-readable label for ledger and report rows. |
| `role` | yes | `primary` or `domain`. `primary` may review any pack; `domain` requires `domains` enumeration. |
| `domains` | yes | List of `domain_id` values from ADR-0091. `["*"]` for primary reviewers. |
| `review_scope` | yes | Subset of `{pack, proposal, chain, eval}`. Bounds what artifacts this reviewer may ratify. |
| `provenance` | yes | Review trail entry for the reviewer's addition itself. |

### Bootstrap entry

Registry ships with exactly one reviewer (`shay-j`) at v1 landing. Adding
reviewers is a separate reviewed proposal flow. The bootstrap entry is
self-sealed: its `provenance` references this ADR.

### Validator rules

The capability validator refuses ratification when:

1. `docs/reviewers.yaml` does not match `schema_version: 1`.
2. A pack manifest names a `reviewer_id` absent from the registry.
3. A reviewer's `role: domain` does not include the pack's `domain_id`.
4. A reviewer's `review_scope` does not cover the artifact being ratified.
5. Two reviewer entries share a `reviewer_id`.

No validator mutates the registry. Mutation remains a reviewed proposal.

---

## Trust Boundary

`docs/reviewers.yaml` is parsed at validator startup and on every ledger
report run. The parser rejects unknown top-level keys and unknown
reviewer fields rather than ignoring them — schema drift is loud, not
silent. Reviewer IDs are display-only; the registry never grants runtime
permissions beyond the predicates ADR-0091 already enforces.

---

## Invariant

`reviewer_registry_schema_v1` — running `core capability ledger` against
a registry that fails schema validation must exit non-zero and produce a
typed error naming the failing field; no ledger row may be emitted under
a malformed registry.

---

## Lane

`evals/reviewer_registry/`:

- positive: valid v1 registry passes
- negative: empty registry blocks all `reasoning-capable` claims
- negative: malformed entry produces typed error
- negative: domain reviewer claiming wildcard `["*"]` rejected

---

## Consequences

- One real reviewer entered; subsequent reviewer additions are themselves
  reviewed proposals, preventing trust inflation.
- ADR-0091 predicate #8 (reviewer resolution) is enforceable.
- Identity, safety, ethics packs gain a checked author trail without
  altering their existing self-seal flow.
