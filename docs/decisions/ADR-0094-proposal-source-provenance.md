# ADR-0094 — Proposal Source Provenance

**Status:** Accepted
**Date:** 2026-05-21
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers

---

## Acceptance evidence

Accepted after the sealed `ProposalSource` schema, exhaustive-match consumers, and deterministic migration landed:

- `teaching/source.py` defines the sealed `ProposalSource` type with `kind` ∈ {operator, miner, curriculum}, serialization, and parse-time rejection of unknown kinds.
- `teaching/proposals.py` widens `PackMutationProposal` / `TeachingProposal` to carry a required `source: ProposalSource` field; parsing fails without it.
- `teaching/store.py` consumers branch on `source.kind` via exhaustive `match`.
- `teaching/migrate_proposals_source_field.py` provides the one-shot deterministic rewriter; two runs produce byte-identical output.
- `tests/test_proposal_source.py` exercises round-trip serialization, parse-time rejection, exhaustive-match enforcement, and migration determinism.
- `tests/test_epistemic_invariants.py` pins `proposal_source_exhaustive_match`.

---

## Context

`teaching/proposals/proposals.jsonl` and the surrounding review flow
(`teaching/review.py`, `teaching/store.py`, ADR-0057) currently assume
proposals originate from a single source: an operator authoring through
the existing teaching CLI. The schema has no typed source field.

Two near-term ADRs widen this:

- ADR-0095 introduces miner-sourced proposals (contemplation Phase 5
  loop closure).
- A future ADR will introduce curriculum-sourced proposals (deferred
  per the rewrite blueprint).

Without a typed source field, downstream consumers (`teaching/review.py`,
capability ledger evidence rows, audit telemetry) will branch on string
prefixes informally. That is the same shape of mistake ADR-0067's
explicit `subject_pack_id` / `object_pack_id` fields prevented for
cross-pack chains.

---

## Decision

Introduce a sealed `ProposalSource` type widening
`PackMutationProposal` / `TeachingProposal` schemas. The widening is
schema-only; no runtime behavior changes under this ADR.

### Sealed type

```python
@dataclass(frozen=True, slots=True)
class ProposalSource:
    kind: Literal["operator", "miner", "curriculum"]
    source_id: str  # "" for kind="operator"; miner_id or course_id otherwise
    emitted_at_revision: str  # git SHA at emission

    def serialize(self) -> str:
        # "operator", "miner:articulation_quality", "curriculum:math_logic_v1"
        return self.kind if not self.source_id else f"{self.kind}:{self.source_id}"
```

### Schema migration

- New field on `PackMutationProposal` and `TeachingProposal`:
  `source: ProposalSource`.
- Default for existing operator-authored proposals: `ProposalSource(kind="operator", source_id="", emitted_at_revision=<head>)`.
- Migration is one-shot at ADR landing: a deterministic rewriter walks
  existing `proposals.jsonl` files, attaches the default operator
  source, and rewrites in sorted order. Migration is a reviewed
  proposal itself.

### Consumer rules

- `teaching/review.py` performs exhaustive match on `source.kind`. Any
  new kind requires a new ADR adding a branch.
- Telemetry events (`chat/telemetry.py`) carry `source.serialize()` as
  a string field. Redact-by-default already covers proposal content;
  source is non-sensitive and emitted plainly.
- Capability ledger evidence rows (ADR-0091) include `source` in their
  provenance trail.

### What this ADR does not do

- Does not introduce miner-sourced proposals (ADR-0095).
- Does not introduce curriculum-sourced proposals.
- Does not change review thresholds. Source affects audit, not gate.

---

## Invariant

`proposal_source_exhaustive_match` — every code path that branches on
`proposal.source.kind` uses Python `match` with explicit cases for each
sealed-type value; the type checker refuses a non-exhaustive match. A
proposal without `source` fails parsing.

---

## Lane

`evals/proposal_source_schema/` (new, small):

- positive: round-trip serialization for each `kind`
- negative: missing `source` field rejected at parse
- negative: unknown `kind` rejected at parse
- migration: existing `proposals.jsonl` rewritten deterministically;
  two runs produce identical bytes

---

## Trust Boundary

`source_id` is a typed string but flows through user-adjacent surfaces
(telemetry, ledger reports). It is sanitized via
`core/_safe_display.safe_display` at all surface emission points,
matching the discipline established in ADR-0051. The migration rewriter
runs only when invoked explicitly; no implicit on-load mutation.

---

## Consequences

- ADR-0095 can introduce `kind="miner"` without secondary schema churn.
- A future curriculum ADR can introduce `kind="curriculum"` the same way.
- Existing operator review flow is unchanged; the new field is set to
  its operator default on every existing proposal.

---

## PR Checklist

- Capability added: typed provenance schema for proposals.
- Invariant proved: `proposal_source_exhaustive_match`.
- Lane proving it: `evals/proposal_source_schema/`.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none. Migration is explicit and reviewed.
- Trust boundary: `source_id` sanitized at every surface; no implicit on-load rewrites.
