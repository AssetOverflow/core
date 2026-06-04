<!-- CANONICAL | composition-capability-scope.md | updated 2026-06-03 | execution lane | supersedes prior copies -->

# Composition-Capability Scope — v2 (re-anchored to shipped reality)

Status: Proposed analysis / build-scoping. No serving or eval edits. Source of
truth: `docs/claims_ledger.md`, `evals/gsm8k_math/train_sample/v1/report.json`,
ADR-0174 **read in full (644 lines, incl. Implementation Notes + amended Phase 5,
lines 300–533)**. Every empirical claim below reproduced live against `main` @ `3e29559`.

> **v1 correction.** v1 aimed the plan at "land Phase 1; the unlanded value is
> Phase 3/4." That was wrong — scoped from ADR-0174's forward sections only,
> missing the ~225 lines documenting that **Phases 1–4 already shipped and are
> wired into serving**. Verified on `main`:
> `generate/comprehension/{state,lookback,contemplate,constraint_propagation}.py`
> exist with `HYPOTHESIS_CAP`/`open_hypotheses`/`Hypothesis`/`UnknownHeld`/
> `reevaluate`/`contemplate`, and `reevaluate`+`contemplate` are imported and
> invoked inside `generate/math_candidate_graph.py::parse_and_solve`. Metric still
> **6/44/0**. v2 re-anchors to the ADR's own amended Phase 5.

## 0. The finding that scopes everything (corrected)

The held-hypothesis machinery (ADR-0174 Phases 1–4) is **live in serving and the
metric did not move.** A live `parse_and_solve` audit of all 44 refusals (§1)
locates the wall precisely: **44/44 refuse at `branches_enumerated = 0` — upstream
of the solver, which is never reached.** So the lift is **not** more reader
machinery, and **not** solver operation coverage (the 8 op-kinds are never reached;
see §1). The wall is **emission/representation**: the recognizer/parser/binding
layer cannot construct an admissible multi-step candidate for these shapes, so
nothing is fed to the (already-capable) solver. ADR-0174's "removing the 3–5
narrowness layers per case" is that emission/representation work.

This inverts v1's thesis *and* supersedes the intermediate "operation coverage"
thesis: the composition wall is at **emission/representation upstream of the
solver**, not at the operation layer.

## 1. Verified current state on `main`

| Layer | State |
|---|---|
| Held-hypothesis reader (P1–P4: state, constraint-propagation, lookback, contemplate) | **Shipped, wired into serving** candidate-graph |
| `HYPOTHESIS_CAP`, vault>packs>audit precedence | already set/enforced (0174 OQ#1/#3 moot) |
| `lifecycle.py` GSM8K-scoring dispatch | **retired in Phase 5a** (commit `3fd3172`, ancestor of HEAD `8327c6b`) — was inert (admitted 0/50) |
| `lifecycle.py` / `audit.py` reader surface | **load-bearing** for the ADR-0172 teaching corridor — **keep** |
| Solver operation kinds | **8 already exist** (verified by discovery): `add`, `subtract`, `transfer`, `multiply`, `divide`, `apply_rate`, `compare_additive`, `compare_multiplicative`. Missing arithmetic op kinds is **not** the blocker. |
| **Live audit of all 44 refusals (ran `parse_and_solve` on `main`)** | **44/44 refuse at `branches_enumerated = 0`** — i.e. *upstream of the solver*. No branch is built, so the 8 operation kinds are **never reached**. `rate`/`ratio` also exist as first-class `SEMANTIC_ROLES`/`QUESTION_FORMS` (`binding_graph/model.py:42–65`); only `percent`/`accumulate` lack a named op-kind — moot while nothing reaches the solver. |
| train_sample metric | **6 / 44 / 0** (`correct_min=10` not yet passed) |

## 2. The actual remaining work (ADR-0174 amended Phase 5)

> **Runway status (2026-06-03):** Phase 5a **SHIPPED** in commit `3fd3172`
> (ancestor of HEAD `8327c6b`); the §9 completeness-gate precondition **LANDED**
> in PR #534 (`e1bcdf6`). The live runway now starts at the ≤20-case validation
> sub-corpus (§4 item 2), then **Phase 5b** (emission/representation) — the only
> remaining capability work.

### Phase 5a — retire the inert parallel parser (SHIPPED in `3fd3172`)
**Done.** Commit `3fd3172` (ancestor of HEAD `8327c6b`) retired the
GSM8K-scoring-only inert dispatch (`_try_comprehension_reader` /
`_try_reader_for_question`) + adapter (`lifecycle_runtime_adapter.py`) +
`use_reader` / `comprehension_reader_questions` plumbing. Net **−1,038 LOC**
(code + tests). `lifecycle.py`/`audit.py` were **kept** — their reader *refusals*
feed the ADR-0172 math-contemplation teaching corridor (`teaching/math_*`,
`evals/flywheel_demo`, `core/cli.py`). Single-path serving.
Acceptance **met and re-verified at HEAD:** train_sample 6/44/0 byte-identical
(all 44 refusals at `branches_enumerated=0`), completeness-guard suite green.

### Phase 5b — emission / representation buildout (semantic — the real lift)
"This is where `correct` climbs toward 25. It is not a refactor." **Verified
diagnosis (live `parse_and_solve` audit of all 44, on `main`):** every refusal
occurs at `branches_enumerated = 0` — *upstream of the solver*. The 8 operation
kinds are never reached. So 5b is **not** an operation-execution problem and
**not** chiefly a new-primitive problem. It is an **emission/representation**
problem: the recognizer/parser/binding layer cannot construct an admissible
multi-step candidate for these shapes, so nothing is fed to the (already-capable)
solver.

The 44 split into two emission failure modes (verified, matches `report.json`):
- **32 "recognizer matched but produced no injection"** — an anchor fired but the
  hypothesis-emitter declined to construct a candidate (cannot represent the
  multi-clause / derived / scoped structure).
- **12 "no admissible candidate"** — the parser produced nothing admissible.

**Sequencing implication:** fix emission/representation first; the
`percent`/`accumulate` primitive question is **secondary** — answerable only after
cases actually reach the solver. This *lowers* the wrong=0 risk: emitting existing
ops behind the same admissibility predicates is lower-risk than new solver math.

**5b first PR (smallest verified-tractable slice):** pick the emission failure mode
with the highest count whose representation is bounded — and prove it reaches branch
enumeration on ≥1 case without breaking `wrong=0`. The §9 completeness-gate
precondition **landed in PR #534** (`e1bcdf6`); its driver
(`tests/test_candidate_graph_completeness_guard.py`) is green at HEAD.

## 3. Test anchors (reusable, relabeled to 5a/5b)
1. **Serving gate (`gsm8k_math`):** 5a byte-identical 6/44/0; 5b climbs
   (`correct ≥ 10` clears the ADR-0126 exit, target → 15 → 25), `wrong = 0` at
   every step.
2. **Regression nets (100% `wrong=0`):** G1–G5, S1; `anti_regression`; case-0050 pin.
3. **Determinism:** `trace_hash` over `open_hypotheses`; replay-equivalence.
4. **Serving freeze:** `verify_lane_shas.py` passes each step.
5. **Still-needed new asset (0174 OQ#5):** the curated ≤20-case multi-step
   validation sub-corpus — **unbuilt, still required for 5b measurement.** The §9
   hard negatives are the first deposits into it. Author before 5b measurement.

## 4. Corrected sequencing

> **Status (2026-06-03):** items 0, 1, and 3 are **DONE**. The live runway starts
> at item 2 (the sub-corpus), then item 4 (Phase 5b).

0. **Precondition (§9) — LANDED (PR #534, `e1bcdf6`).** The comparative-multiplicative completeness tripwire now refuses a dropped `<N>×` clause (as `twice` does). The driver `tests/test_candidate_graph_completeness_guard.py` pins the §9 hard-negative matrix (10 no-ref `<N> times` cases + with-ref must-solve + must-still-refuse controls) and is **green** at HEAD `8327c6b`. The "RED on `main`" claim in §9 is the pre-landing measurement.
1. **5b gating analysis — done (§8):** the **emission/representation** audit ran and the 32 no-injection cases are sub-classified by representation. Highest-count bounded gap = **R1 derived/intermediate symbol (24/44)**.
2. **Author the ≤20-case multi-step validation sub-corpus** (test anchor for 5b) — **next open step.**
3. **Phase 5a — SHIPPED (`3fd3172`, ancestor of HEAD `8327c6b`):** the inert scoring-path dispatch was retired (−1,038 LOC); `lifecycle.py`/`audit.py` kept for the ADR-0172 corridor.
4. **Phase 5b** — build the **emitter/representation** for R1 (derived-symbol) on the §8 near-pure exemplars (prove ≥1 case reaches `branches_enumerated > 0` and admits), each behind §3 gates **and the §9 precondition**. Not new operations — the 8 exist and are unreached.

(Do **not** "land Phase 1" — shipped. Do **not** treat P3/P4 as the lever — shipped, metric flat. Do **not** re-do Phase 5a — shipped in `3fd3172`.)

## 5. Relation to cross-subject testing
5b maturing the math `DomainSolver`'s emission/representation is still the precondition
for wiring symbolic_logic as arena #2; the held-hypothesis reader + disagreement
gate remain the shared, arena-portable primitives. `cross_domain_transfer` /
`monotonic_learning` (both exist, with `contract.md`/`holdouts/`) become live tests
once arena #2 exists.

## 6. Honest ceiling (corrected)
The ≥15 climb is a **5b** outcome (emission/representation), **not** a P4 outcome — P4
shipped and we are at 6. Cases needing world knowledge (0040 legs) or representations 5b
does not add stay refused = `wrong = 0` holding, not failure.

## 7. Open questions for the build lane
1. **Answered by the live audit:** the binding constraint is emission upstream of
   the solver (44/44 at `branches_enumerated=0`), not operation execution. Remaining:
   rank the §8 R-classes by the size of the bounded-representation slice per class.
2. Of the 44, which are emission-fixable with existing ops vs (a) genuinely need a
   `percent`/`accumulate` primitive *after* emission, vs (b) world-knowledge/out-of-
   scope permanent refusals (e.g. 0040 legs-per-animal). The audit gives the upstream
   verdict; this split needs per-case reader-trace reads.
3. 5a pre-flight: confirm the exact inert-dispatch LOC and that no teaching-corridor
   consumer breaks when the GSM8K-scoring dispatch is retired.

---

## 8. Verified per-case representation classification (live audit, all 44)
Structural reading of each of the 44 (what representation the emitter must build for
emission to succeed), grounded in the case text + the live `parse_and_solve` locus.
Multi-tagged; a case usually needs several. Frequency across the 44:

| Representation gap | # cases (multi-tagged) |
|---|---:|
| R5 — multi-step rate/duration/scalar | 27 |
| R1 — derived/intermediate symbol | 24 |
| R6 — percent/fraction mutation (no op-kind) | 18 |
| R4 — accumulation/residual | 10 |
| R2 — inverse target | 6 |
| R3 — subset/partition scope | 3 |
| R7 — world-knowledge (permanent refusal) | 1 |

**Highest-leverage gap: R1 (derived/intermediate symbol)** — 24/44 need to compute an
intermediate quantity and reuse it downstream. Its lowest-arity exemplars are nearly
pure R1: 0027 (Twitter = half of IG+FB), 0008 (total beads → ÷ per bracelet),
0029 (keyboard = 3× mouse → sum), 0038 (×3 → sum). Contrastive proof it is the emission
gap (parseable aggregate question form): `"Nicole has 400 cards. Cindy has 800 cards.
How many cards do they have together?"` **admits (1200)**; `"…Cindy has twice as many
cards. How many cards do they have together?"` reaches `branches_enumerated=1` but
**refuses** (completeness: scalar `2.0` unconsumed). The stated-sum reaches the solver;
the derived form does not. R7 (0040 legs-per-animal) is a permanent refusal — world
knowledge.

**First 5b slice (recommended):** derived/intermediate-symbol emission, validated on the
four near-pure exemplars above — move them from refused to admitted, `wrong=0` preserved.
**But see §9 first — it is a hard precondition.**

## 9. ⚠ Latent `wrong=0` hazard surfaced by the live audit (gate gap)

> **Status (2026-06-03):** the guard recommended below **LANDED in PR #534**
> (`e1bcdf6`). Its hard-negative matrix lives in
> `tests/test_candidate_graph_completeness_guard.py` (10 no-ref `<N> times` cases
> + with-ref must-solve + must-still-refuse controls) and is **green** at HEAD
> `8327c6b` (21 passed). The "RED on `main`" statements below are the point-in-time
> pre-landing measurement, kept for provenance.

Contrastive probes (not in the 50-case sample) surface a reproducible **admitted-wrong**
path. **Use the parseable aggregate question form `"...do they have together?"`** — the
short form `"How many apples together?"` refuses upstream at question-parse
(`branches_enumerated=0`) and does NOT exercise this `be=1` completeness gap.

```
"Tom has 7 apples. Jerry has 3 times as many apples. How many apples do they have together?"
  → admitted=True, answer=7, branches_enumerated=1   (correct = 28)   # base returned, clause dropped
"...Jerry has five times as many apples. ..."  → admitted, answer=7   (correct = 42)
"...Jerry has twice as many apples. ..."        → refused, be=1 (completeness: scalar 2.0 unconsumed)  # safe
```

**Broadened surface (all verified RED on `main`).** The hazard is the **no-reference**
comparative-multiplier surface across all four connectives and both cardinal forms:

```
<N> times as many <unit>
<N> times more <unit>
<N> times the number of <unit>
<N> times the <unit>
```
…for `<N>` ∈ {digit 2/3/5/…, word two/three/five/…, N≥2}. Every one admits the base.
`twice` / `double` / `double the` (no digit/cardinal) refuse safely.

**Root cause (verified by reading the emitted `MathProblemGraph`).** The admitted graph
contains a spurious initial:
`InitialPossession(entity='Jerry', quantity=Quantity(value=3, unit='times'))`.

1. `quantity_values_in_text` is **symmetric** (registers 2.0 for `twice` *and* 3.0 for
   `3 times`) — **not** a quantity-extraction asymmetry (this overturns an earlier guess).
2. For the no-ref surface, **neither** serving comparative regex fires
   (`_COMPARE_MULT_ANCHOR_RE` / `_COMPARE_MULT_NTIMES_RE` both require an "as `<REF>`"
   tail the probe lacks). `comparatives.py::_N_TIMES_RE` is the **disjoint** `derivation/`
   reader — off the serving path — so it is *not* the locus either.
3. Instead `recognizer_match.py::_match_discrete_count_statement` (open regex
   `_extract_discrete_count_re_open`) captures the multiplier cardinal as a **count**, and
   `recognizer_anchor_inject.py::_build_initial_from_discrete_count` builds
   `CandidateInitial(value=N, unit='times', entity=<actor>)` — note the unit is the literal
   `'times'` token, **not** the counted unit.
4. That bogus initial **consumes** the scalar N, so completeness sees
   `uncovered = {N, base} − {N, base} = ∅` → admits. The answer sums only the counted unit
   (`apples`) and returns the base. `twice`/`double` carry no cardinal the discrete-count
   regex grabs → no spurious initial → scalar unconsumed → existing guard refuses.

**Recommended guard shape (refusal-only, `wrong=0` preserving).** Make the discrete-count
recognizer **decline** when its cardinal sits in a
`<N> times {as many | more | the number of | the} <unit>` comparative-multiplier context
— equivalently, refuse to build a discrete-count initial whose unit is the literal
`'times'`. The no-ref form then refuses (like no-ref `twice`) until real no-ref
comparative-multiplicative *emission* lands in 5b. The fix MUST NOT regress the controls
below.

**Controls (verified on `main`).**
- **With-ref `<N> times` already solves — must stay green.** train_sample **case 0024**:
  *"Sidney does 20 jumping jacks on Monday, 36 on Tuesday, 40 on Wednesday, and 50 on
  Thursday. Brooke does three times as many jumping jacks as Sidney. How many jumping
  jacks did Brooke do?"* → **438** (committed verdict: correct). Also `dice 3×` → 80.
- **Existing safe refusals — must stay refused.** no-ref `twice`, no-ref `double the`,
  with-ref `twice` (Ivan/Jerry dice).

**Driver test (FINAL, RED on `main`).** `test_completeness_guard_ntimes_noref_hazard.py`
— **10 no-ref hazard cases** (the broadened surface × digit/word) that MUST refuse, plus
**2 with-ref must-solve controls** (0024 → 438, dice → 80) and **3 must-still-refuse
controls**. Verified live: **10 failed, 5 passed** on `main` (hazard RED, controls green).
This is the first concrete 5b PR, ahead of any R1 emission work.

**Scope — stated precisely.** This is a **latent gate gap, not a live-metric violation.**
The two layers are distinct: the §1 wall is at `branches_enumerated=0`
(emission/question-parse); this hazard lives at `branches_enumerated=1` (the completeness
gate). The real 44 all refuse at `be=0` — upstream of `be=1` — so none reach this gap
today; that is *why* it is latent. train_sample 6/44/0 is reproduced live. The full-test
`0/0/1319` is **not** re-verified here — it is a sealed, recorded measurement per
`docs/claims_ledger.md` row A / `ADR-0119.7` (ciphertext
`evals/gsm8k_math/holdouts/v1/cases.jsonl.age`), not a CI-reproducible artifact; cited,
not re-verified (the citation and ciphertext both exist on `main`).

**Why it gates 5b.** Phase 5b's explicit goal is to make comparative-multiplicative cases
*reach the graph*. If emission improves while this completeness gap remains, 5b would
**convert latent into live** — admitting wrong answers on exactly the `<N> times` shape it
is trying to solve. Therefore: **hardening the comparative-multiplicative completeness
tripwire (so a dropped `<N>×` clause refuses, as `twice` does) is a hard precondition for
any 5b emission PR.** The §9 driver test is the ready-made hard negative for the ADR-0174
OQ#5 validation sub-corpus.
