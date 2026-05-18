# ADR-0037: Per-Predicate Ethics Refusal Opt-In

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`ADR-0033-ethics-packs.md`](ADR-0033-ethics-packs.md), [`ADR-0034-ethics-check-surface.md`](ADR-0034-ethics-check-surface.md), [`ADR-0036-safety-refusal-policy.md`](ADR-0036-safety-refusal-policy.md)

## Context

ADR-0036 wired typed refusal for safety violations only.  Ethics
violations were left audit-only because:

1. The pack layer's swappability semantics meant a pack-author flag
   could silently change refusal behavior on every deployment.
2. Empirical violation rates for individual ethics commitments did
   not yet exist.

ADR-0036's deferred follow-up was *per-predicate ethics refusal*: a
mechanism by which a pack author can opt **specific** commitments
into refusal one at a time, without flipping a global ethics-refuses
switch.  That coupling is what this ADR introduces.

## Decision

Add an optional `refusal_commitments` field to the ethics pack JSON
schema.  Each entry must already appear in `commitment_ids`.  At
runtime, an ethics commitment contributes to typed refusal only when
*both*:

1. Its predicate fired `runtime_checkable=True, upheld=False`.
2. Its id appears in `EthicsPack.refusal_commitments`.

The default pack ships with an **empty** `refusal_commitments`.
Audit-only is the floor; opt-in is the ceiling.

### Surface format change

The refusal prefix is generalised from
`"I cannot proceed — safety boundary violated: "` to
`"I cannot proceed — boundary violated: "`, and contributing ids are
**source-tagged**:

* `safety:<boundary_id>`
* `ethics:<commitment_id>`

Source tags disambiguate sibling namespaces and avoid name collisions
between the two pack types.  Lex order is preserved across the merged
list.

### Pack-loader bounds

`packs/ethics/loader.py` now validates `refusal_commitments`:

* Optional; defaults to empty.
* Must be a list of strings if present.
* Every entry must be a declared `commitment_id` (typo → load-time
  error; silent typos would be catastrophic given the behavioral
  consequences).
* No duplicates.

The validator is shared with ADR-0038 (`_validate_opt_in_subset`) and
will be reused for `hedge_commitments`.

### Ratification

Adding a field to the pack invalidates its prior mastery-report seal.
The default pack was re-ratified through
`scripts/ratify_ethics_pack.py` (idempotent re-run); the new
`mastery_report_sha256` reflects the schema addition.

### Backward compatibility

`build_refusal_surface(safety_verdict)` (the ADR-0036 single-arg
form) still works — with no ethics pack supplied, ethics contributes
nothing.  Existing safety-only tests pass unchanged because their
assertions are substring-based on the boundary id (now appearing as
`safety:<id>`).

## Consequences

### Positive

* **Audit-only remains the default.**  An operator who clones the
  default pack and deploys gets ADR-0036 behavior unchanged.
* **Per-commitment granularity.**  A medical-domain pack can opt
  `defer_high_stakes_to_human_review` into refusal without flipping
  the rest of the ethics surface.
* **Schema-enforced safety.**  Typos in `refusal_commitments` fail
  at load time, not at the first matching violation.
* **Unified refusal surface.**  Auditors see one refusal text per
  turn covering both safety and ethics violations, with source tags.

### Negative / risks

* **Pack mutation invalidates ratification.**  A deployment that
  edits `refusal_commitments` must re-ratify.  This is the intended
  cost: opting commitments into refusal is a deployment-level
  decision that deserves the ratification round-trip.
* **The opt-in list is JSON, which means it sits inside the swappable
  layer.**  This is correct semantically (refusal policy *is* a
  deployment choice) but means an operator can flip refusal on/off
  by editing a file.  Mitigated by: ratification round-trip,
  schema validation, and the load-time error for unknown ids.
* **Surface prefix changed.**  Downstream consumers parsing the
  refusal text by exact prefix needed an update.  We chose to update
  the constant in place rather than maintain a parallel API because
  no in-tree consumer existed.

## Verification

* `tests/test_ethics_refusal_opt_in.py` — 16 tests covering:
  loader bounds (empty default, unknown id rejected, duplicate
  rejected, non-list rejected); pure builder paths (no opt-in →
  no refusal, opt-in + violation → refusal, opt-in subset
  semantics, non-runtime-checkable ignored, combined safety+ethics,
  ADR-0036 back-compat); helper `violated_runtime_checkable_ethics`;
  ChatRuntime integration (default pack does not refuse, mutated
  pack refuses, combined safety+ethics in runtime).
* Combined pack-layer suite: **132 tests, all green**.
* CLI suites: smoke 67, runtime 19, cognition 121 — unchanged.

## Open questions deferred to a future ADR

1. **Pack-schema-driven hedge injection.**  Sibling field
   `hedge_commitments` follows in ADR-0038 — same opt-in pattern,
   different remediation.
2. **Mutual exclusion between `refusal_commitments` and
   `hedge_commitments`.**  Encoded at load time in ADR-0038.
3. **Per-domain default policies.**  Should the medical-domain pack
   ship with `defer_high_stakes_to_human_review` opted into refusal
   by default?  Deferred until a medical pack actually exists.
4. **Telemetry split by source.**  A future telemetry sink may want
   to count safety refusals and ethics refusals separately.
