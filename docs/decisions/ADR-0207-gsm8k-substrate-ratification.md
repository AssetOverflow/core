# ADR-0207 — GSM8K Comprehension/Composition Substrate: Ratify · Freeze · Execute

**Status:** Accepted (ratified 2026-06-03)
**Date:** 2026-06-03
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Consolidates (does not replace):** ADR-0164, ADR-0165, ADR-0174,
ADR-0178 (Compositional Structure), ADR-0179.
**Supersedes:** ADR-0163 §Phase B–E *prescription* and ADR-0136's regex
sentence-template prescriptions (refusal taxonomies preserved as evidence).

---

## 1. This is not a new design

It is the ratification of a design that already exists and is already built, plus the
closing of the fallback path that keeps re-opening it. It ends a process loop, not an
architectural gap:

> a structured substrate gets proposed → never ratified or finished → the old regex path
> stays live in parallel → someone sees overfitting on the live regex path and proposes a
> "new" structured substrate that already exists → repeat.

**If anyone (human or agent) proposes a "semantic operation grammar compiler," a "new IR,"
or a "new reader" for GSM8K after this ADR: it is redundant with the five ADRs consolidated
here. Redirect to this document.** The next correct artifact on this surface is *execution
against the gates* (§6), not another design.

## 2. Verified findings (origin/main `2cb0922`)

Every claim below was reproduced read-only against the tree on 2026-06-03.

**252 ADRs.** The relevant design is on the books, not missing. Actual status lines (cited as
they stand — these are *not* "design of record" labels until this ADR is ratified):

| ADR | Title (verbatim) | Status (verbatim) |
|---|---|---|
| **0164** | Incremental Comprehension Reader (replaces regex sentence-template parsing) | *Partially implemented (Phase 1 + 2 shipped; eval delta pending lexicon expansion)* |
| **0165** | Regex Scope Rule: Lexemes Only, Never Grammar | *Proposed* |
| **0174** | Held-Hypothesis Comprehension with Lookback and In-Loop Contemplation | *Proposed* |
| **0178** | Compositional Structure: Comprehension-Guided Multi-Step Derivation (Gap B) | *Proposed* |
| **0179** | Extraction Richness | *Proposed* |
| 0136 | Statement Layer Corridor | *Active* — regex sentence-template prescription superseded by 0164 |

- **ADR-0164** explicitly *"replaces regex sentence-template parsing"* and supersedes
  ADR-0163 §Phase B–E + ADR-0136 (+ the .S.1–.S.4 sub-family). Verified verbatim.
- **ADR-0174** *deprecates* the per-category injector dispatch table at
  `generate/recognizer_anchor_inject.py:233` **as the runtime admission path** — *"the
  injectors become hypothesis-emitters within the held-hypothesis reader; they no longer
  route admission via category lookup."* Verified verbatim.

**The machinery is built, not theoretical.** All present and importable at HEAD:
`generate/comprehension/{lifecycle,state,lookback,constraint_propagation,contemplate,composition_registry}.py`
and `generate/derivation/{multistep,compose,accumulate,clauses,extract,pool}.py`.
Held-hypothesis primitives (`lookback.reevaluate`, `contemplate`) are invoked live inside
`generate/math_candidate_graph.py` (ADR-0174 Phase 3 lookback block, ~line 685–743).

**Topology is fragmented into three coexisting pieces:**
1. **The regex recognizer/injector path** (`generate/recognizer_match.py` +
   `generate/recognizer_anchor_inject.py`) — the **live serving admission path**
   (imported by `math_candidate_graph.py` at lines 663, 685, 1004) and the overfitting vector.
2. **The held-hypothesis primitives** — bolted into the candidate-graph flow (above).
3. **The `derivation/` composer** — built and *already enriched* (see §3), but **disjoint
   from serving**: `chat/` imports zero derivation modules, and the serving candidate-graph
   path imports **exactly one** derivation symbol —
   `generate.derivation.product_bridge.resolve_promotable_product`
   (`math_candidate_graph.py:530`, the guarded product bridge behind the current lift). The
   composer proper (`extract`/`clauses`/`compose`/`accumulate`/`multistep`/`search`/`verify`)
   is **not reached from serving**. (`cue_precision/`, `proof_chain/`, and `derivation.model`
   type imports are inert w.r.t. serving.)

The reader-*as-admission-dispatch* was found inert and **retired in Phase 5a** (`3fd3172`,
ancestor of the prior HEAD `8327c6b`, −1,038 LOC); the primitives survived. So ADR-0174's
intended topology (**reader = the brain; injectors = emitters**) **was never realized — it
fragmented.**

**Empirical signature of the unfinished state:** train_sample **6/44/0** (reproduced live);
sealed holdout **0/0/1319** (cited per `docs/claims_ledger.md` / ADR-0119.7 ciphertext — not
CI-reproducible). The live regex path solves a few train surface forms and transfers to
~nothing unseen. Safe failure (refuses, never wrong), but narrow-and-non-transferring.

**Root cause of the wasted weeks is process, not architecture:** five `Proposed`/partial ADRs
never ratified or driven to completion, with the deprecated fallback left live.

## 3. RATIFY — the design of record

Upon ratification of this ADR, adopt the following as the single ratified GSM8K design (and
move ADR-0164/0165/0174/0178/0179 out of `Proposed`/limbo, this ADR serving as the
consolidating decision that cites them):

> **Doctrine (decoding-not-generating).** GSM8K capability comes from a structured
> comprehension reader that builds typed hypotheses and a composer that assembles them into
> multi-step derivations. Regex recognizes **lexemes only** (currency, fractions, numerics) —
> **never** sentence/grammar structure (ADR-0165). The composer's incomplete productions
> **refuse structurally**, preserving `wrong=0`.

ADR-0163 §Phase B–E and ADR-0136's regex sentence-template prescriptions are **superseded**
(their refusal taxonomies are kept as evidence; the regex *prescription* is dead — already
recorded in ADR-0164's "Supersedes in part" block).

## 4. FREEZE — close the fallback

The regex recognizer/injector path on the **serving candidate-graph** (`recognizer_match.py`
+ `recognizer_anchor_inject.py`) is **lexeme-recognition + refusal-only.**

- **Permitted:** refusal-only `wrong=0` guards — the no-reference `<N> times` completeness
  tripwire (composition-capability-scope §9; `tests/test_candidate_graph_completeness_guard.py`)
  is the model: it *removes* wrong answers, it cannot overfit.
- **Forbidden:** any new *positive* capability as a bespoke recognizer/injector branch.
  Positive capability flows only through the comprehension/composition machinery (§5).

This is consistent with ADR-0174's own deprecation (the per-category injector dispatch is no
longer the admission path) and is the line that, left open, re-creates the loop.

## 5. CONVERGE + EXECUTE — feed the built machinery (no new architecture)

The convergence target is ADR-0174's intent: the structured machinery is the brain; regex is
demoted to lexemes + refusal. Realize it by **connecting and feeding what is already built**,
not rewriting it.

> **Extraction is not the open lever (tree-verified, 2026-06-03).** An earlier draft named
> *extraction richness* (ADR-0179) as primary. That is **stale**: EX-1/EX-2/EX-4/EX-5/EX-6
> + unit-hygiene have **landed** in `generate/derivation/extract.py`; only EX-3 (multi-word
> units) is deliberately deferred with documented traps (`TestEX3StillDeferred` pins them),
> and ADR-0179's §Context "thin extractor" table no longer matches the code — e.g. case 0003
> now solves 864 end-to-end through the derivation composer. See
> [extraction-richness-audit-2026-06-03](../analysis/extraction-richness-audit-2026-06-03.md).

Execute these three levers, in order:

1. **WIRING — the crux.** Connect the disjoint `generate/derivation/` reader (where the
   enriched extractor *and* the ADR-0178 composer already live) into the **serving
   candidate-graph path**, so its output counts toward the live metric. The derivation
   machinery is built and enriched but disjoint; until it feeds serving, none of its richness
   moves 6/44/0. `product_bridge` (§2) is the lone existing tendril and the proof the wiring
   pattern works. **This is wiring, not new design**, and it is the central task — not a
   preliminary.
2. **COMPOSITION (ADR-0178) — the actual wall.** Complete the derivation composer's
   multi-step assembly: which quantities group, via which ops, in what order (the R4/R5/R6
   lever). This is the genuine research risk; extraction already feeds it.
3. **LEXICON (ADR-0164) — category/lexicon expansion.** So the serving reader stops emitting
   `ReaderRefusal` on the first unknown token (the "eval delta pending lexicon expansion"
   ADR-0164 itself flagged).

**EX-3 multi-word units = narrow mop-up only**, addressed minimally if at all — e.g.
head-unit list inheritance for the 0024-class, sidestepping the deferred EX-3 traps
(see the audit's P1). **Not a lever.**

Positive capability = **wiring + composer enrichment + shared lexicon** (composable,
generalizing). Never a per-shape branch.

## 6. Acceptance gates (`wrong=0` is the governor)

Every step must hold all of:

1. train_sample stays **`wrong=0`** (6/44/0 or better — `correct` may only rise).
2. The no-reference `<N> times` hazard (composition-capability-scope §9) stays **refused**.
3. No partial graph admits while any source quantity is unbound (the completeness leg).
4. Progress is measured on the composition-typed **validation sub-corpus**
   ([`evals/gsm8k_math/composition_validation/v1/`](../../evals/gsm8k_math/composition_validation/v1/cases.jsonl),
   now **22 cases**) *and* on the **sealed 1,319** — the sealed number is the real bar. A
   train_sample gain that does not move held-out is overfitting in a tidier wrapper and does
   **not** count.
5. Each gain lands as machinery enrichment (§5), audited to confirm it is not a new
   recognizer/injector branch (the §4 freeze).

**Phase 5b is gated on the 22-case composition corpus AND the sealed 1,319 together.**

## 7. What this explicitly is NOT

Not a new grammar compiler. Not a new IR. Not a new reader. Not a new ADR-numbered
architecture beyond this consolidation. It is: ratify the five that exist, freeze the
fallback, feed the built machinery, measure on held-out. Any proposal to build a "new"
structured front-end for GSM8K is this, restated — point it here (§1).

## 8. Why this ends the loop

The loop had three drivers: **propose** (Proposed-limbo), **leave the fallback live** (an
overfitting vector to rediscover), and **re-propose** (perpetual design instead of
finish-to-instrument). This ADR removes all three at once — **ratify** (§3), **freeze** (§4),
**finish-to-instrument** (§5–§6, measured on the sealed set, not on more proposals).

## 9. Documentation-hygiene flags (for the operator, non-blocking)

- **Duplicate ADR-0178 number.** Two files carry `ADR-0178`:
  `ADR-0178-compositional-structure.md` (the Gap-B composer this ADR consolidates) and
  `ADR-0178-GB3b-referent-accumulation-scope.md` (a scope-only sub-phase). They should be
  renumbered/renamed for unambiguous citation.
- **ADR-0179 §Context drift.** Its "thin extractor" table predates the landed
  EX-1/2/4/5/6 + unit-hygiene work; reconcile it to the tree (the audit in §5 is the
  reconciliation) when 0179 is moved out of `Proposed`.

## 10. Cross-references

- **Consolidates:** [ADR-0164](./ADR-0164-incremental-comprehension-reader.md),
  [ADR-0165](./ADR-0165-regex-scope-rule.md),
  [ADR-0174](./ADR-0174-held-hypothesis-comprehension.md),
  [ADR-0178 Compositional Structure](./ADR-0178-compositional-structure.md),
  [ADR-0179](./ADR-0179-extraction-richness.md).
- **Supersedes:** ADR-0163 §Phase B–E prescription, ADR-0136 regex sentence-templates.
- **Instruments:** the 22-case composition validation corpus
  (`evals/gsm8k_math/composition_validation/v1/`) and the sealed holdout
  (`evals/gsm8k_math/holdouts/v1/cases.jsonl.age`, `0/0/1319`).
- **Evidence:** [composition-capability-scope](../analysis/composition-capability-scope.md),
  [extraction-richness-audit-2026-06-03](../analysis/extraction-richness-audit-2026-06-03.md).
- **Thesis:** [[thesis-decoding-not-generating]].
