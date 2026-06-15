# Step-3 relational-surface lookback (2026-06-15)

**Scope.** Cross-PR lookback review of the three relational capabilities now composed on
`main @ 0be18ebd`:

- **#775** — one-hop inverse/converse + pack-declared symmetric relational inference (breadth 9→10).
- **#781 (B2)** — transitive strict-order relational inference (breadth 10→11).
- **#783 (B3)** — `overlaps_event` finite-verb reader surface (`comprehension_relational_predicate` 17→18).

**Method.** A 5-auditor read-only sweep over the merged surface — predicate tables,
cross-capability interactions, soundness/proof discipline, measurement integrity, and
documentation — re-verified independently against source, plus the full test gauntlet on
merged main (below). This complements (does not replace) the per-PR adversarial reviews
that ran on #781 and #783.

## Verdict: SOLID — clear to stop before B4

**37 solid findings, 0 hazards, 0 drift, 0 fix-before-next-phase.** One minor gap
(cosmetic test decoration), fixed in this PR. No live `wrong=0` risk anywhere on the
composed surface.

### Verification (merged `main @ 0be18ebd`)

| Gate | Result |
|---|---|
| Relational + capability + OWA lanes (`test_determine_relational_*`, `*_lane`, `test_composition_lower_transitive`, `test_capability_*`, `test_proofwriter_owa_lane`) | 128 passed |
| INV-30 / 29 / 21 / 25 / 27 firewalls | 19 passed |
| Full smoke (`test_architectural_invariants` + runtime + pipeline + packs) | 99 passed |

## Solid (the load-bearing claims, re-confirmed)

**Predicate tables (closed, correctly placed, non-vacuously pinned).**
`INVERSE_OF` is a closed involution (8 keys, no self-inverse); `SYMMETRIC_PREDICATES`
equals the pack's `graph.edge.symmetric` ontology; `TRANSITIVE_PREDICATES` is *exactly*
`{less_than, greater_than, before_event, after_event}` with all 9 named non-strict-order
predicates absent; the finite-verb table admits `overlaps_event` only. All four pinning
tests (`test_transitive_predicates_closed_and_excludes`, `…symmetric_table_matches_pack_ontology`,
`…algebra_members_are_relational_predicates`, `…inverse_is_an_involution`) fail under
exactly the mis-placement they guard (auditor injected each violation and confirmed the
failure). *The one non-empty cross-table overlap — `INVERSE_OF ∩ TRANSITIVE` = the four
strict orders — is intentional and sound: a strict order is legitimately both transitive
(`a<b ∧ b<c ⊨ a<c`) and has a converse (`a<b ⟺ b>a`); independent compatible properties,
not a mis-placement.*

**Interactions (firewalled).**
(1) inverse + transitive do **not** compose — `_relational_transitive` recalls only the
queried predicate's edges (`recall_realized(predicate=predicate)`) and `lower_transitive_chain`
re-rejects any off-predicate edge, so transitive-closure-then-inverse refuses.
(2) symmetric predicates do **not** become transitive (`sibling_of`/`spouse_of` ∉
`TRANSITIVE_PREDICATES`; the transitive branch is double-gated).
(3) the finite-verb branch is **not** a generic parser — only the literals `overlaps`/`overlap`;
every other verb falls through to the copula grammar and refuses.
(4) the other 15 connectives still **require the copula** — the copula branch is
byte-unchanged; `Monday before Friday.` refuses.
(5) query surfaces do **not** fabricate — the single-token slot gate holds on both the
finite-verb and copula query paths.

**Soundness (True-only, search-then-verify).**
Every `Determined` construction is `answer=True` (exactly 3 sites; no `answer=False`
anywhere); INV-30 is mechanically enforced and non-vacuous. The transitive path is
search-then-verify — BFS proposes, the `proof_chain` ROBDD verifies, corrupted /
non-contiguous / cross-predicate paths refuse. The ProofWriter-OWA floor asserts True only
on gold-True against a disjoint oracle (INV-25/27) and fails on `wrong>0`. B3 is reader-only
— `determine.py` untouched, so INV-30 is structurally unaffected.

**Measurement.**
`baseline.json`: breadth 11, `wrong_total` 0, `not_covered` empty, deterministic digest.
Inference + transitive fixture SHA pins recomputed and accurate; the `relational/v1` reader
lane is an (unpinned) count lane. Refusal floors **rose, never shrank** (the one inference
confuser removed in #781 was a legitimate migration — a `less_than` chain that now correctly
*determines*, moved to a positive). The #779 OWA floor is correctly **not** registered as a
capability-index domain.

**Documentation.**
Module + function docstrings in `relational.py` / `determine.py` reflect the landed one-hop,
transitive, and finite-verb capabilities — no stale "out of scope / impossible / follow-up"
claims. Provenance docs reflect all three PRs (the B3 overlaps gap is documented as
**resolved**). **ADR-0222 (B4) remains design-only — no runtime `FrameVerdict` / `ClosedFrame`
/ `evaluate_frame_verdict` / closed-world `entailed_false` implementation exists; INV-31 is a
future obligation, not yet a test.** The Step-3 handoff brief correctly marks B4 as DESIGN ONLY.

## Gaps (no risk — fixed in this PR)

- `test_symmetric_table_matches_pack_ontology(pack)` declared an unused `pack` fixture
  parameter (the body re-loads the pack internally). Cosmetic; the test is non-vacuous.
  **Fixed here** (parameter removed).

## Drift / Hazards

None. No documentation-vs-implementation drift; no live `wrong=0` hazard surfaced on the
composed surface.

## Conclusion

**Step-3 relational implementation is complete and stable.** The one-hop, transitive, and
finite-verb capabilities compose cleanly with no cross-PR regression, every determination
stays open-world True-only, and the B4 / closed-world boundary (ADR-0222) is untouched and
design-only. No further relational-surface work is required before the (separately-ratified)
B4 implementation track.
