# ADR-0175 — Calibrated Attempt-and-Eliminate Learning: Two Regimes Under wrong=0

**Status:** Proposed
**Date:** 2026-05-28
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Discussion / derivation:** [SESSION-2026-05-28 — From "Another Matcher" to a Self-Calibrating Problem Solver](../sessions/SESSION-2026-05-28-risk-reward-learning-architecture.md)
**Builds on:** [ADR-0174 — Held-Hypothesis Comprehension](./ADR-0174-held-hypothesis-comprehension.md) (the `eliminate_violating` / `reevaluate` / `contemplate` substrate — here **generalized** from reading to solving; see §"Pre-implementation audit" — it is reading-coupled today, not a drop-in), capability axes G1–G5, the round-trip filter + multi-branch disagreement rule, teaching-safety (proposal-only / reviewed = the seal). The per-class reliability ledger is **new** (the existing `calibration/` module is a grid-search param tuner, not a ledger).
**Supersedes:** the matcher-oriented Phase 5b sub-phases (5b.1 single-sentence / 5b.2 cross-sentence / 5b.3 deep) in ADR-0174 — they collapse into *instances* of this architecture.

---

## Context — why per-shape matching cannot compound, and the contradiction underneath

ADR-0163/0164/0174 moved the engine from `0/50/0` to `3/47/0` on GSM8K
train_sample by building, one at a time, recognizers and injectors for specific
sentence shapes. Each addition lifts `correct` by 0–2 cases. The 2026-05-28
measurement (GSM8K's own `<<a*b=c>>` calculator annotations over the 47 refused
cases) explains why this is structural, not incidental:

- **37/47 (79%)** of refused cases need multiplication; **43/47** need mul-or-div;
  **0/47** are single-step (median 3 steps).
- The *single-sentence* multiplicative aggregate — the supposed "simplest" target
  — is exactly **one idiosyncratic case** (0021); the regular in-clause shape
  already works.

So the needed *operations* are few and general (the solver already supports
`{add, subtract, transfer, multiply, divide, apply_rate, compare_additive,
compare_multiplicative}` with pack lemmas), but the *phrasings* are unbounded. A
matcher per phrasing buys a handful of cases and the curve flattens. **This is
overfitting by construction** — the library-of-founds trap the thesis forbids
([[thesis-decoding-not-generating]]).

The deeper problem surfaced once we asked "let the solver *attempt* instead": a
solver that **refuses whenever uncertain is safe but frozen** — it can only ever
learn what a human hands it. Autonomous learning *requires* attempting through
uncertainty, which is exactly where being wrong lives. **You cannot have
autonomous learning and a global "never be wrong" at the same time.** The current
design applies `wrong=0` even to gold-labeled *practice* data — i.e. it is built
to give up on the very corpus meant to teach it.

The full derivation (problem → dead-ends → pivots → solution) is in the
[session doc](../sessions/SESSION-2026-05-28-risk-reward-learning-architecture.md).
This ADR records the decision.

## Decision

Relocate the engine's intelligence from front-end pattern-matching into a
**problem solver that attempts a grounded derivation and learns by elimination**,
and govern *when it may attempt vs. must refuse* with a **deterministic,
per-context risk/reward gate grounded in earned calibration** — while preserving
`wrong=0` on everything served, by construction.

### 1. Two regimes (the "mode")

- **Serving** — anything the engine commits to a consumer who will act on it
  (chat runtime, held-out/generalization measurement). Cost of error ≈ ∞.
  **`wrong=0`, absolute, unchanged.** Refuse unless certain. This ADR does not
  weaken the field/answer-integrity invariant in any way.
- **Practice** — attempting on material where being wrong is **checkable and not
  served**. Here **wrong is the elimination signal**, not a failure. This is the
  only place autonomous learning occurs.

### 2. The proof-carrying seal (why wrong=0 survives a hot practice loop)

Practice never writes to serving. It emits **proposals that carry their own
proof** (round-trips, forced-unique, introduces zero wrong, replay-stable);
nothing crosses into the serving path except through the existing **proposal-only,
reviewed** teaching gate. Practice may be as bold as its calibration allows
*because* the seal makes its mistakes structurally unable to become a served
answer. This reuses, and must not bypass, teaching-safety.

### 3. The attempt/refuse gate — a deterministic ratio (NOT reinforcement learning)

Per attempt, the action is licensed iff measured reliability meets the human-set
ceiling for that action's blast-radius:

```
license(action, C) :=  reliability_of_relevant_checker(C) / θ_required(action, C)  ≥ 1
```

- The two-regime structure **collapses the reward side**: in serving only
  reliability matters (learning value is irrelevant to a served answer); in sealed
  practice the threshold is "is it checkable?" (`θ_practice = 0`). We therefore
  never have to assign units to "value" or "learning" — **the only thing
  quantified is reliability vs. ceiling.**
- `θ` are **human-set, version-controlled constants** per class and blast-radius
  (`θ_practice = 0`; `θ_propose`; `θ_serve` strict, e.g. `.99`). Raising autonomy =
  a human lowering `θ_serve(C)` for a class the ledger has earned. **The engine
  never sets or raises its own ceiling.**

### 4. The per-class calibration ledger (counts, not learned weights)

Per **class** (= capability axis G1–G5), a **replayable ledger of counts** —
nothing learned, nothing stochastic, every figure a tally over deterministic
attempts or an explicit human constant:

- `n(C), correct(C), wrong(C), refused(C)` — already produced by the eval harness.
- `t2_verified(C), t2_agrees_gold(C)` — on the live gold anchor set.
- `reliability(C) = conservative_floor(correct(C), k(C))` where
  `k(C) = correct(C) + wrong(C)` is the **committed** attempt count — a
  deterministic lower bound on *precision when the engine commits*. **Refusals
  are excluded from the denominator on purpose**: refusing is always safe, so a
  high refusal rate is a *coverage* fact (tracked by `refused(C)`), never a
  *reliability* penalty. Using total `n` would wrongly tie trust to coverage.
- `t2_precision(C) = conservative_floor(t2_agrees_gold(C), t2_verified(C))` — how
  trustworthy self-verification is on `C`; the number that licenses widening past
  gold.

This ledger is **new** (it is *not* the existing `calibration/` module, which is a
deterministic grid-search hyperparameter tuner — orthogonal, no reuse).
`conservative_floor` is the pinned fixed-arithmetic function in §4a.

### 4a. The `conservative_floor` function (pinned)

`conservative_floor(s, k)` returns a deterministic lower bound on the success
proportion given `s` successes in `k` committed trials. Pinned as the **one-sided
Wilson lower bound** with a hard evidence floor:

```text
constants (system-wide, pinned):
  z      = 2.576     # ~99% one-sided pessimism; the single global caution knob
  N_min  = 10        # minimum committed trials before any reliability is claimed

conservative_floor(s, k):
  if k < N_min:                      return 0.0      # insufficient evidence
  p   = s / k
  z2  = z * z
  denom  = 1 + z2 / k
  center = (p + z2 / (2*k)) / denom
  margin = (z / denom) * sqrt( p*(1 - p)/k + z2 / (4*k*k) )
  return max(0.0, center - margin)
```

**Why this shape.**
- *Pessimistic at small k, converges as k grows.* With a perfect record (`s = k`)
  the bound is `k / (k + z²)`, so reliability is *earned by volume*, not granted by
  a lucky streak. The `z²/(2k)` and `z²/(4k²)` terms pull a thin sample toward
  ignorance.
- *Asymmetric by construction.* It is a **lower** bound — the engine acts on the
  pessimistic estimate of its own reliability, so the FP≫FN asymmetry is encoded in
  the estimator itself, not bolted on.
- *Two independent dials.* `z` (pinned) = how skeptical the *estimator* is, global.
  `θ_required` (human-set, per class) = how much reliability an *action* demands.
  Raising autonomy moves `θ`; it never touches `z` and the engine touches neither.

**Boundary behavior (pin these in tests).**
- `k = 0` or `k < N_min` → `0.0` (no claim from trivial evidence).
- range is `[0.0, 1.0)`; it never returns exactly `1.0` (no finite record proves
  perfection — the floor is forever shy of certainty).

**What it costs to clear a ceiling** (perfect record, `z = 2.576`, `z² ≈ 6.64`):

| `θ_required` | committed clean trials to clear |
|---|---|
| 0.85 (e.g. `θ_propose`) | ~38 |
| 0.90 | ~60 |
| 0.95 | ~127 |
| 0.99 (e.g. `θ_serve`) | ~657 |

A single wrong commitment in 40 drops reliability from ~0.86 to ~0.82 — back below
a 0.85 propose gate until more clean commitments accumulate. That is the asymmetry
working: errors cost more standing than successes buy, and standing is re-earned by
volume. Auto-serving a class is deliberately expensive (hundreds of clean
commitments); the ratification corridor is the path to serving *before* that bar is
met.

**Determinism contract.** `conservative_floor` is computed in IEEE-754 float64 and
the result **rounded half-to-even to 1e-9** before any gate comparison; `θ`
constants are specified to the same precision. This makes
`reliability / θ_required ≥ 1` byte-stable and replayable across backends (no
platform-dependent `sqrt` divergence reaches the verdict). A replay test must fail
on any run-to-run difference (invariant #3).

**Residual: precision can be gamed by easy instances.** A class that commits only
to trivial instances and refuses the hard ones shows high precision with thin
coverage. Defense is *not* in this function: per-class axis granularity, the live
gold tether, and human-set ceilings already bound it, and a human MAY add an
optional per-class **coverage floor** (`(correct+wrong)/n ≥ c_min`) as a *separate*
serving precondition. The floor function stays precision-only and clean.

### 5. The checkability ladder — privilege ∝ reversibility

Checkability is not a line but a confidence-stratified ladder. **Governing rule:
require check-strength proportional to the reversibility/blast-radius of the action
it licenses**, because a false positive in the checker (a wrongly-"verified"
belief) is a *persistent contaminant* and is far worse than a missed learning
opportunity.

| Tier | Checker | May change |
|---|---|---|
| **1 — External truth** | gold label / known answer | serving-bound knowledge (via ratification) — *anchors* |
| **2 — Convergent self-verification** | round-trip **∧** ≥2 *structurally-distinct* derivations agree **∧** unit/dimensional consistency **∧** no contradiction with vault/packs (conjunctive) | provisional, **retractable** knowledge (still ratified before serving) |
| **3 — Consistency-only** | merely no contradiction with the known | **practice-internal pruning only** — never crosses the seal |

**Tier 2 is the operating median**: the widest checkability still strong enough to
*create* knowledge, needing no human and no label, so the practice arena scales
toward open-world. Tier 3 keeps the arena wide (attempt anything; learn search
shape) while being reversible and sealed.

### 6. Provenance + retractability

Every learned belief stores `(tier, n_at_admission)`. Retraction is deterministic:
a Tier-1 (or stronger Tier-2) contradiction → retract, and decrement
`t2_agrees_gold` → `t2_precision` falls → the `θ`-gate tightens. Provenance is what
makes widening past gold *safe* — weak beliefs are quarantined by confidence and
reversible. Extends CORE's existing provenance / exact-recall discipline to beliefs.

### 7. Gold tether — defense against correlated self-delusion

Tier-2 agreement only helps if derivations are **independent**; a shared wrong
premise (the engine misunderstands "twice") makes them all agree *and* round-trip
while all being wrong. Defenses:
- **Independence is counted, not assumed**: Tier-2 requires **≥2 structurally
  distinct paths** (different operation multiset or different intermediate
  quantities).
- **A live Tier-1 anchor set always runs**, measuring `t2_precision(C)` per class.
  When it drifts below a floor, appetite contracts. Gold doesn't just teach — it
  *audits whether self-verification is trustworthy*, which is the calibration loop
  closing.

### 8. Diagnostic refusal — the router between skill and knowledge

Every refusal must **name the missing piece**, so effort routes to the right axis:
- *"quantities extracted, units consistent, no grounded derivation reaches target"*
  → **skill** gap → solver search / elimination practice.
- *"unknown relation / unit relationship"* → **knowledge** gap → acquire a
  world-fact.
- *"two grounded derivations disagree"* → **genuine ambiguity** → stay refused.

Quantified: if `reliability(C)` still climbs with practice → skill gap (keep
practicing); if it has stalled → knowledge gap (needs a new world-fact). Extends
typed refusals + the OOV gradient + the math-reader-refusal audit corridor.

### 9. Three compounding stores

Each diagnosis routes to where learning accumulates: **experience → vault** (exact,
deterministic recall), **world-knowledge → ratified packs**, **skill → the
solver's elimination-learned pruning**. The flywheel: stronger solver → more vault
experience + sharper pruning → fewer knowledge gaps to ask about → less
contemplation per problem → fewer hand-authored packs → compounds.

### 10. Self-proving acquisition and the narrowing of human input

Autonomy does **not** mean "no human input" — the engine cannot conjure world-facts
from nothing; facts enter from an ingested data/experience stream. The human role
*shifts* from hand-authoring meaning to **curating what it ingests + ratifying
what it has already self-proven**. The bridge is **self-proving acquisition**: new
knowledge is proposed *with a mechanical proof attached* — the schema-proof-
obligation discipline (CLAUDE.md) pointed at learning. The ratification gate never
opens to ungrounded learning; it simply has less to do as the engine's proofs get
stronger.

### 11. "Creative," defined for a deterministic engine

Not stochastic invention. **A willingness to leap a gap in known structure** — a
recombination no stored pattern directly licenses — always a step from given
ground, never from the void. The checkability tier is the leap dial: a Tier-3 leap
stays a hypothesis; a Tier-2 leap becomes provisional knowledge; a Tier-1-confirmed
leap becomes an anchor.

## Non-negotiable invariants (must be *proven*, not asserted)

Per CLAUDE.md §Schema-Defined Proof Obligations, each of these requires a test that
**fails** under the violation it names:

1. **wrong=0 on serving is untouched.** A test must fail if any practice-regime
   artifact reaches a served answer without crossing the ratification gate.
2. **The search cannot bank a spurious answer.** A test must fail if a derivation
   that is *not* grounded+unique+round-tripping is admitted as knowledge (the
   `20/5` coincidence class).
3. **Determinism / replay.** All ledger counts, the `conservative_floor`, the gate,
   and the search are deterministic and replayable; a test must fail on any
   run-to-run divergence. **No learned weights, no stochastic sampling, no
   approximate recall** — the vault stays exact.
4. **No self-authorization.** A test must fail if the engine mutates any `θ`
   ceiling. Ceilings are human-set config only.
5. **Retractability.** A test must fail if a Tier-1 contradiction does not retract
   the contradicted Tier-2 belief and tighten the gate.

## Consequences

- **What it collapses:** the per-shape matcher backlog. Multiplicative/comparative/
  fraction cases become the **first practice arena** where attempt-and-eliminate is
  proven, not a set of shapes to hand-match. ADR-0174's 5b sub-phases are
  superseded.
- **The train_sample double-duty is resolved.** It currently serves as *both*
  practice arena and serving-regression canary. Decouple: practice may attempt all
  47 (scored correct/wrong/refused, wrongs feed elimination) while `wrong=0` stays
  absolute on the serving contract + held-out generalization, and the hazard
  canaries (0050) keep guarding serving.
- **Risk concentrates in the search + checker.** This is where the project's
  correctness mandate is most stressed; invariants #1–#2 are the load-bearing work.
- **Part composition, part new (see Pre-implementation audit):** classes =
  capability axes; counts = eval harness; replay = existing determinism; `θ` = a
  small config table; seal = teaching-safety. **New or generalized:** the
  reliability **ledger + `conservative_floor`** (new; not the `calibration/` tuner);
  the elimination substrate (`eliminate_violating`/`reevaluate`/`contemplate`)
  **generalized** off its reading-coupled types; a **solver-practice evidence type**
  for the corridor (today's `MathReaderRefusalEvidence` is reader-refusal-shaped).

## Phasing (wrong=0-first; each phase ships its proof obligations)

1. **Ledger + gate substrate.** Per-class calibration ledger, `conservative_floor`,
   the ratio gate, `θ` config table. Invariants #3–#4 proven. Zero behavior change
   to serving.
2. **Sealed practice regime on GSM8K train — as a NEW lane.** Run
   attempt-and-eliminate over the 47 (Tier-1 gold checkable) in a *separate* runner;
   **do not modify the wrong=0-pinned train_sample serving runner** (~25 tests +
   its exit criterion guard it). Score correct/wrong/refused as *practice* metrics;
   wrongs produce elimination records. Invariant #1 proven (nothing leaks to
   serving). Diagnostic refusal (§8) emitted.
3. **Grounded derivation search.** Bounded, deterministic operation-chain search
   over extracted quantities, gated by grounding + unit + unique + round-trip.
   Invariant #2 proven (the spurious-answer test). Measure the flip-curve on the
   multiplicative chunk; require it to hold under ADR-0114a perturbation.
4. **Tier-2 self-verification + provenance + tether.** Convergent self-verification,
   per-belief provenance, the live gold tether + `t2_precision`. Invariant #5
   proven. Widen the arena past gold-labeled material.
5. **Self-proving proposals into the ratification corridor.** Add a
   **solver-practice evidence type** alongside the reader-refusal-coupled
   `MathReaderRefusalEvidence`; practice emits proof-carrying proposals; the
   (narrowing) HITL gate admits to serving. Measure the serving-`correct` lift this
   produces with `wrong=0` held.

## Acceptance criteria (Proposed → Accepted)

1. Phase 1 substrate lands; invariants #3–#4 proven; serving byte-identical.
2. A prototype grounded search demonstrably **refuses** the `20/5`-class spurious
   derivation (invariant #2) on a curated case.
3. The practice regime is provably sealed from serving (invariant #1).
4. Capability-axis lanes G1–G5, S1 remain 100% `wrong=0`; pinned lane SHAs pass.
5. Cross-references to ADR-0174 (substrate), teaching-safety (seal), and the
   thesis reviewed and confirmed consistent.

## Open questions

1. ~~**Shape of `conservative_floor` and `N_min`.**~~ **RESOLVED (§4a):** one-sided
   Wilson lower bound over *committed* trials, `z = 2.576`, `N_min = 10`, float64
   rounded half-to-even to 1e-9 for replay. `z` is the single pinned pessimism
   constant; per-class `θ` ceilings remain the human autonomy dial.
2. **First practice-arena home.** GSM8K train (gold-labeled, checkable, already
   wired) is the obvious Phase 2/3 home; confirm no serving-path coupling remains
   after the train_sample double-duty decoupling.
3. **Search bound + determinism budget.** The operation-chain search must be
   bounded and replay-stable; fix the enumeration order and depth cap before
   Phase 3.

## Pre-implementation audit (2026-05-28)

Per CLAUDE.md §Lookback Review Discipline + §ADR cross-reference discipline, the
existing substrate was audited for conflicts *before* any code. **No hard blockers
or contradictions.** Findings:

**Reinforcing alignments (the design fits the grain):**
- **ADR-0165 (Regex Scope Rule).** Its line — regex may match *orthographic shape*
  (lexemes) but never *grammar* (how words combine to mean X) — is exactly this
  ADR's thin-front-end / thick-solver split. Extraction stays lexeme-level;
  *combining is the solver's attempt, never grammar-regex.* 0175 fulfills 0165.
- **INV-07 governance** already forbids non-deterministic/low-trust frontends from
  claiming `AUTO_ACCEPT_ELIGIBLE` at construction — our no-self-authorization
  principle, pre-wired.
- **`MAX_TOTAL_BRANCHES = 64`** establishes bounded-deterministic-enumeration-with-
  refuse-on-overflow; the derivation search inherits this pattern.
- **The seal** (teaching-safety, proposal-only/reviewed) exists and is reusable.

**Drift corrected in this ADR (overclaims of reuse):**
- The reliability **ledger is new** — `calibration/` is a grid-search param tuner,
  not a per-class ledger.
- The 0174 elimination substrate is **reading-coupled** (`Hypothesis`,
  `ProblemReadingState`, parse-shaped predicates); "repoint to solving" requires
  **generalization**, not drop-in reuse.
- The teaching corridor's evidence schema (`MathReaderRefusalEvidence`, grouped by
  `refusal_reason × missing_operator`) is **reader-refusal-coupled**; solver-practice
  proposals need a **new evidence type**.

**Binding constraints (not conflicts):**
- **wrong=0 is pinned on the serving/eval lane by ~25 test files + the train_sample
  runner exit criterion.** Preserved, not contradicted — therefore **practice must
  be a separate lane**; it cannot reuse the train_sample runner. Confirms the
  double-duty decouple is mandatory.
- Determinism invariants (INV-05/13) bind the ledger/gate/search → the §4a float
  rounding contract.

## Lookback review — Phases 1–3b stack (2026-05-28)

Per CLAUDE.md §Lookback Review Discipline (5 PRs on one new surface + before
merging a stacked sequence). Shipped: Phase 1 `core/reliability_gate/` (#432),
Phase 2 `evals/gsm8k_math/practice/v1/` (#433), Phase 3a `generate/derivation/`
self-verify gate (#434), Phase 3b multiplicative search (#435).

**Solid.** All four invariants exercised by failing-under-violation tests
(#1 seal, #2 spurious-refusal, #3 determinism, #4 no-self-authorization); 84
tests green; seal grep-verified (no `generate`/`chat` import of any new surface;
serving 3/47/0 unchanged; 0050 refuses in serving).

**No live hazards.** Phase 3b's search produced 9 wrong attempts — all sealed
practice eliminations, never served; nothing reads the practice ledger to gate
serving yet.

**Drift recorded:**

1. **The shipped self-verification gate (3a) is *partial* vs this ADR's Tier-2 /
   Phase-3 spec.** Shipped: `operand-grounding ∧ cue-grounding ∧ unit ∧
   uniqueness`. **Not yet wired: round-trip and no-contradiction-with-vault.**
   Phase 3b's headline finding — self-verification is **necessary but NOT
   sufficient** (9 of 13 self-verified attempts were wrong vs gold) — is partly
   *because* those stronger clauses are deferred. **Consequence:** before Phase 5
   lets self-verification gate proposals, the gate MUST be strengthened
   (wire round-trip + no-contradiction; broaden candidate enumeration so
   disagreement refuses ambiguous cases) and the cue model refined from the
   practice eliminations. This inserts a **self-verification-strengthening phase
   before Phase 5**.

2. **Class taxonomy divergence.** Phase 2 buckets by gold-derived operation class
   `{multiplicative, divisive, additive}`; this ADR says `class = capability axis
   G1–G5`. The train_sample cases are not axis-tagged, so operation-class is the
   pragmatic per-case label. Reconcile when the practice arena widens beyond
   train_sample.

3. **Minor test gaps (no risk):** a few defensive/edge branches untested
   (`Step` invalid-op, `.answer` subtract, floor TypeError + ≥1.0 clamp); not
   invariant-bearing. `pytest-cov` unavailable (numpy/coverage process conflict);
   coverage audited manually.

## Cross-references

- **Derivation:** [SESSION-2026-05-28](../sessions/SESSION-2026-05-28-risk-reward-learning-architecture.md).
- **Substrate repointed:** [ADR-0174](./ADR-0174-held-hypothesis-comprehension.md)
  (`eliminate_violating` / `reevaluate` / `contemplate`), calibration module,
  capability axes G1–G5, round-trip filter + disagreement rule, teaching-safety.
- **Anti-overfitting obligations:** ADR-0114a (perturbation / OOD / depth / adversarial axes apply to every flipped case).
- **Thesis:** [[thesis-decoding-not-generating]] — find, comprehend, rationalize; not a library of founds.
