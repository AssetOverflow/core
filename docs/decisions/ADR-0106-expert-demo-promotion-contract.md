# ADR-0106 — Expert-Demo Promotion Contract

**Status:** Proposed
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096, ADR-0097, ADR-0100, ADR-0101, ADR-0102

---

## Context

Four domains now sit at `reasoning-capable` in the ledger (`mathematics_logic`,
`physics`, `systems_software`, `hebrew_greek_textual_reasoning`). The
`expert_demo` field on each ledger row is `false` and currently has no
domain-aware contract behind it.

`core/capability/reporting.py:418` is the only site that can flip
`expert_demo` to `true`, and it does so by reading the **cognition** lane's
`public`/`holdout` metrics regardless of which domain is being scored. This is
incoherent: a math ratification cannot be promoted to `expert_demo` by
evidence from a cognition pack it never claimed against.

Without a domain-aware contract, `reasoning-capable` is the ceiling — and
that ceiling is "contract predicates satisfied, no fabrication, operator
coverage above floor," which is *not* the same claim as "the system can do
real expert work in this domain." External readers cannot distinguish the
two, so the ratification ledger overstates what the system has actually
demonstrated.

ADR-0106 closes that gap.

---

## Decision

Introduce `expert_demo` as a **domain-scoped, reviewer-signed** capability
promotion, not a global threshold.

### 1. Promotion predicate (domain-aware)

`expert_demo = true` for a ratified domain *D* requires **all** of:

1. *D* is already `reasoning-capable` (ADR-0093 contract still holds).
2. Every lane attached to *D*'s ratified packs reports `public` and `holdout`
   splits at:
   - `surface_groundedness >= 0.95`
   - `term_capture_rate     >= 0.85`
   - `intent_accuracy       >= 0.95`
   - `versor_closure_rate   == 1.0`
3. *D*'s `fabrication_control` lane is `passed=1.0` on both `public` and
   `holdout`.
4. A signed **expert-demo claim** exists in the reviewer registry under a
   new `expert_demo_claims` block, naming:
   - `domain_id`
   - `evidence_lanes` (list of lane ids consulted)
   - `evidence_revision` (git sha at promotion time)
   - `signed_by` (reviewer id from ADR-0092 registry)
   - `claim_digest` (SHA-256 over the canonical evidence bundle)
5. The promotion is **replay-deterministic**: re-running the consulted lanes
   at `evidence_revision` reproduces `claim_digest` byte-for-byte.

If any condition fails the row stays at `reasoning-capable`. Promotion is
never silent — it requires both mechanical thresholds AND a reviewer
signature.

### 2. Reporting changes

`core/capability/reporting.py` stops consulting the cognition lane for
non-cognition domains. The expert-demo branch consults *the domain's own
attached lanes*. The cognition lane keeps its existing thresholds only when
the domain under evaluation is the cognition pack itself.

### 3. First worked promotion

This ADR does **not** promote any domain. It defines the contract.

A follow-up ADR (`ADR-0107`, expected to be `mathematics_logic`) will be
the first worked expert-demo promotion against the contract defined here,
including the reviewer-signed claim and the SHA-pinned evidence bundle.

---

## Invariants

### `expert_demo_requires_signature`

No domain row may carry `expert_demo=true` without a corresponding entry in
`expert_demo_claims` whose `claim_digest` matches the re-derived evidence.

### `expert_demo_domain_aware`

The reporting layer must consult only lanes attached to the domain's
ratified packs when computing `expert_demo`. Cross-domain lane bleed
(e.g. cognition lane metrics deciding a math promotion) is rejected by a
test gate.

### `expert_demo_replay_byte_equality`

Re-running every consulted lane at `evidence_revision` must reproduce the
exact JSON bytes hashed into `claim_digest`. A drift here demotes the row
to `reasoning-capable` until re-signed.

---

## Acceptance evidence

Accepted when the following land together:

- `expert_demo_claims` block added to the reviewer registry schema (ADR-0092
  extension, additive only)
- domain-aware `expert_demo` predicate in `core/capability/reporting.py`
- new test `tests/test_expert_demo_contract.py` covering the three
  invariants above
- updated `docs/decisions/README.md` index and "Accepted reasoning-capable
  domains" table noting the `expert_demo` column is contract-gated (not
  thresholded only)
- no domain row's `expert_demo` field flips by this ADR — only the contract
  changes

---

## Consequences

- "Reasoning-capable" becomes an honest ceiling: it means the contract
  predicates hold, not that the system has demonstrated expert work.
- Promoting a domain to `expert_demo=true` now requires deliberate
  reviewer action and replayable evidence — the same discipline that
  ADR-0092 imposed on reviewers themselves.
- The ledger becomes externally legible: an outside reader can tell at a
  glance which domains are *contract-passing* versus *demonstrated*.
- Opens the door to ADR-0107+ as worked promotions, starting with
  `mathematics_logic` as the smallest expert-demo proof surface.

---

## Out of scope

- This ADR does not change Domain Pack Contract v1 (ADR-0091).
- This ADR does not introduce new eval lanes.
- This ADR does not promote any existing domain — promotions are separate
  ADRs that consume this contract.
- Multi-reviewer threshold signing (ADR-0105 candidate frontier) is
  orthogonal and remains future work.
