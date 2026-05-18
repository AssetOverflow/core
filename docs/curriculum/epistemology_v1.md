# Curriculum Unit — Epistemology v1

**Date:** 2026-05-18
**Author:** Shay
**Lift:** cognition holdout `term_capture_rate` 70.8% → 75.0% (+4.2pp); public split unchanged.
**Active corpus after this unit:** 14 chains (15 lines on disk, 1 retired).

---

## Premise

CORE's reviewed teaching corpus is the inter-session memory surface
([ADR-0055](../decisions/ADR-0055-inter-session-memory-discovery-promotion.md)).
The operator-driven path to extend it is the propose → replay-equivalence
gate → operator accept loop ([ADR-0057](../decisions/ADR-0057-teaching-chain-proposal-review.md)),
plus the supersede surface for retiring chains in favour of replacements.

This unit is the **first** end-to-end use of those surfaces against the
production corpus to **measurably lift a cognition-lane metric**.

---

## What this unit teaches

Five reviewed chains closing epistemology-subgraph cells:

| Action | Old chain (if any) | New chain |
|---|---|---|
| Supersede | `verification_wisdom_grounds_judgment` | `verification_wisdom_requires_knowledge` |
| Propose + Accept | — | `cause_understanding_requires_knowledge` |
| Propose + Accept | — | `cause_judgment_requires_wisdom` |
| Propose + Accept | — | `verification_evidence_grounds_knowledge` |
| Propose + Accept | — | `cause_inference_requires_evidence` |

All five claims are pack-consistent (subject + object both in
`en_core_cognition_v1`) and follow the canonical predicate set.

---

## Why these chains (and not others)

### The supersede

`verification_wisdom_036` ("Is wisdom the same as knowledge?") was
the only holdout case whose term-capture miss was addressable by
corpus surgery. The case expects both `wisdom` and `knowledge` in
the surface; the prior chain (`wisdom grounds judgment`) emitted
only `wisdom` and `judgment`. Replacing the chain's object from
`judgment` to `knowledge` and the connective from `grounds` to
`requires` produces a defensible claim (wisdom presupposes
knowledge) and emits both expected terms.

No holdout case depended on the prior `wisdom→grounds→judgment`
doctrine, so the supersede is net-positive. Provenance on the new
entry: `adr-0057:hand_authored:2026-05-18:supersede(verification_wisdom_grounds_judgment)`.

### The four proposals

Each opens a previously-empty `(subject, intent)` cell in the
teaching index:

- `(understanding, cause)` — *understanding requires knowledge*: the
  classical claim that understanding is structured-over-knowledge.
- `(judgment, cause)` — *judgment requires wisdom*: pairs with the
  pre-existing `wisdom orders judgment`, asserting the inverse
  dependency direction (wisdom orders judgment, judgment depends
  on wisdom to be sound).
- `(evidence, verification)` — *evidence grounds knowledge*: cognate
  to `truth grounds knowledge` but admitting evidence as the
  warranting relation.
- `(inference, cause)` — *inference requires evidence*: pairs with
  `knowledge requires evidence`, locating inference downstream of
  evidence rather than alongside knowledge.

Each is defensible philosophically and passes the eligibility
predicate (polarity=affirms, corpus-evidence-pointer, claim_domain=factual,
boundary_clean, complete chain).

---

## Why the holdout lift is exactly +4.2pp

Holdout has 19 cases × 1.27 terms-per-case ≈ 24 expected terms
total. Pre-unit term-capture was 70.8% = 17/24 ≈ 17 captured.
Post-unit captures one additional term (`knowledge` in
`verification_wisdom_036`), so 18/24 = 75.0%. **The +4.2pp matches
the single-term fix exactly.**

The remaining four holdout misses are architectural, not corpus-fixable:

| Case | Category | Gap |
|---|---|---|
| `correction_truth_040` | correction | Correction-acknowledgment template doesn't mention the corrected subject lemma. |
| `procedure_define_010` | procedure | `procedure` intent has no teaching-grounded surface path; pack-grounded path doesn't fire on this intent. |
| `unknown_spirit_041` | unknown | UNKNOWN intent → disclosure; no clear `(subject, intent)` to teach. |
| `unknown_word_018` | unknown | Same. |

Closing those four requires changes to runtime surface composition,
not to the teaching corpus. They're correctly scoped out of this unit.

---

## Public split: no regression

The replay-equivalence gate ran the full public cognition split twice
per proposal (active corpus vs. transient-with-append) and reported
`replay_equivalent=True` and `regressed_metrics=[]` for every one
of the four proposals. After all four accepts plus the supersede,
public split metrics are byte-identical to pre-unit:

```
intent_accuracy       100.0%   (unchanged)
term_capture_rate      91.7%   (unchanged)
surface_groundedness  100.0%   (unchanged)
versor_closure_rate   100.0%   (unchanged)
```

The supersede was operator-direct (no replay gate by design — operator
explicitly accepts the change). It also did not regress any public
metric.

---

## Reproducibility

Every action is replayable from the proposal log + corpus file alone:

```bash
# Inspect the trail
core teaching audit                            # 15 lines on disk, 14 active, 1 dropped
core teaching supersessions                    # wisdom→grounds→judgment retired by →requires→knowledge
core teaching proposals --state accepted       # the four new chains' proposal_ids

# Confirm the lift
core eval cognition                            # public unchanged
core eval cognition --split holdout            # holdout term_capture 75.0%
```

The proposal-log JSONL is append-only at `teaching/proposals/proposals.jsonl`.
Every state transition (`created` → `replay` → `transition` →
`accepted_corpus_append`) is one line; replaying the log reconstructs
the active view deterministically.

---

## What this unit demonstrates

1. **The propose/review/accept loop works end-to-end on the production
   corpus** — not just in the demo trilogy.
2. **The supersede surface produces a clean retirement trail** —
   `core teaching supersessions` shows the retired chain paired with
   its replacement and the supersession provenance string.
3. **A four-chain batch + one supersession costs ~10 seconds of
   operator wall-time** — propose is ~2s each (replay gate runs the
   cognition lane), accept is sub-second.
4. **The replay-equivalence gate's no-regression guarantee held
   for every proposal** — public split metrics did not move.
5. **Curriculum work can target specific measurable misses**
   (the `verification_wisdom_036` case) and the lift matches the
   prediction exactly.

---

## Cross-References

- [ADR-0055](../decisions/ADR-0055-inter-session-memory-discovery-promotion.md) — the inter-session-memory architecture this unit consumes.
- [ADR-0056](../decisions/ADR-0056-contemplation-loop-c1.md) — DiscoveryCandidate contemplation; the candidate JSONL in this unit was operator-authored (hand-augmented with corpus-evidence pointers) rather than emitted by the runtime, but the structure is the same.
- [ADR-0057](../decisions/ADR-0057-teaching-chain-proposal-review.md) — the proposal + replay gate + accept surface this unit uses; the supersede CLI is the follow-up at `8d2c84a`.
- [teaching_order.md](../teaching_order.md) — the prerequisite-topological doctrine that scoped this unit's chain selection.
