# evals/reviewer_registry — Lane Contract

**ADR:** ADR-0092
**Invariant:** `reviewer_registry_schema_v1`

## Purpose

Prove that ADR-0092's Reviewer Registry v1 schema is enforced. The lane
asserts:

1. A schema-valid registry loads without error and exposes the expected
   reviewer count and ids.
2. Each ADR-0092 schema violation produces a typed
   :class:`ReviewerRegistryError` whose message names the failing field.
3. An empty registry (`reviewers: []` with no entries) blocks all
   `reasoning-capable` claims under ADR-0091 by producing zero
   resolvable reviewer ids.
4. A registry without `schema_version: 1` is rejected before any
   reviewer entry is parsed.

## Cases

The runner iterates over the case fixtures in this directory:

- `cases/positive_primary.yaml` — single primary reviewer, must load.
- `cases/positive_domain.yaml` — single domain reviewer, must load.
- `cases/negative_empty.yaml` — `reviewers: []`, must load with zero
  reviewers (no error, but no resolvable id either).
- `cases/negative_wrong_version.yaml` — `schema_version: 2`, must reject.
- `cases/negative_domain_wildcard.yaml` — domain reviewer claims
  `["*"]`, must reject.
- `cases/negative_unknown_field.yaml` — reviewer entry has an
  unrecognized field, must reject.

## Determinism

The runner emits a `results/v1_dev.json` containing per-case outcomes
and a SHA-256 of the report bytes. Two consecutive runs against the
same fixtures must produce identical bytes.

## Exit code

The runner exits non-zero on any case whose actual outcome diverges
from the case spec.
