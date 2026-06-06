# Step D — CLOSE: idle deductive consolidation of soundly-derived facts

**Date:** 2026-06-06
**Branch:** `feat/loop-learns-determined`
**Sequence:** A INSTRUMENT (#598/#599) → B WIRE (#600/#601) → C DEEPEN (#602) → **D CLOSE** → E ESTIMATION (last)
**Telos:** [[project-core-is-one-continuous-life]] — the loop *learns from determined facts*, not just the partial discovery chains it emits today.

## The scoped seam (read, not assumed)

The autonomous loop today is `extract_discovery_candidates → _pending_candidates →
idle_tick(contemplate → propose_from_candidate) → ProposalLog (pending, HITL)`. Two
findings from reading the source fix what D actually is:

1. **Today's loop is a within-corpus generalizer.** `extract_discovery_candidates`
   emits an *intentionally partial* chain `{subject, intent, connective:None,
   object:None}`; `contemplate` completes it *only* by enumerating objects the
   reviewed corpus already used, and `check_eligibility` **Gate 2** requires a
   `source="corpus"` evidence pointer. So it can only re-propose a shape the corpus
   already contains. It cannot learn a fact that arose in lived conversation.

2. **The HITL ProposalLog never reaches serving.** D's falsification — "the capability
   index climbs across loop iterations" — therefore *cannot* be met by emitting
   proposals (the index is a static breadth×accuracy eval, hard-gated to 0 on any
   wrong; proposals are HITL-gated and never feed serving). For the index to climb,
   a *determined fact must feed back into what the engine can answer.*

So the inevitable D is **session-memory consolidation**, not proposal emission:

> When idle, the engine consolidates each soundly-derived determination
> (`member∘subset`, `subset∘subset` — the transitive is-a reasoning C built) back
> into the realized-knowledge vault as a new realized record, so the *next*
> `determine()` reaches it directly and can chain one hop further. The directly
> answerable set climbs monotonically across idle ticks to the deductive-closure
> fixed point.

Emitting determined facts as HITL teaching-chain proposals is a *distinct* capability
that collides with Gate 2 (the corpus-evidence floor, a teaching-safety / wrong=0
surface). It is **deliberately deferred** to its own evidence-floor-touching PR rather
than bolted onto D — the falsifiable core stays clean.

## Mechanism (semi-naive deductive closure, one layer per tick)

`idle_tick` (gated by `config.consolidate_determinations`, default OFF) runs
`consolidate_once(ctx)`:

1. Recall realized `member` + `subset` facts.
2. Compute every **one-hop** extension under the two SOUND is-a rules:
   - `member(s,b) ∧ subset(b,t) → member(s,t)`
   - `subset(a,b) ∧ subset(b,t) → subset(a,t)`
   - **`member ∘ member` is never an edge** — instance-of is not transitive
     ("Socrates is a man" + "man is a species" ⊬ "Socrates is a species"). The
     reader's member/subset split is exactly what makes the included rules sound.
3. For each derived edge not already realized, **verify with the sound+complete
   proof_chain ROBDD** (reusing C's single verifier `_verify_subsumption` — no
   duplicate proof logic), then write it via `realize_derived`.

Each tick adds exactly one hop-layer; the closure saturates after `diameter` rounds;
re-running at the fixed point is a no-op. This is textbook semi-naive evaluation, and
it is precisely what produces the monotone "climbs across iterations" signal.

## Invariants held (the wrong=0 / honesty boundary)

- **Soundness (wrong=0).** Every consolidated fact is the conclusion of a sound rule
  over realized premises, *confirmed by the sound+complete decider* — defense in depth
  beyond the one-hop rule. The `member∘member` fallacy is structurally unreachable (no
  member→member edge). A consolidated `member(s,t)` can only be extended by a *subset*
  edge, never a member edge, so the fallacy stays unreachable across iterations.
- **Epistemic honesty.** A fact derived from SPECULATIVE premises is SPECULATIVE,
  `basis="as_told"`. The soundness of the *inference* never upgrades the *standing* of
  the premises. **COHERENT is never minted.**
- **Session memory, not reviewed learning.** Consolidation is the immediate session
  tier (allowed), an extension of the `generate.realize` path — **not** corpus
  mutation and **not** coupled to proposals. The teaching/review HITL path is
  untouched; no parallel learning path is created.
- **Sanctioned write path.** Writes reuse `_realize_structured` (the INV-21 allowed
  vault writer). No new normalization; no closure/repair — `algebra/versor.py` keeps
  closure. The derived record reuses the subject's `probe_ingest` placement, identical
  to a told fact about the same subject.
- **Idempotency / determinism.** Dedup on the span-free `structure_key` (identical to
  a told fact's, so a later told duplicate collapses). Deterministic order; no clock,
  no LLM, no metric call. Bounded by the existing `_SUBSUMPTION_SUBSET_FACT_BUDGET`.

## Provenance — the replayable proof obligation (Fork 2)

`Determined` already carries `grounds: tuple[RealizedRecord, ...]` — the premise
records that entailed it. The consolidated record records, as derived-provenance, the
premise `structure_key`s + the `rule` + the `verdict` (always `entailed`). This makes
the soundness claim **meaningfully fail** (per the Schema-Defined Proof Obligations
rule): a replay re-fetches the premises by `structure_key` and re-runs the rule +
proof_chain — if a consolidated fact were ever unsound, re-verification fails loudly.

## Falsification — `evals/determination_closure/`

A frozen replay seeds a deep is-a chain (`member(x,c0)`, `subset(c0,c1)…subset(cₙ₋₁,cₙ)`)
and runs idle consolidation ticks. Asserts:

- **Monotone climb:** the directly-realized `member(x, ·)` closure grows by exactly one
  per tick (each layer), strictly increasing until the fixed point.
- **Convergence:** after `n` ticks the closure is saturated; a further tick is a
  **no-op** (`at_fixed_point=True`, 0 consolidated).
- **wrong=0:** no `member(x, y)` is ever consolidated for `y` outside the chain's
  reachable set (no fabricated fact); the `member∘member` canary derives nothing.
- **Provenance replay:** every consolidated record's recorded premises re-verify as
  `ENTAILED`.

## Adversarial verification (5 independent skeptics, refute-the-claim)

A panel re-read the shipped source under five distinct lenses, each tasked to *refute*.
- **wrong=0 / soundness** — held. `member ∘ member` is structurally unreachable (member
  facts are only ever extended by subset edges); every write is proof_chain-`ENTAILED`;
  no cross-subject leakage. **Acted on its note:** `_verify_subsumption` now *refuses* a
  mislabeled/wrong-arity path (a member fact smuggled into `subset_path`), converting
  soundness-by-caller-discipline into soundness-by-construction now that consolidation is
  a second caller.
- **epistemic honesty** — held. `realize_derived` writes SPECULATIVE unconditionally;
  `_basis` returns `as_told` for SPECULATIVE grounds; `promote_eligible_entries`
  (SPECULATIVE→COHERENT) requires energy metadata derived facts never carry and is
  disjoint from `idle_tick`.
- **teaching-safety boundary** — held. Single write path (`ctx.vault.store`, `tier=
  "session"`); zero `teaching/`/proposal/pack/identity coupling; the two `idle_tick`
  passes are orthogonal (the proposal pass's vault probe filters to COHERENT, excluding
  these SPECULATIVE facts).
- **determinism / replay / persistence** — held. Sorted write order; derived
  `structure_key` identical to a told fact's; `Derivation` round-trips through the
  snapshot; the lane's `reverify_derived` meaningfully fails on a non-entailing record.
- **normalization / closure invariant** — flagged `high`, assessed a **misattribution**.
  The cited `vault.store → reproject → null_project` is pre-existing (`aadaf116`,
  2026-05-13, ~3 weeks before D), triggered *identically* by the already-merged
  `realize_comprehension` path, operates on vault **content** null-vectors (which
  CLAUDE.md says to preserve as null vectors — sanctioned), and is a different object
  from the runtime field `versor_condition(F)<1e-6` invariant the claim referenced. The
  lane's high `vault_reproject_interval` is the established determine/realize test idiom,
  not a D-specific sidestep. D adds zero normalization code and reuses the INV-21-allowed
  writer; the claim ("consolidation *adds* no forbidden normalization") stands.

## Out of scope (follow-ups)

- **Promotion firewall (defensive).** If a future change ever called
  `promote_eligible_entries` inside `idle_tick` or attached energy metadata to derived
  facts, SPECULATIVE derived facts could promote to COHERENT and bootstrap standing. No
  live path (the separation is architectural); a structural `derived ⇒ never-promote`
  marker would harden it.
- **Runtime vs. lane proof obligation.** The provenance replay (`reverify_derived`) runs
  in the eval lane, not per-write at runtime — matching the repo's "wrong=0 proven by
  lanes, not runtime asserts" pattern (consolidation already verifies each write *before*
  writing). Noted, not a gap.


- Determined-fact → HITL teaching proposal (touches Gate 2 / evidence floor — its own PR).
- Incremental frontier (semi-naive with a delta set) instead of recompute-and-dedup per
  tick — an O() optimization once the closure substrate is proven.
- Order/containment transitivity (`less_than`, `before_event`, `inside_of`) — the C-2
  predicate widening; consolidation generalizes to them once C-2 lands.
