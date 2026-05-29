# ADR-0178 — Compositional Structure: Comprehension-Guided Multi-Step Derivation (Gap B)

**Status:** Proposed
**Date:** 2026-05-28
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Builds on / synthesises:**
- [ADR-0174 — Held-Hypothesis Comprehension](./ADR-0174-held-hypothesis-comprehension.md) — its held-hypothesis / `eliminate_violating` / `reevaluate` / `contemplate` substrate is **repointed** here from reading-to-parse to reading-to-*structure* (where it finally becomes load-bearing).
- [ADR-0176 — Multi-Step Composition](./ADR-0176-multistep-composition-question-targeting.md) — the chain model + the self-verification gate that scores each structure.
- [ADR-0177 — Cue-Precision Learning](./ADR-0177-cue-precision-learning.md) — the learned `(cue→op)` reliabilities that *guide* the structural search and that this search *feeds*.
- The comparatives pack (and a future relational-cue / superordinate-units pack) — the irreducible relational world-facts.

---

## Context — the actual flip lever, and what it really is

MS-3 proved the multi-step search is built and wrong=0-safe but low-coverage: blunt
whole-problem shapes (product-of-all / sum-of-all) flip only the one case where the
shape happens to match (0021), and a rich *unguided* search drowns in
disagreement-refusals. The dominant failure (0019, 0041) is **compositional
structure** — *which* quantities group, via which ops, in what order. That is
**Gap B**, and ADR-0177 established it is the real coverage lever (cue-precision is
its safety gate and prune, not the unlock).

**The central tension:** a richer search produces more self-verifying candidate
structures that *disagree*, so uniqueness refuses more. Coverage cannot come from
enumerating more structures — it must come from **steering to the right one**.

**The reframe that resolves it — structure-from-reading, not enumeration.** The
text already encodes its own compositional structure: clauses group local
quantities, and relational cues across clauses say how the pieces combine. Every
gold structure fits a **sequential, clause-by-clause** read:

| Case | Read sequentially |
|---|---|
| 0021 | one clause: `15 × 10 × 3` |
| 0003 | `48` → `×24` (24 *in each* box) → `×0.75` (sell *for* $0.75 each) = 864 |
| 0024 | `20+36+40+50` (the *and*-list) → `×3` (*three times as many*) = 438 |
| 0033 | `12` → `×7` (7 *times*) → `÷2` (*half*) → `+5` (5 *older*) → … |

So Gap B is, at bottom, **comprehension**: read the problem, build the derivation
structure as you read, holding alternatives when a clause is ambiguous and revising
on lookback when a later clause disambiguates. This is precisely the original
project articulation — *"articulate word to word, with lookback re-evaluation, with
problem-solving throughout, without insane complexity."* It is also the synthesis
of every prior strand: the **reader** (ADR-0174) supplies structure, the **solver/
gate** (ADR-0176) scores it, the **learning** (ADR-0177) guides it, the **packs**
supply the relational facts.

## Decision

A **comprehension-guided sequential composer**: read the problem clause-by-clause;
within a clause, derive a local sub-result by a *small, bounded* search over that
clause's few quantities; across clauses, combine the running result with the next
clause via the **relational cue** the text presents (per/each/of → multiply; same-
unit *and*-list → sum; comparative → scale; more/older/then → add; fewer/less/lost →
subtract; fraction-of → scalar). When a clause's relation is ambiguous, **hold
multiple candidate structures** and eliminate them downstream (repointed ADR-0174
machinery); when a later clause disambiguates an earlier choice, **reevaluate**
(repointed). Every structure is scored by the ADR-0176 self-verification gate
(grounding ∧ cue ∧ unit ∧ completeness) + uniqueness; the relational cue→op choices
are guided/ranked by ADR-0177 cue-precision.

**Why this gets coverage *without* breaking wrong=0:** locality bounds the search
(each clause has few quantities → no flat explosion), and the text's relational
cues *constrain* the cross-clause op (so the surviving structure set is small enough
that uniqueness can **resolve**, not just refuse). Where the text is genuinely
ambiguous and no constraint or learned cue-precision resolves it, the held-
hypothesis set stays >1 and the composer **refuses** — refuse-preferring, unchanged.
Coverage rises exactly as far as the reading constrains the structure; no further.

### Repointing ADR-0174 (where the inert reader becomes load-bearing)

ADR-0174's held-hypothesis substrate was built for reading-to-parse and is inert
(0/50). Gap B is its true home: `ProblemReadingState.open_hypotheses` becomes the
set of candidate *derivation structures*; `eliminate_violating` prunes structures a
later clause contradicts; `reevaluate` revises an earlier structural commitment;
`contemplate` consults vault/packs when a relation is unknown. These are reading-
coupled today (per ADR-0175's audit) and must be **generalised** off their parse-
specific types — not a drop-in, but the conceptual machinery is exactly right.

## wrong=0 obligations (must be *proven*, not asserted)

1. **Per-step self-verification.** Each clause-local and each cross-clause
   combination is grounded + unit-consistent before it joins the structure (the
   ADR-0176 gate, applied per step). A test fails if an ungrounded/unit-incoherent
   step is admitted.
2. **Irreducible ambiguity refuses.** When the held structure set stays >1 with no
   eliminating constraint or decisive cue-precision, the composer refuses (does not
   pick). A test fails if it resolves an unresolved hold.
3. **Completeness + uniqueness** (ADR-0176) over the *whole* structure: all body+
   question quantities used; a single distinct verified answer or refuse.
4. **No spurious structure.** A structure whose grouping is not licensed by the
   reading (relational cue absent/ungrounded) cannot self-verify even if its value
   matches gold (extends invariant #2 to trees/chains).
5. **Determinism/replay**; **sealed** (no serving import; serving stays `3/47/0`
   until Phase 5 ratifies).

## The honest hard parts

- **Relational-cue precision** — the cross-clause op hinges on relational lexemes
  (per/each/of, times/half, more/older, fewer/less, then). Their op-mapping is
  partly packs (comparatives) and partly learned (ADR-0177 cue-precision, which is
  itself bottlenecked + data-starved). This is the same Gap-A/Gap-B co-dependency:
  Gap B *produces* gold-matching chains that give cue-precision its signal, and
  cue-precision *ranks* Gap B's structural choices. They co-evolve.
- **Clause/clause segmentation** — deciding clause boundaries is itself a parse
  decision; start with sentence + simple conjunction splits, refine cautiously
  (ADR-0165: orthographic/lexeme splits, not grammar templates).
- **Referent binding** — *whose* value a clause refers to ("Brooke does 3× as many
  as Sidney" → scale *Sidney's* result). Cross-sentence entity tracking (ME-2 / the
  discourse-subject machinery already exists) must say which running value a
  relation applies to.
- **Branch/DAG structures (the hard end)** — 0033 reuses `12` in two branches
  (`12×7…` and `25−12`); a pure sequential chain cannot express quantity reuse. DAGs
  are GB-5, after chains work.
- **Data/scale** — coverage and the cue-precision it feeds compound only with volume
  (ADR-0163 §Phase F). On 50 cases this is mechanism + incremental flips, not a
  finished solver.

This is the **comprehension core** — the largest remaining capability and the place
serving lift actually materialises. It is multi-phase by nature; each phase is
gated wrong=0-first and measured honestly.

## Sub-phases

- **GB-1 — clause segmentation + clause-local sub-derivation.** Split the problem
  into clauses (lexeme/sentence-level); within a clause, a small bounded search over
  its quantities → a local sub-result (self-verified). Tests: locality bounds the
  search; a clause-local product/sum self-verifies; ambiguous clause holds/refuses.
- **GB-2 — sequential combination (chains).** Combine running result with the next
  clause via the relational cue → op (guided by ADR-0177 + comparatives). Flips the
  sequential-chain gold cases (0003/0024-class) under self-verification + uniqueness.
- **GB-3 — lookback / reevaluate** (repoint ADR-0174 `reevaluate`): a later clause
  revises an earlier structural choice. wrong=0-first.
- **GB-4 — held structural hypotheses + eliminate** (repoint `eliminate_violating` /
  `contemplate`): hold >1 structure on ambiguity, eliminate downstream, refuse if
  irreducible.
- **GB-5 — branch/DAG structures** (quantity reuse, 0033-class). The hard end.
- **GB-6 — measurement + perturbation + the cue-precision/scale dependency.**

## Acceptance criteria (Proposed → Accepted)

1. GB-1/GB-2 land; the per-step gate + completeness + uniqueness hold; sequential-
   chain gold cases flip under self-verification with `wrong=0` in serving.
2. Invariant: spurious/unlicensed structures and irreducible holds refuse (proven).
3. Flips hold under ADR-0114a perturbation; determinism/seal invariants hold;
   capability lanes G1–G5/S1 stay 100% `wrong=0`.
4. The measurement reports honestly against the relational-cue-precision + scale
   dependencies (no coverage claim the substrate can't support).

## Cross-references

- **Repointed substrate:** [ADR-0174](./ADR-0174-held-hypothesis-comprehension.md)
  (held hypotheses, `eliminate_violating`, `reevaluate`, `contemplate`,
  `ProblemReadingState`) — generalised from parse to structure.
- **Scoring/gate:** [ADR-0176](./ADR-0176-multistep-composition-question-targeting.md).
- **Guidance/learning (co-evolves):** [ADR-0177](./ADR-0177-cue-precision-learning.md).
- **Relational facts:** the comparatives pack + a future relational-cue /
  superordinate-units pack (ADR-0175 §10 self-proving-vs-pack split).
- **Scale:** ADR-0163 §Phase F.
- **Thesis & origin:** [[thesis-decoding-not-generating]] — this is the
  word-to-word, lookback-revised, problem-solving-throughout reader the project set
  out to build; Gap B is where it lands.
