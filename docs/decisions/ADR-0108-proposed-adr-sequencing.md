# ADR-0108 — Proposed-ADR Sequencing Post-ADR-0105

**Status:** Proposed
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Relates to:** ADR-0080, ADR-0084, ADR-0087, ADR-0106

---

## Context

After ADR-0105, the ADR index carries four Proposed-but-not-Accepted ADRs:

| ADR | Proposed | Origin |
|---|---|---|
| ADR-0080 | 2026-05-20 | Contemplation loop (self-interrogation, read-only Phase 1) |
| ADR-0084 | 2026-05-20 | Definitional layer for lexicon packs (optional per-entry block) |
| ADR-0087 | 2026-05-20 | Rhetorical style as a third substantive selection axis |
| ADR-0106 | 2026-05-22 | Expert-demo promotion contract |

Three of these (0080 / 0084 / 0087) were proposed in a single 2026-05-20
session and have not advanced. The frontier work since that day went into
the ADR-0091→0105 evidence-governed domain chain (a different axis), so
the stall is *orthogonal scope*, not contradiction or rejection.

`docs/decisions/README.md` currently states "No ADR currently sits in a
'Proposed but unimplemented' state." That sentence is no longer true and
the README will need updating once this sequencing decision is accepted.

Without an explicit sequencing decision, three things happen:

1. The Proposed-ADR list grows without external legibility.
2. Reviewers cannot tell *intent to land* from *intent to defer* from
   *intent to withdraw*.
3. Future "what's next?" questions re-derive sequencing on every read,
   which is wasted work and drifts over time.

ADR-0108 makes the sequencing decision explicit, durable, and revisable.

---

## Decision

### 1. Priority order

The four currently-Proposed ADRs are sequenced as follows:

1. **ADR-0106 — Expert-Demo Promotion Contract.** *Highest priority.*
   Domain-legibility: the four `reasoning-capable` ratifications overstate
   what the system has demonstrated until `expert_demo` has a real
   contract. Implementation PR follows acceptance.

2. **ADR-0107 — `mathematics_logic` expert-demo promotion (reserved).**
   First worked promotion against the ADR-0106 contract. Smallest
   expert-demo proof surface across the four ratified domains.

3. **ADR-0080 — Contemplation Loop.** *Next-most-load-bearing.* Converts
   gap-finding from human-driven to system-emitted-and-reviewed.
   Phase 1 is intentionally read-only and `SPECULATIVE`-only. Unlocks
   curriculum growth speed.

4. **ADR-0084 — Definitional Layer.** *Deferred pending ADR-0107.* The
   definitional block is content-shaped; its value surfaces during a
   worked expert promotion when definitional depth becomes a bottleneck.
   Holding it Proposed avoids premature schema commitment.

5. **ADR-0087 — Rhetorical Style Axis.** *Lowest current priority.*
   Register + anchor-lens already demonstrate the orthogonality pattern
   ADR-0087 generalizes. No active pull from a downstream consumer.
   Stays Proposed until a concrete consumer ADR motivates it.

### 2. No withdrawals

This ADR withdraws none of 0080 / 0084 / 0087. Each remains Proposed and
intact. Sequencing ≠ rejection.

### 3. Sequencing is revisable

Acceptance of ADR-0108 does not freeze the order. The order is the
*current* best guess; new evidence (a worked promotion that hits a
definitional bottleneck, a downstream rhetorical-style consumer landing,
an unanticipated capability gap) updates the order by a follow-up ADR.

### 4. README discipline

The README "Current frontier" section MUST list every Proposed ADR with
its sequencing rank and one-line rationale, so outside readers can see
intent without reading every ADR body. The sentence "No ADR currently
sits in a 'Proposed but unimplemented' state" is removed when this ADR
lands and is replaced with the sequenced Proposed-ADR list.

---

## Invariants

### `proposed_adr_index_complete`

Every ADR with `Status: Proposed` in `docs/decisions/` must appear in the
README "Current frontier" sequencing list. A Proposed ADR absent from the
sequencing list is a documentation drift bug.

### `no_silent_withdrawal`

A Proposed ADR may move to `Withdrawn` only by a successor ADR that
explicitly cites it. No silent deletion.

### `sequencing_is_revisable`

Acceptance of ADR-0108 does not lock the order. A subsequent ADR may
re-rank Proposed ADRs by citing this one and stating the trigger.

---

## Acceptance evidence

Accepted when the following land together:

- README "Current frontier" updated to:
  - remove the "No ADR currently sits in a 'Proposed but unimplemented'
    state" claim
  - add the ranked Proposed-ADR list with one-line rationales matching
    §Decision
- this ADR's status flipped to Accepted
- no body content of ADR-0080 / 0084 / 0087 / 0106 is modified by this PR
  (sequencing is a meta-decision, not a content edit)

---

## Consequences

- "What's next?" becomes a one-screen read on `docs/decisions/README.md`
  rather than a four-file scan plus reasoning.
- Reviewers can act on Proposed ADRs in declared order without
  cross-checking session memory.
- Proposed ADRs that genuinely no longer fit get a documented exit via
  a successor ADR rather than disappearing from the index.
- Future "candidate frontier" bullets in the README become the on-ramp
  to a new Proposed ADR, with this sequencing list as their next stop.

---

## Out of scope

- This ADR does not implement any of the four Proposed ADRs.
- This ADR does not modify ADR-0080 / 0084 / 0087 / 0106 bodies.
- Multi-reviewer governance (the open ADR-0105 candidate frontier item)
  is orthogonal and remains future work.
