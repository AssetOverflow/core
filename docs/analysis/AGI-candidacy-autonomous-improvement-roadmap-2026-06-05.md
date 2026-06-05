# Roadmap: the autonomous-improvement engine (path to AGI-candidacy)

**Date:** 2026-06-05 · **Status:** ROADMAP (the hyperfocus design plan) · **Telos:** [[project-core-is-one-continuous-life]] — `listen → comprehend → recall → think → articulate → learn → replay`, as one continuous, ever-improving life.

## The bar (what we are actually building toward)

A **serious AGI candidate**: an engine that is at least as **book-smart as an LLM**,
**keeps up with the world**, and **forever gets smarter autonomously under human
supervision** — by **taking in inputs (literature, told facts, world inputs,
experiences), comprehending them, and *realizing* them as structured grounded
memory it can recall** — rather than the LLM move of bulk-absorbing the whole
corpus indiscriminately and compressing it into weights.

> **Clarification — "intake" vs "ingestion".** The engine absolutely *ingests*:
> it must take in literature, knowledge, and experience to learn anything, and
> intake is first-class (Phase 3). The distinction from an LLM is *what is kept
> and how*: CORE keeps **selectively-realized, comprehended, provenance- and
> status-tagged knowledge + remembered experiences** (the vault + corpus *are* its
> memory, with exact recall), and never realizes unverified content as true — vs
> indiscriminately swallowing everything (junk included) and lossily averaging it
> into weights. "We don't need the world's *data*" means we get smart from
> comprehended structure + high-signal told facts, *not* that we don't take input.

What the bar is **not**: mass indiscriminate absorption, statistical
pattern-matching, or confident guessing (the LLM trick — and a different identity
config could even make our own models behave that way; it is not the point).
Determinism / `wrong=0` / auditability are the **necessary baseline**, not the
achievement.

## The strategic key: grounded honesty is the efficient-learning mechanism

An LLM must swallow the entire internet — junk, lies, contradictions — and average
its way past them. CORE **only realizes what it can ground** (told-and-evidenced,
comprehended, or reasoned), so it never absorbs garbage and never has to unlearn
it. The junk-filter *is* the learning advantage: we don't need the world's data,
we need the world's **true, comprehended structure**, accumulated forever. So
grounding is load-bearing for the *capability*, not just for trust. (`wrong=0` is
the high-stakes gear of this honesty — see the epistemic foundation below — not a
universal law that forces the engine to refuse everything it can't prove.)

## The loop (the autonomous-improvement engine)

```
open question / discovery / TOLD fact
   → COMPREHEND (arbitrary input → structured meaning)
   → REALIZE (make it real: integrate into the held self with an epistemic status)
   → REASON / GROUND / RECALL
   → RESPOND in the honest gear:
        ASSERT (verified / realized)
        ESTIMATE (evidence-grounded likelihood — ONLY where taught it is apt)
        REFUSE (no grounding, or stakes forbid an estimate)
   → PROPOSE (idle_tick, proposal-only)
   → HITL ratify (reviewed, supervised)
   → ACCUMULATE into the one continuous life
   → MEASURABLY more capable  →  repeat, autonomously
```

When this loop demonstrably climbs a **general capability curve** over time, on its
own, under supervision — that is the AGI candidate.

## The epistemic foundation (honesty designed, estimation learned)

This corrects an earlier over-emphasis on `wrong=0` as a universal law. The right
frame has three commitments:

1. **Honesty is designed in; confabulation is impossible by construction.** The
   engine's native stance is grounded: ASSERT what it has realized, REFUSE what it
   has not. It has **no organ that fabricates** — no statistical token-soup, no
   manufactured confidence. That cannot emerge by accident; it could only be
   *deliberately built*, and we will not build it. This is the absolute floor, not
   a policy defended turn by turn.

2. **Estimation is a LEARNED, ratified competence — never a designed-in default.**
   There is a season for a calibrated assessment (*"on the evidence, most likely
   X"*). The engine may acquire the competence to give one — **but only through
   human ratification and deliberate guidance**, realized as knowledge like any
   other. We do NOT design a "guess mode" with a risk knob; the engine never
   self-authorizes a guess. `wrong=0` is therefore **demoted to one gear**
   (high-stakes / verified assertion), not deleted.

3. **All confidence is evidence-grounded, so even uncertainty is honest.** A CORE
   "likelihood" attaches to the deterministic confidence primitives we already
   have — the calibrated-learning ledger, one-sided Wilson floors, cue-precision
   reliability counts, the `EpistemicStatus` taxonomy. It means *"seen N times, M
   coherent → confidence M/N with a hard lower bound"* — a counted fact about the
   engine's own realized experience, not a vibe. This is the exact inverse of an
   LLM (softmax over absorbed text) and is **why it can offer graded answers
   without ever confabulating**.

**The measured invariant is calibration + grounding, not "never wrong":** every
confidence the engine states must trace to counted evidence, and it offers graded
answers only where it was taught that is appropriate. Being *honestly uncertain*
is success; being *dishonestly confident* is the only failure — and the substrate
makes the latter impossible without intentional design.

> **"Being told" is first-class.** Most knowledge arrives as *told facts* ("these
> are facts"); the engine realizes them and earns the why/how (coherence /
> evidence) over time. Determination does NOT mean proof-from-first-principles —
> intake → realize-with-evidence → build coherence is a primary growth path. The
> seed packs are the told bootstrap; the engine comprehends the new by relating it
> to what it has already realized, and grows.

## What is already built (compose, don't rebuild)

- **The continuous self** — Shape B+ resume ([[milestone-shape-b-plus-persistence]]),
  L11 identity continuity + the idle learning mechanism
  ([[milestone-l11-identity-and-continuous-learning]]). The life that accumulates.
- **Verified reasoning substrate** — sound+complete propositional entailment
  (`deductive_logic`, wrong=0, independent gold), `generate/proof_chain/`
  (proof-tree builder/entail/rules), `generate/binding_graph/` (the universal-
  structure interlingua DAG).
- **Determination pieces** — `core/reliability_gate/` (gold-tether, ledger,
  calibrated propose) determines correctness in the math lane; the wrong=0
  self-verification gate in `generate/derivation/verify.py`.
- **Comprehension front door** — `generate/derivation/` (extract → clauses →
  compose), the question layer.
- **Measurement raw material** — independent-gold lanes (`deductive_logic`,
  `relational_metric`, `dimensional`, `cold_start_grounding`, `symbolic_logic`)
  + the Perplexity-surveyed adoptables (ProntoQA, ProofWriter-CWA, CLUTRR, FOLIO —
  all with independently-checkable gold + a refuse class).

## The bottleneck that gates everything

The flywheel can only **propose what is already determined** — `idle_tick` refuses
`undetermined` candidates. The engine can *learn a fact it is handed*; it cannot yet
autonomously **figure one out**. The missing organ is **general determination**:
comprehend an open question, reason/ground it to a *verified* conclusion (or refuse),
and feed *that* to the flywheel. The math lane does a narrow version; nothing does
it generally. **Closing comprehend → determine → learn, measured on a general
capability curve, is the load-bearing arc.**

## Phased roadmap (entry → exit gates; wrong=0 is structural throughout)

| Phase | Build | Exit gate / measurement |
|-------|-------|-------------------------|
| **0 — the yardstick** | A **general capability index**: compose the independent-gold reasoning lanes (+ adopt ProntoQA/ProofWriter-CWA/CLUTRR/FOLIO) into one report with two axes — **correctness (wrong=0, never fabricate)** and **coverage (determined vs honestly-refused)**. Frozen-gated. | A single reproducible capability number the engine must climb; `wrong=0` enforced; a baseline measured. *You cannot improve what you cannot measure.* |
| **1 — the determination organ** | A general `determine(question) → {determined: conclusion ∣ refused}` path composing comprehension (`derivation`/`binding_graph`) + reasoning (`proof_chain`/`deductive`) + the reliability gate. Commits ONLY verified conclusions; refuses the rest. | On the Phase-0 yardstick: coverage rises with **wrong still 0**; every committed conclusion is independently checkable. |
| **2 — close the autonomous loop** | Wire `determine` → the `idle_tick` flywheel: take open questions, determine what it can (wrong=0), propose, HITL-ratify, accumulate. | The capability index **rises across loop iterations**, autonomously, under supervision — falsifiably (a frozen replay shows monotonic, junk-free improvement). |
| **3 — autonomous curriculum** | The engine drives its own agenda: identifies its determination frontier (what it can't yet determine), proposes what to learn next, under HITL guidance. | "Forever getting smarter autonomously under supervision" — the engine's self-chosen curriculum measurably advances the index. |
| **4 — breadth / generality** | Expand comprehension + reasoning across domains so the index is genuinely GENERAL (book-smart breadth), acquired via the loop — intake → comprehend → realize, not bulk indiscriminate absorption. | The capability index spans enough domains to credibly claim general book-smarts — every gain via comprehension+determination over realized knowledge, none via indiscriminate corpus absorption or per-domain matchers. |

## Invariants (non-negotiable across all phases)

- **`wrong=0` is structural** — the engine commits only verified conclusions; it
  refuses rather than fabricates. This is the learning filter, not just a gate.
- **Reviewed learning** — ratification stays HITL (`teaching/review`); the loop
  *proposes*, the human *ratifies*. Autonomy is supervised, not unmoored.
- **Determinism / replay** — every capability gain is reproducible; improvement is
  a replayable curve, not a vibe.
- **Identity continuity** — the improving engine stays one continuous self
  (L11); a smarter CORE is the *same* CORE, grown.

## Execution order — logical necessity × technical priority

Not arbitrary phases: each step is gated by what it *logically depends on*, then
ordered within that by leverage × risk. The dependency DAG:

```
        MEASURE ───────────────────────────────────┐ (gates every "improved" claim)
           │                                        │
     COMPREHEND  ──► REALIZE ──► DETERMINE/RESPOND ─┼─► AUTONOMOUS LOOP ──► CURRICULUM
   (NL → universal     (hold      (assert / refuse  │      (idle_tick           + BREADTH
    interlingua)      with         over realized)   │   climbs the curve,
                      status)          │            │   autonomously)
                                       └─ LEARNED ESTIMATION ◄── needs MEASURE(calibration)
                                          (ratified, evidence-grounded)
```

**Step 1 — MEASURE: the cross-domain capability yardstick.** *Logical necessity:*
nothing can be called "more capable" without it; it is prior to all improvement.
*Technical priority:* HIGH leverage (north-star instrument + the anti-self-
deception guard — a per-domain hack moves one lane and breadth stays flat,
exposing it), MODERATE effort (compose the existing independent-gold lanes +
adopt ProntoQA/ProofWriter-CWA/CLUTRR/FOLIO). Measures **assert-correctness +
grounding + coverage + calibration** under a configurable risk budget. **Build
first.**

**Step 2 — COMPREHEND: NL/prose → the universal interlingua.** *Logical
necessity:* it is the wall (GSM8K refuses 92% on comprehension coverage, not
arithmetic; prose/exams are ~0); every downstream step needs structure to operate
on. *Technical priority:* HIGHEST leverage (unlocks all breadth) AND HIGHEST
risk/effort (open-ended; the overfit trap lives here). The discipline: it must
emit the **general** binding-graph / universal-structure, never per-domain parses
— and the Step-1 yardstick is what proves it generalized rather than gamed. **The
make-or-break.**

**Step 3 — REALIZE: integrate comprehended/told structure into the held self**
with an epistemic status (`EpistemicStatus`), persisted via Shape B+. *Necessity:*
needs COMPREHEND. *Priority:* MODERATE effort (vault/corpus/persistence exist),
HIGH leverage — this is what makes knowledge *accumulate* (told facts become
realized; the engine grows). Intake ("being told") lands here.

**Step 4 — DETERMINE / RESPOND: reason over realized structure → the honest
gear** (assert verified / refuse ungrounded). *Necessity:* needs COMPREHEND +
REALIZE. *Priority:* MODERATE effort (compose `proof_chain` / `deductive` /
binding-graph entail onto comprehension output), HIGH leverage — coverage rises
on the yardstick with grounding intact. **No estimation yet — assert/refuse only.**

**Step 5 — AUTONOMOUS LOOP: wire comprehend→realize→determine→idle_tick→ratify→
accumulate.** *Necessity:* needs Steps 1–4. *Priority:* MODERATE effort (idle_tick
exists), HIGH leverage — this is the step that makes "forever improving" real and
falsifiable (the yardstick curve climbs autonomously, under supervision).

**Step 6 — LEARNED ESTIMATION: the calibrated likelihood competence.**
*Necessity:* needs DETERMINE (the honest floor) + MEASURE-calibration + the
teaching loop. *Priority:* MODERATE effort, MODERATE leverage — deliberately
LATE: only after the assert/refuse floor and the calibration measurement are
solid do we teach (HITL-ratified) when/how to offer evidence-grounded likelihoods.
Never a designed-in default.

**Step 7 — AUTONOMOUS CURRICULUM + BREADTH.** *Necessity:* needs the loop. The
engine drives its own determination frontier under supervision; breadth expands
across domains via the loop (intake → comprehend → realize), never via
indiscriminate corpus absorption or per-domain matchers.

**Critical-path summary:** `MEASURE → COMPREHEND → REALIZE → DETERMINE → LOOP`,
with ESTIMATION grafted after DETERMINE+MEASURE and CURRICULUM after LOOP. The
single highest-risk step is **COMPREHEND** (Step 2); the single highest-necessity
"do-first" is **MEASURE** (Step 1), because it is the only thing that keeps every
later step honest.

## Cross-cutting invariants (hold at every step)

The 8 foundation commitments above, plus the standing CLAUDE.md invariants:
`versor_condition < 1e-6` (math floor), no forbidden-site repair/normalization,
reviewed learning stays HITL, exact CGA recall (no approximation), deterministic
replay. Every step is TDD + mutation-verified-to-bite + curated-smoke + CI-lane-SHA
gated, the way the L10→L11 spine was built.

## Honest scope boundary

This is the multi-phase arc to AGI-candidacy, not one PR. AGI is the destination;
this roadmap is the **critical path** and the **measurement** that makes progress
toward it real and falsifiable. **Phase 0 (the yardstick) is the first build** —
without a general capability curve, "getting smarter" is unfalsifiable, and we'd
be doing exactly the unmeasured hand-waving the LLM world runs on.
