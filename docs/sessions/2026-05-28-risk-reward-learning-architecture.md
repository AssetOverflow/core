# Session 2026-05-28 — From "Another Matcher" to a Self-Calibrating Problem Solver

**Status:** Discussion captured ✓ — ADR-0175 to follow
**Headline:** A scoping session for GSM8K Phase 5b turned into the discovery that the
whole "build another recognizer per problem shape" strategy is structurally
self-limiting (overfitting by construction), and converged on a different
architecture: **move the intelligence into the solver (attempt + eliminate),
separate a sealed practice regime from the wrong=0 serving regime, and gate
attempts with a deterministic risk/reward ratio grounded in earned per-class
calibration.** This document is the *journey* — the problem, the dead-ends, the
pivots, and how we arrived at the solution. The formal decision is **ADR-0175**.

---

## TL;DR

We started trying to scope "Phase 5b.1 — single-sentence multiplicative
aggregate." Measurement showed the target was **one idiosyncratic case (0021)**,
and that the broader per-shape-matcher approach can never compound: GSM8K
phrasings are unbounded, so each matcher buys a handful of cases and the curve
flattens. That is overfitting wearing an engineering hat.

The turn (driven by Shay): stop asking the *front-end* to recognize every shape;
give the *solver* room to **attempt** a derivation over extracted quantities and
**learn by elimination** from what's wrong. The solver already supports the
operations; the front-end was the bottleneck and the source of brittleness.

That exposed the real contradiction: a system that **refuses whenever uncertain
is safe but frozen** — it can only ever learn what a human hands it. Autonomous
learning *requires* attempting through uncertainty, which is exactly where being
wrong lives. You cannot have autonomous learning and a global "never be wrong" at
once.

Resolution: **two regimes** — *serving* (wrong=0, refuse-unless-certain,
unchanged) and *sealed practice* (attempt-and-eliminate, where wrong is the
learning signal, not a failure) — separated by a **proof-carrying seal**. Which
regime applies is decided per-attempt by a **deterministic risk/reward ratio**:
`measured_reliability(class) / required_reliability(action) ≥ 1`. Reliability is
an **earned, per-class, conservatively-bounded count** from a live gold tether —
not a learned weight, not a probability from nowhere. Checkability is a **tiered
ladder** (gold > convergent self-verification > consistency-only) where the
*privilege a passed check earns* scales with the check's strength, and everything
weak is reversible. Humans raise the per-class ceiling on evidence; the engine
never self-authorizes.

---

## Where we started: scoping Phase 5b.1

Phase 5a had just shipped (PR #430): the inert GSM8K reader retired, single
canonical parse path, `3/47/0` byte-identical, net −1,038 LOC. We turned to
Phase 5b — the *semantic* lift — and began with what the scope called the
cleanest first slice: "single-sentence multiplicative aggregate" (e.g. case 0021,
"He bench presses 15 pounds for 10 reps and does 3 sets" → 15×10×3 = 450).

## Dead-end #1 — the per-shape matcher reflex

Every instinct pulled toward *building another recognizer*: detect this shape,
emit that primitive. Two measurements stopped that cold.

**The brute-force measurement that lied.** A bounded expression search over each
refused case's numbers found "matches" — but several were *coincidences*
(`20/5 = 4` for a case whose answer was 4 for unrelated reasons; `5−3 = 2`). The
measurement itself overfit. Lesson banked: **number-matching without grounding
manufactures spurious answers** — the same hazard a naive solver search would
have.

**The ground-truth measurement.** Parsing GSM8K's own `<<a*b=c>>` calculator
annotations (real operations, not guesses) over the 47 refused cases:

| Profile | Count | Share |
|---|---|---|
| Uses multiplication (`*`) | **37/47** | 79% |
| Uses mul **or** div | 43/47 | 91% |
| Pure add/subtract | 4/47 | 9% |
| **Single-step solvable** | **0/47** | **0%** |

Step-count histogram: `2:13 · 3:12 · 4:8 · 5:8 · 6:3 · 7:3`.

And a scan for *single-sentence* multiplicative aggregates (all operands in one
clause, gold = their product) returned exactly **one** case — 0021 — whose
surface ("for 10 reps and does 3 sets", pronoun subject, three different units)
is the *least* general multiplicative shape in the set, not the simplest.

**The conclusion that reframed everything:** multiplication is needed by 79% of
the corpus (maximally general — a foundational capability, not a niche), but
**no case is solvable in one step**, and the regular in-clause shape *already
works* via existing Wave-A scaffolding. So a "single-sentence multiplicative
matcher" would flip ~1 case via near-bespoke pattern matching — the textbook
definition of overfitting the project has repeatedly ruled out ("lifting a few at
a time → simply overfitting"). The per-shape path is unbounded because phrasings
are unbounded. It cannot compound.

## Pivot #1 (Shay) — breadth-of-impact is the overfitting test

> "If solutions result in generally large chunks of failed results turning green,
> then it's more likely that we are getting GENERALLY smarter... if tweaking the
> injector fixes a big chunk or percentage then it COULD be a solution."

This corrected a sloppy framing ("tweaking the injector = overfitting"). The
overfitting test isn't *where* the fix lives — it's **breadth**: a change that
flips a large *general* chunk (and holds under perturbation) is a real capability;
a per-phrasing patch that flips one case is overfitting. The measurement said the
biggest, most general chunk is *multiplication itself* — so the question became
"how do we get general multiplicative capability," not "how do we match 0021."

## Pivot #2 (Shay) — give the solver room to attempt; move the intelligence

> "Maybe the solution is to give it more room to attempt to solve the problem...
> the better we make the problem solver, the better the model will be at
> anything/everything... the less we will have to put into packs and the less it
> will have to contemplate over time, and the faster it will learn what works and
> it compounds. That's what intelligence does."

This is the architectural turn. Today the front-end (recognizer/injector) must
hand the solver a *fully-typed, correct* graph or the solver does nothing — so
all intelligence is forced into surface pattern-matching, and surface is infinite.
The capable part sits idle:

- The **solver already supports** `{add, subtract, transfer, multiply, divide,
  apply_rate, compare_additive, compare_multiplicative}` with pack lemmas for
  each. It just waits passively.
- The gap is entirely the **reader → injector → Operation** front-end (the
  recognizer matches a shape but extracts *zero* anchors on real sentences).

The redirection: shrink the front-end to **extract quantities + the relations the
text licenses**, and grow the solver to **attempt** — search the bounded space of
operation-chains for a derivation that reaches a *verifiable* answer. This
generalizes across all phrasings because it never looks at phrasing — it looks at
quantities and the goal. The compounding the project wants comes from the solver,
not from a growing library of founds (the [[thesis-decoding-not-generating]]).

**The honest crux we named:** search makes wrong=0 *harder*, not easier — an
active searcher has more chances to land on a spurious-but-valid answer (cf. the
brute-force `20/5`). The whole approach rests on the derivation being **grounded**
(each step licensed by text + unit-consistent), **unique-or-refuse** (the existing
disagreement rule), and **round-trip-checked** (realize back to language, reject
if it doesn't match the problem). Those gates already exist in CORE.

## Insight #3 — two failure modes, and the diagnosis that routes them

> "Either it has enough information... to work the problem with masterfully built
> problem-solving skill, or it needs a wider understanding of what it's trying to
> decode... it needs more pieces to the puzzle."

When the engine can't decode a problem, exactly one of three things is true:

1. **Skill gap** — has the pieces, can't compose the derivation → improve the
   reasoner.
2. **Knowledge gap** — missing a world-fact (what "twice" means, that "each basket
   holds 50" is a per-container rate) → acquire knowledge.
3. **Genuine ambiguity** — under-determined → refuse, correctly, forever.

The mechanism that makes "finding the pieces" efficient is **diagnostic refusal**:
a refusal that *names the missing piece* routes itself to the right axis
("quantities extracted but no grounded derivation" = skill; "unknown relation:
twice" = knowledge; "two grounded derivations disagree" = ambiguity). CORE already
has typed refusals, the OOV honesty gradient, and the math-reader-refusal audit
corridor. Knowing what you don't know is most of knowing how to find it.

**Three compounding stores**, each fed by the matching diagnosis:
- **experience → vault** (exact, deterministic recall),
- **world-knowledge → ratified packs**,
- **skill → solver's elimination-learned pruning**.

**The floor (Shay):** "it cannot conjure world-facts from nothing. not even a
human can. only God himself." Autonomy doesn't mean "no input" — facts about the
world must enter from a data/experience stream. The human role *shifts* from
hand-authoring meaning to **curating what it ingests + ratifying what it has
already self-proven**. The bridge is **self-proving acquisition**: a new fact is
admitted with a *mechanical proof attached* (round-trips, forced-unique, zero
wrong, replay-stable) — the schema-proof-obligation discipline, pointed at
learning. Knowledge acquired with a proof needs less judgment to admit.

## Pivot #4 (Shay) — the contradiction, and the "mode"

> "If we intentionally build around it always 'giving up' whenever it doesn't
> know, it will never learn without humans. Maybe there should be a 'mode' for
> when it's allowed to work on a problem... a type of risk-to-reward RATIO system
> (not... reinforcement learning; not that kind of risk/reward)."

This is the central contradiction stated exactly: **refuse-when-uncertain is safe
and frozen.** The resolution can't be a global setting — it must be contextual.

**Two regimes (the concrete "mode"):**
- **Serving** — committed to someone who will act on it; cost of error ≈ ∞;
  refuse unless certain; **wrong=0, absolute, unchanged.**
- **Practice** — attempting where being wrong is *checkable and not served*; here
  **wrong is the elimination signal**, the most informative event possible. The
  only place autonomous learning can happen.

What keeps wrong=0 intact while practice runs hot: the **proof-carrying seal** —
practice emits *proposals carrying their own proof*; nothing reaches serving
except via the (narrowing) ratification gate. CORE already has this seal
(proposal-only, reviewed teaching).

**"Creative," defined for a deterministic engine:** not stochastic invention — a
**willingness to leap a gap in known structure** (a recombination no stored
pattern directly licenses). The risk is the leap is unwarranted; the reward is
that a *verified* leap becomes new structure. It is always a step from solid
ground, never from the void — the engineering form of "only God conjures from
nothing." The risk/reward gate decides *how far across an unlit gap calibration
permits a step.*

## The checkability question — and the tiered answer

If practice can attempt without a human or a gold label, *what counts as checkable
enough to learn from?* The asymmetry that governs the answer: **a false positive
in the checker is far worse than a missed learning opportunity** — a wrongly
"verified" belief is a persistent contaminant; a refusal is just a missed chance.

So the boundary isn't a line — it's a **confidence-stratified ladder**, with the
rule: *require check-strength proportional to the reversibility/blast-radius of
the action it licenses.*

| Tier | Checker | May change |
|---|---|---|
| **1 — External truth** | gold label / known answer | serving-bound knowledge (via ratification) — anchors |
| **2 — Convergent self-verification** | round-trip **∧** ≥2 *structurally-distinct* derivations agree **∧** unit-consistent **∧** no contradiction with vault/packs | provisional, **retractable** knowledge (still ratified) |
| **3 — Consistency-only** | merely no contradiction | **practice-internal pruning only** — never crosses the seal |

**Tier 2 is the median** — the widest checkability still strong enough to *create*
knowledge, needing no label, so the arena scales toward open-world. Two
safeguards make widening safe:
- **Provenance per belief** `(tier, n_at_admission)` → Tier-2 beliefs are
  *retractable* when a stronger check later contradicts them.
- **A live gold tether** measuring `t2_precision(class)` — catches *correlated
  self-delusion* (a shared wrong premise makes all derivations agree); when it
  drifts, appetite contracts. Independence is *counted* (≥2 structurally-distinct
  paths), not assumed.

## Quantifying it — the part that makes it engineering

The naive ratio needs units for "value" and "learning" — a quagmire. The regime
structure **collapses the reward side**: in serving only reliability matters
(learning is irrelevant to a served answer); in sealed practice the threshold is
just "is it checkable?". So **the entire numeric system reduces to: measure
reliability, compare to a ceiling.** Everything else is counting.

Per **class** (= capability axis G1–G5), a replayable **ledger of counts** —
nothing learned, nothing stochastic:

- `n(C), correct(C), wrong(C), refused(C)` — the eval already counts these.
- `t2_verified(C), t2_agrees_gold(C)` — on the live anchor set.
- `reliability(C) = conservative_floor(correct, n)` — a deterministic **lower
  bound** (pessimistic at small n, so luck can't grant appetite).
- `t2_precision(C) = conservative_floor(t2_agrees_gold, t2_verified)` — how
  trustworthy self-verification is on C; the number that licenses widening past
  gold.

**The gate is a literal ratio:**
```
license(action, C) := reliability_of_relevant_checker(C) / θ_required(action, C) ≥ 1
```
`θ` are **human-set, version-controlled constants** per class and blast-radius
(`θ_practice = 0`; `θ_propose`; `θ_serve` strict, e.g. .99). "Humans ready to let
it" = a human lowering `θ_serve(C)` for a class the ledger has earned.

**Compounding becomes a measurable curve:** `refused(C)` ↓ and `reliability(C)` ↑
with practice volume, `wrong` on serving pinned at 0 throughout. And the
**skill-vs-knowledge diagnosis is quantified**: if reliability still climbs with
practice → skill gap (keep practicing); if it has stalled → knowledge gap (needs a
new world-fact). Learning-rate = reliability gain per unit practice.

Almost none of this is new machinery — it's composition: classes = capability
axes; counts = the eval harness; reliability + lower bound = the calibration
module; replay guarantees reproducibility; `θ` = a small config table; seal +
ratification = existing teaching-safety.

## The converged model (one line)

> attempt-or-refuse is a **per-context risk/reward decision**, not a global rule →
> **two regimes** (serving wrong=0 / sealed practice attempt-and-eliminate)
> separated by a **proof-carrying seal** → the ratio is
> `measured_reliability / required_reliability ≥ 1` → reliability is an **earned,
> conservatively-bounded, per-class count** from a live gold tether → checkability
> is a **tiered ladder** with privilege ∝ reversibility and provenance making weak
> beliefs retractable → humans **raise the ceiling on evidence**; the engine never
> self-authorizes → "creative" = a calibrated leap across a gap, always from given
> ground.

## Open question carried into the ADR

The one genuinely new number to pin: **the shape of the `conservative_floor`
function and `N_min`** — how pessimistic to be at small n. That single choice sets
how cautiously the whole system earns its autonomy.

## What this supersedes

The matcher-oriented Phase 5b sub-phases (5b.1 single-sentence / 5b.2
cross-sentence / 5b.3 deep) in ADR-0174 collapse into *instances* of this
architecture rather than standalone work. The multiplicative cases become the
first **practice arena** where attempt-and-eliminate is proven, not a set of
shapes to hand-match.

## Cross-references

- **Decision:** ADR-0175 (to be written).
- **Builds on:** ADR-0174 (held-hypothesis / `eliminate_violating` / `reevaluate`
  / `contemplate` — the elimination substrate, here repointed from *reading* to
  *solving*); the calibration module; capability axes G1–G5; the round-trip
  filter and multi-branch disagreement rule (the wrong=0 gates that make search
  safe); teaching-safety (proposal-only, reviewed) = the seal.
- **Thesis anchor:** [[thesis-decoding-not-generating]] — find/comprehend/
  rationalize, not a library of founds.
- **Phase 5a (shipped):** PR #430.
