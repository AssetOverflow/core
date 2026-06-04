<!-- analysis | wiring-promotion-gate-brief | 2026-06-03 | read-only, no code | ADR-0207 §5 step 1 execution brief -->

# WIRING + Promotion-Gate Brief — feeding the derivation composer into serving

**Status:** Analysis only. No serving, eval, or code edits. Every claim reproduced
read-only against `origin/main` @ `2cb0922` (corpus + branch state per PR
[core#536](https://github.com/AssetOverflow/core/pull/536)).

**Scope.** ADR-0207 §5 step 1 (WIRING) is the named next lever: connect the disjoint
`generate/derivation/` composer to the serving candidate-graph so its output counts
toward 6/44/0. This brief reads the actual integration surface — `product_bridge.py`,
`pool.py`, `verify.py`, `target.py`, the `math_candidate_graph.py:530` boundary — and
defines what the wiring *and its promotion gate* must be. It also reports an empirical
finding that **partly corrects ADR-0207 §5's sequencing claim**; see §5.

---

## 1. Bottom line

"The wiring is trivial, the gate is the work" is correct — but incomplete, and the
honest version is sharper:

1. **The general composition entry already exists** — it is `resolve_pooled(text)`, not a
   thing to build. (The brief's earlier "there is no `resolve_composition`" was wrong.)
2. **The general self-verify gate already exists and is composition-agnostic**
   (`select_self_verified`: grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness).
3. **`product_bridge` is already the promotion gate for one shape (pure products) and is
   already wired** at `math_candidate_graph.py:530`. The wiring lever, for what the
   composer can safely certify *today*, is **already done**.
4. **The composer refuses every R1/R4/R5/R6 target in the validation corpus** (§3). So
   wiring `resolve_pooled` yields **zero lift** on the target shapes — there is nothing
   correct yet to promote.
5. **Wiring `resolve_pooled` *wholesale* is a live `wrong=0` regression** — it commits
   `0016 → 510` (gold 2) (§3). The promotion gate is mandatory from the first wire.

**Therefore:** WIRING and COMPOSITION (§5 steps 1–2) are **not separable**, and WIRING is
**not the lowest-risk first step** as ADR-0207 §5 states. The safe wire already exists
(`product_bridge`); extending it to a new shape requires the composer to *build that
shape's chain* (it currently refuses) **and** a promotion gate to *certify it*, in
lockstep. The gate and the composition capability are the same problem (§6).

## 2. The verified integration surface

| Component | What it is | Serving-wired? |
|---|---|---|
| `math_candidate_graph.py:524–540` | The ADR-0195 boundary: `r = resolve_promotable_product(text); if r is not None: return CandidateGraphResult(answer=r.answer, branches_enumerated=1, branches_admissible=1)` | **yes** (the one tendril) |
| `derivation.pool.resolve_pooled(text) → Resolution \| None` | General composition resolver: pools accumulation + multiplicative + chain candidates, classifies each `complete`/`exempt`/`None`, refuses on disagreement or exempt-only, guards `asks_prior_state` | no (sealed) |
| `derivation.verify.select_self_verified(derivs, text, target_units=…)` | Composition-agnostic gate: grounding ∧ cue ∧ unit ∧ completeness, then uniqueness/disagreement; `target_units` drops chains answering the wrong dimension | no (sealed) |
| `derivation.verify.classify_derivation` | ADR-0182 commit-eligibility: `complete` (resolves) / `exempt` (pool-only, forces disagreement) / `None` (fails a clause) | no |
| `derivation.target.extract_target(question, known_units) → Target` | Question-target extraction (a general analogue of product_bridge's hardcoded target check) | no |
| `product_bridge.resolve_promotable_product` | The promotion gate for **one shape** (pure products) — see §4 | **yes** |

**Wiring shape (mechanically trivial, confirmed).** A second block at the same `:530`
boundary: `c = resolve_promotable_composition(text); if c is not None: return
CandidateGraphResult(answer=c.answer, branches_enumerated=1, branches_admissible=1)`.
The work is entirely inside `resolve_promotable_composition` — the gate.

## 3. The empirical crux (live `resolve_pooled`, all corpus positives)

Ran `resolve_pooled` on the validation corpus's composition positives + diagnostics:

| Cases | Composition | `resolve_pooled` result |
|---|---|---|
| 0029, 0038, 0008, 0027 | R1 | **refuse** (×4) |
| 0037, 0035 | R4 | **refuse** (×2) |
| 0030, 0015 | R5 | **refuse** (×2) |
| 0005, 0046 | R6 | **refuse** (×2) |
| 0033 | downstream | refuse |
| 0024 | extraction (EX-3) | refuse |
| 0040 | world-knowledge | refuse |
| **0016** | hazard-both | **COMMIT 510 — WRONG (gold 2)** |

Two facts fall out, both load-bearing:

- **Zero lift from wiring.** The pool commits *nothing correct* on the 10 R1/R4/R5/R6
  positives — it refuses all of them. The composers cannot yet assemble a committable
  complete-unique chain for these shapes. Wiring the pool moves 6/44/0 by **+0 correct**.
- **A live wrong commit.** `0016` is a unique complete self-verifying reading that is
  *wrong* (the chain `… → 510`, no rival to trigger the disagreement rule). This is
  exactly the "known wrong commits" `product_bridge`'s docstring warns of. Wiring the pool
  *ungated* makes serving **6/43/1** — a `wrong=0` violation. `product_bridge`'s
  `_has_hazard_surface` blocks `0016` today via its `{less, more, per, …}` cues.

## 4. What `product_bridge` actually proves (the gate to generalize)

`resolve_promotable_product` is a **four-layer** promotion gate over `resolve_pooled`:

1. `_has_hazard_surface` — a refuse-preferring **blocklist**: comma-thousands, `%`/percent,
   text blockers `{left, more, less, gave, spent, profit, remaining, …}`, question
   blockers `{per, after, before, remaining, profit, …}`. (This is what stops `0016`.)
2. `resolve_pooled` — the pooled candidate + disagreement rule.
3. `_is_complete_pure_product` — every step `multiply`, non-comparative, `classify == "complete"`.
4. `_has_product_target` — a **near-whitelist of two target shapes**: `money … make/earn`,
   or `weight … total/move` with a mass unit.

**The tell:** layer 4 is almost hardcoded to 0003 (revenue) and 0021 (weight). Its safety
comes from its narrowness — it admits essentially two target forms. **This does not
generalize.** A composition gate for R4/R5/R6 cannot copy a two-entry target whitelist; it
needs a *general* op-class/target proof (the natural tool is `extract_target` +
`select_self_verified(target_units=…)`), and that proof is the hard part.

## 5. Correction to ADR-0207 §5 (flagged, not buried)

ADR-0207 §5 step 1 calls WIRING "the crux … the lowest-risk of the execution steps … it's
wiring, with `product_bridge` already proving the pattern … the central task, not a
preliminary." The verified surface refines this:

- **The safe wire is already done** (`product_bridge` at :530). What remains to wire is, by
  shape, gated on composition capability that **does not exist yet** (the pool refuses every
  R4/R5/R6 target).
- **WIRING is not lower-risk than COMPOSITION** — they are the same step. The risk lives in
  the promotion gate, which is where "which composed readings are safe to promote" = "which
  readings the composer got right" = the §5 step-2 composition wall.
- **The ungated pool is `wrong=0`-negative** (0016), so "just wire it in" is not a safe
  preliminary.

**This does not unwind the ratification.** ADR-0207's core — freeze the regex serving path,
design-of-record, the `wrong=0` gates, measure on the sealed set — all stand. The
correction is to §5's *sequencing optimism*. Recommended: amend §5 step 1 to "extend the
`product_bridge` promotion-gate pattern to one new composition shape, in lockstep with the
composer capability for it; never wire the pool ungated," or carry this brief as the §5
execution refinement. Operator's call which.

## 6. The promotion-gate contract (what to build, no code)

`resolve_promotable_composition(text) → Resolution | None`, mirroring `product_bridge` but
**per chosen shape**, must prove all of:

1. **Candidate source.** Obtain the shape's candidate (via `resolve_pooled`, or a
   shape-scoped composer call) — only if the composer actually *builds* it (today: none of
   R4/R5/R6, so this gate is empty until composition lands).
2. **General self-verify** (reuse, don't reinvent): `select_self_verified` —
   grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness.
3. **Target proof** (generalize layer 4): the question's target op-class matches the
   chain's, via `extract_target` + `target_units` — not a per-shape whitelist.
4. **Hazard firewall** (generalize layer 1): the residual `wrong=0` hazards that survive
   self-verify (the `0016`-class: a unique complete reading that is still wrong) must be
   refused. The `0016 → 510` commit is the **mandatory first firewall test** — the gate is
   not done until `resolve_promotable_composition` refuses it.

**`wrong=0` boundary contract:** every corpus case + every sealed case either **refuses or
returns exactly gold**. Proven on the 22-case `composition_validation/v1` corpus (the
instrument) **and** the sealed 1,319 (the real bar, ADR-0207 §6). A train_sample/corpus
gain that does not move the sealed set is overfitting and does not count.

## 7. Recommended first slice + open questions

- **First slice:** pick the *one* shape whose composer is closest to building a correct
  committable chain (candidate: R4 accumulation/residual — `accumulation_candidates` already
  exists and `compose_accumulation` is wired into the pool). Confirm whether the composer
  can build `0037`/`0035` at all (today: pool refuses both — so step 0 is *composer* work,
  not gate work). Only once a correct chain exists does the gate become the lever.
- **Open Q1:** *why* does the pool refuse the R4/R5/R6 positives — is it a missing composer
  production (no chain built) or a gate over-refusal (chain built but fails completeness/
  uniqueness)? This split decides whether step 1 is composer or gate work, and it needs a
  per-case `pooled_candidates` + `classify_derivation` trace read (the next brief).
- **Open Q2:** can `extract_target` express the R4/R5/R6 target op-classes (residual,
  duration-sum, percent-of) precisely enough to replace product_bridge's whitelist without
  admitting a `0016`-class wrong? This is the generalization risk.
- **Open Q3:** does any composer *currently* produce a unique-complete wrong on a sealed
  case (not just 0016)? The hazard firewall must be characterized on the sealed set, not
  only the corpus, before any pool output is wired.

**Invariants observed by this brief:** read-only; `train_sample` 6/44/0 reproduced live;
no serving code touched; the no-ref `<N> times` hazard and 0016 remain refused on the
serving path (product_bridge blocks 0016).
