# ADR-0103 — Fluency Lane Attachment for ADR-0102

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0102

---

## Context

ADR-0102 ratified `hebrew_greek_textual_reasoning` with only universal reasoning lanes attached:

- `inference_closure`
- `fabrication_control`

At the time, the language-specific Hebrew and Koine Greek fluency lanes did not yet expose sealed holdout splits, so attaching them to ratified contracts would have violated ADR-0091 expectations around `dev/public/holdout` coverage.

Both lanes now ship plaintext holdout sets through:

```text
holdouts/v1/cases.jsonl
```

and can therefore be attached to the ADR-0102 manifests without weakening the contract discipline.

---

## Decision

Attach the following eval lanes to all four ADR-0102 manifests:

- `hebrew_fluency`
- `koine_greek_fluency`

Each lane declares:

```jsonc
{
  "version": "v1",
  "splits": ["dev", "public", "holdout"]
}
```

The following packs must remain uniform:

- `he_core_cognition_v1`
- `he_logos_micro_v1`
- `grc_logos_cognition_v1`
- `grc_logos_micro_v1`

All four manifests advance provenance to:

```text
adr-0103:reviewed:2026-05-22
```

---

## Acceptance evidence

Accepted after the following landed together:

- Hebrew holdout cases
- Koine Greek holdout cases
- updated fluency contracts
- updated gap notes
- updated sibling-ratification invariants
- uniform lane attachment across all four manifests

---

## Invariants

### `hebrew_greek_fluency_lanes_uniform`

All four ADR-0102 packs must declare identical eval-lane coverage.

### `hebrew_greek_fluency_holdouts_present`

Both:

- `hebrew_fluency`
- `koine_greek_fluency`

must ship non-empty `holdouts/v1/cases.jsonl` before appearing in ratified domain contracts.

---

## Consequences

- ADR-0102 now carries language-specific fluency evidence in addition to universal reasoning evidence.
- Hebrew/Greek textual reasoning contracts now satisfy full `dev/public/holdout` discipline for attached fluency lanes.
- Future language-track ADRs can extend morphology and construction coverage without changing Domain Pack Contract v1.
