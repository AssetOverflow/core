# Session 2026-06-08 — Practice-time attempts vs served answers, and the servability blade

**Status:** discussion / design note — **session document, not an ADR yet.** No
code shipped. This records a *refinement of doctrine* reached in conversation,
deliberately preserved before any new capability work so the idea cannot be
silently collapsed back into a binary gate. **Headline:** `wrong=0` has been
operating as a hard binary — **verified answer OR refusal** — and that binary,
correct for sealed evaluation, is wrong for collaborative reasoning. The real
law is **"no false presentation of epistemic status."** From that reframing fall
two proposed organs: a **ProblemAttemptSession** (where typed, isolated candidate
guesses are *allowed* at practice time) and a **ServabilityBlade** emitting a
**ServabilityDecision** (which chooses, at serving time, among *more than two*
truthfully-labeled output modes).

`No serving path, algebra, versor, recall, or gate touched. This is the research`
`trail — what we decided and how the conversation arrived there.`

> **Amended 2026-06-08 (see [§ Amendment](#amendment-2026-06-08--reconcile-with-adr-0206--epistemic_state-do-not-build-parallel-substrate) below).** The doctrine here stands, but the original draft **under-referenced substrate that already ships the serving half of this design.** `ServabilityDecision` / `ServabilityBlade` must be built as the **activation of the already-shipped ADR-0206 response-governance bridge** (`ReachPolicy` / `govern_response` / `shape_surface`, gated STRICT-only today, already disclosing `[approximate]`), and the `epistemic_state` Literal must **reuse `core/epistemic_state.py`** — *not* a parallel object or a smaller renamed enum. Read the Amendment before building.

> **Why this doc exists, and why now.** CORE is open-source research in a largely
> uncharted corner of AI — a deterministic cognitive engine, not a transformer
> wrapper. The *reasoning behind* a design is as load-bearing as the design.
> Capturing it as a **session doc rather than an ADR** is deliberate: the idea is
> a refinement, not yet a ratified architectural commitment. Writing it down now
> protects the research trail and **keeps future agents (and the operator) from
> collapsing the idea back into a binary gate** the next time the wrong=0
> invariant is invoked. An ADR can follow once PRA/REL exist and the blade has a
> concrete consumer.

---

## TL;DR — the refinement, in four lines

```text
wrong=0  ≠  binary answer/refuse
wrong=0  =  no false presentation of epistemic status
practice / contemplation  MAY  explore typed, isolated candidates (even guesses)
served output  NEEDS  a servability blade (more modes than verified | refuse)
```

1. **The binary we inherited.** The serving contract is, today, *emit a verified
   answer, or refuse.* That is the classic wrong=0 path
   ([[project-self-check-soundness-not-correctness]]) and it is **correct for
   sealed eval.**
2. **The over-reach.** Read literally, that binary also forbids partial
   reasoning, provisional insight, surfacing multiple admissible readings, and
   open-ended problem-solving — none of which are false presentations of truth.
   It makes the engine mute unless omniscient.
3. **The reframing.** Truth discipline is **disclosure discipline**: *never hide
   uncertainty; never promote a candidate to a fact; never collapse a hypothesis
   into a verified answer; never omit the reason a conclusion is provisional.* A
   *labeled* provisional answer is honest, not a lie.
4. **Two layers fall out.** A **practice/attempt layer** where typed, isolated
   candidates may be explored, and a **served-output blade** that decides what of
   that internal state is truthfully emittable in the current context.

---

## 1. The distinction: practice-time attempts vs served answers

This is the spine of the whole refinement. There are **two different lanes** with
**two different epistemic licenses**, and the binary gate conflated them by
applying the serving license everywhere.

| | **Practice / contemplation** | **Serving** |
|---|---|---|
| purpose | explore, attempt, eliminate, learn | emit to a user / downstream |
| may contain | guesses, attempts, pattern-matches, candidate eliminations, partial derivations | only what is *truthfully labelable* in context |
| failure mode it guards | *getting stuck / never learning* | *misrepresenting epistemic status* |
| existing substrate | sealed practice lane (ADR-0175), `comprehension_attempt`, contemplation, failure families, proposal-only learning | wrong=0 verify gate, refusal taxonomy, safety/refusal policy |
| license | **guessing allowed** (typed + isolated) | **no false presentation of status** |

The mistake was letting the *serving* license (prove-or-refuse) leak into the
*practice* lane, which would forbid the engine from ever attempting something it
cannot yet prove — i.e. forbid it from learning. And, symmetrically, letting the
*practice* binary ("we either solved it or we didn't") leak into *serving*, which
collapses everything that isn't a finished proof into silence.

**Practice may explore. Serving must disclose. Neither may lie.**

## 2. Why candidate guesses are allowed — *when typed and isolated*

A guess is dangerous only when it can be **mistaken for a fact** or **leak into
ratified state**. Remove those two hazards and a guess becomes a legitimate
research instrument. Two conditions make it safe:

- **Typed.** A candidate is not a free-floating string asserted as an answer. It
  is a *typed object* carrying its own epistemic status (`inferred`,
  `underdetermined`, `ambiguous`, …), its basis, and its eliminations. Its type
  *is* its honesty: nothing about a typed candidate claims to be verified.
- **Isolated.** The candidate lives in the practice/attempt lane and the
  proposal-only learning path ([[project-next-batch-contemplation-prototype]]:
  `teaching/proposals/` emits, never self-installs). It cannot reach serving, and
  it cannot ratify itself into corpus or packs. The fail-closed boundary already
  exists; the guess simply lives behind it.

Under those two conditions the existing **sealed practice lane** (ADR-0175:
attempt-and-eliminate, [[adr-0175-calibrated-learning-architecture]]) is already
*doing this safely* — accumulating typed attempts and eliminations under a Wilson
floor without ever touching the wrong=0 serving metric. The refinement is to name
the principle explicitly so it is not re-litigated: **typed + isolated ⇒ a
candidate guess is admissible at practice time.**

## 3. Why served output needs more than verified/refuse

The same internal evidence should produce *different* emissions depending on
context — and "refuse" is frequently the *worst* truthful option available.
Examples where a third mode is strictly more honest *and* more useful:

- **Partial progress** — *"I can establish these constraints but can't yet pin a
  unique answer; one variable is underdetermined."* (More useful than refusal,
  asserts nothing false.)
- **Multiple candidates** — *"Two admissible readings: under A the answer is 12,
  under B it's 15; the text doesn't disambiguate."* (The honest output for
  genuinely ambiguous input — refusal *hides* the real finding.)
- **Provisional working answer** — *"Best current setup is this; I haven't
  verified every assumption, so treat it as provisional."* (Honest disclosure for
  collaborative, low/medium-risk work.)
- **Clarifying question** — *"Does 'total animals' include the dogs?"* (When the
  ambiguity is resolvable by the user.)

The unifying rule — **the engine may emit anything it can truthfully label:**

| May emit (truthfully labeled) | May **not** emit |
|---|---|
| verified fact **as** verified | hypothesis **as** fact |
| inference **as** inference | guess **as** proof |
| hypothesis **as** hypothesis | partial setup **as** complete |
| partial result **as** partial | pattern-match **as** verification |
| ambiguity **as** ambiguity | unreviewed proposal **as** ratified |
| failure **as** failure | |

The right column is the real wrong=0. The binary was needlessly suppressing the
left column.

## 4. Proposed: `ProblemAttemptSession` (PRA)

The practice-lane evidence object. It records the typed candidates, what's been
eliminated, and what ambiguity remains — the substrate the blade later reads. (The
comprehension-attempt substrate from [[project-next-batch-contemplation-prototype]]
— `core/comprehension_attempt/`, setup router, failure-family registry — is the
natural home; PRA firms up its *evidence shape*.)

```python
@dataclass(frozen=True)
class CandidateAttempt:
    value: str                              # the candidate answer/setup
    epistemic_state: Literal[
        "verified", "inferred", "underdetermined",
        "ambiguous", "contradicted", "unsupported",
    ]
    basis: tuple[str, ...]                  # why this candidate was produced
    eliminated_by: tuple[str, ...]          # checks that ruled it out (empty = live)

@dataclass(frozen=True)
class ProblemAttemptSession:
    problem_id: str
    reader: Literal["R1", "R2", "R3", "CMB"]   # which setup family produced it
    candidates: tuple[CandidateAttempt, ...]   # typed; guesses allowed here
    eliminated: tuple[CandidateAttempt, ...]
    residual_ambiguity: tuple[str, ...]        # unresolved readings/variables
    risk_context: Literal[
        "sealed_eval", "practice", "collaborative_work",
        "research", "tutoring", "safety_critical", "production_serving",
    ]
    # frozen, inspectable, replayable — an auditable artifact like every gate decision
```

Note what the type *guarantees*: a `CandidateAttempt` can never be mistaken for a
served fact, because its `epistemic_state` travels with it and `eliminated_by`
records its disqualification. This is the "typed" half of §2 made concrete.

## 5. Proposed: `ServabilityDecision` (SRV)

The serving-lane policy object. It consumes a `ProblemAttemptSession` plus risk
and user intent, and selects a *truthfully-labeled* output mode.

> **Reuse, don't reinvent (Amendment 2026-06-08):** this *is* the ADR-0206
> `ReachPolicy` / `govern_response` decision, gated STRICT today — not a new object.
> The `mode` values below map onto `ReachLevel` (`STRICT < APPROXIMATE < EXTRAPOLATE
> < CREATIVE`); the `epistemic_state` field must be `core.epistemic_state.EpistemicState`,
> not the Literal sketched here. Build SRV as the *activation* of that seam. See the Amendment.

```python
@dataclass(frozen=True)
class ServabilityDecision:
    mode: Literal[
        "verified_answer",            # proof complete — the classic wrong=0 path
        "provisional_working_answer", # strong-but-unratified, disclosed as such
        "partial_progress",           # useful, can't finish
        "multiple_candidates",        # several admissible readings survive
        "clarify",                    # ambiguity resolvable by the user
        "refuse_unsupported",         # can't proceed without guessing
        "refuse_unsafe",              # safety/high-risk threshold unmet
        "contradiction_report",       # evidence conflicts
    ]
    epistemic_state: Literal[
        "verified", "inferred", "underdetermined",
        "ambiguous", "contradicted", "unsupported",
    ]
    risk_level: Literal["low", "medium", "high", "sealed_eval"]
    confidence_basis: tuple[str, ...]      # why we believe what we believe
    required_disclosures: tuple[str, ...]  # caveats that MUST accompany the surface
    prohibited_phrases: tuple[str, ...]    # claims this mode may not make
    servable_claims: tuple[str, ...]       # what may actually be emitted
```

**Risk sets strictness, not the existence of the blade.** The *same* epistemic
state yields different modes by context:

```text
sealed_eval        → VERIFIED_ANSWER | REFUSE only        (no provisional)
practice           → (internal; not a served emission)
collaborative_work → PROVISIONAL_WORKING_ANSWER allowed
research           → hypotheses / candidate paths / uncertainty valued
tutoring           → MULTIPLE_CANDIDATES with explanation
safety_critical    → strict proof/source threshold; else caveat or refuse
production_serving → verified, else disclosed-provisional, else refuse
```

The answer/refuse binary is now visible as **the strict end of a spectrum**
(`sealed_eval` / `safety_critical`), retained verbatim there — not the whole
contract. This is what resolves the practice-vs-serving tension cleanly: serving
stops being binary and becomes **controlled disclosure**.

A provisional answer is truthful **iff** it carries its label: *"best current
inference … not fully verified … these assumptions are load-bearing … here is
what would change the answer."*

## 6. How this came from the R1 / R2 / R3 / CMB trajectory

The refinement was not abstract — it was forced by where the reader/compiler work
actually went. Each step produced **typed candidates and typed failures in an
isolated lane**, and that accumulation is what made the binary's coarseness
visible:

- **R1 — reconstruction reader.** Derivation/reconstruction over GSM8K
  ([[project-two-disjoint-gsm8k-readers]]). Committed serving sits at a few
  correct / many *refused* / **zero wrong** — i.e. the binary's "refuse" branch
  is doing almost all the work. The reader *knew things* about the refused cases
  it had no way to say.
- **R2 — constraint compiler.** Finite-integer linear-constraint setup compiler
  (ADR-0217, [[project-r2-constraint-compiler-built]]): prose → reader →
  `ConstraintProblem` → solver → answer-verifier with a **contradiction flag**.
  Here the engine started producing *structured, typed* intermediate state
  (underdetermined systems, contradictions) that is precisely *not* "verified
  answer" and *not* "nothing" — the first hard evidence that two modes were too
  few. The reader owns *setup*; the solver owns *solvability* — already a graded
  split.
- **R3 — single-rate / rates-time-state.** The rate family
  ([[project-it-idle-integration-and-frontier]]): exact-rational time-unit
  conversion (R3.2), single-rate setup → `quantity = rate × time`. Gold
  `13/13`, reader `9/0/4`. Rate/time problems are ambiguity-rich, which is
  exactly where *partial progress* and *multiple candidates* become the honest
  outputs.
- **CMB — the combined-rate ladder.** Combined rate is a *new semantic object*
  (two explicit rates over one shared unit, combined by an explicit `sum` /
  `difference` mode, then single-rate algebra over the result), with its own
  organ (`generate/combined_rate_comprehension/`) and ruler
  (`evals/combined_rate_oracle/`). Built as a staged ladder: **CMB-a** (model +
  gold + setup oracle — *"the ruler is defined and gold-valid"*, landed #650,
  [`cmb-a-combined-rate-ruler-2026-06-08`](../analysis/cmb-a-combined-rate-ruler-2026-06-08.md))
  → **CMB-b** (exact solver, int-or-refuse) → **CMB-c** (reader: prose →
  `CombinedRateProblem | Refusal`) → **CMB-d** (router / contemplation wiring +
  failure-family) → **CMB-e** (capability ledger). CMB is the sharpest evidence
  for this whole session: its **2×2 domain-entry grid** does not produce a flat
  refuse — it produces *typed, graded* outcomes at the setup boundary itself:

  |                | combination cue        | no cue                       |
  |----------------|------------------------|------------------------------|
  | **two rates**  | solved (sum/difference)| `combine_mode_ambiguous`     |
  | **one rate**   | `missing_second_rate`  | `not_combined_rate_shaped`   |

  `combine_mode_ambiguous` is explicitly *"a substantive refusal"* — the engine
  knows it is in combined-rate territory but cannot pick a unique mode. That is a
  textbook `MULTIPLE_CANDIDATES` / `clarify`, **not** the same epistemic object as
  `not_combined_rate_shaped` (out-of-domain, step aside to R3) or a clean solve.
  The binary gate has one bucket — "refuse" — for three structurally different
  states. CMB-a *already typed them apart*; it just has nowhere to send the
  distinction at serving.

**The throughline:** every rung — R1, R2, R3, CMB — kept generating *typed
intermediate epistemic states* (refused-but-known, underdetermined, contradicted,
**substantively-ambiguous**, out-of-domain), and the typed-contemplation lane
([[project-next-batch-contemplation-prototype]]: `core/comprehension_attempt/`,
failure-family registry, `teaching/proposals/` proposal-only emitter) kept
*exploring typed candidates in isolation* without ever denting wrong=0 (the
empirical proof of §2). The binary serving gate had nowhere to put any of it
except "refuse." The ServabilityBlade is the organ that finally gives that
accumulated, typed, isolated evidence a truthful way to reach the user.

---

## How it fits CORE (the ingredients already exist)

The blade is the **consumer** of organs already built, not a new subsystem:
epistemic states (derivation/verify), safety/normative clearance
([[safety-refusal-policy]] → `refuse_unsafe`, `required_disclosures`),
setup/answer oracles (`verified` vs `underdetermined` — e.g. CMB-a's combined-rate
ruler), the typed-contemplation / comprehension-attempt lane (→ the candidate
evidence), proposal-only learning (`proposal`
vs `ratified`), the existing [`refusal-taxonomy`](../refusal-taxonomy.md) (→ the
`refuse_*` / `contradiction_report` branches), and the calibrated reliability gate
(ADR-0175 Wilson floors → `risk_level` / `confidence_basis` for the provisional
mode). The work is **integration + a policy object** — same character as the
AGI-spine integration phase ([[milestone-agi-spine-A-to-E-complete]]).

## Why this matters for AGI-candidacy

A real intelligence does not only *answer* or *refuse*. It can say, distinctly and
truthfully: *I know this. I think this. I suspect this. I can prove this part. I
cannot prove that part. Here are the assumptions. Here is the risk. Here is what
would settle it.* That is **more** truthful than the binary, not less — the binary
discards true statements about the engine's own knowledge state by collapsing them
into silence. It sits under the telos ([[project-core-is-one-continuous-life]]): a
continuously-learning life that *thinks with* its operator must share in-progress
thought honestly, not only ratified conclusions.

---

## Amendment 2026-06-08 — reconcile with ADR-0206 + `epistemic_state` (do NOT build parallel substrate)

A review of this note against the tree at `main` found it **under-references the substrate that
already ships the serving half of this design.** The *doctrine* above stands; the *naming and the
build plan* must reuse existing organs, not fork parallel ones (CLAUDE.md: reuse over reinvention;
[[feedback-adr-cross-reference-discipline]]). Three bindings:

1. **`ServabilityDecision` / `ServabilityBlade` ⇒ advance ADR-0206 `core/response_governance/`, not
   a new object.** [ADR-0206](../decisions/ADR-0206-response-governance-bridge.md) (the
   Response-Governance Bridge) already ships `ReachPolicy`, `govern_response`, and `shape_surface`,
   with `ReachLevel = STRICT < APPROXIMATE < EXTRAPOLATE < CREATIVE` and disclosure prefixes
   (`shape_surface` already emits `[approximate]`). It is gated **STRICT-only** today
   (`govern_response` returns `STRICT_POLICY`; `shape_surface` is the identity at STRICT) — which is
   *precisely* "the answer/refuse binary is the strict end of a spectrum" (§5). The SRV modes map
   onto `ReachLevel`; the SRV `risk → strictness` table is the policy ADR-0206 explicitly left as the
   future bridge. **Build SRV as the activation of that seam** — produce a widening `ReachLevel`
   under the reliability-gate license — not as a parallel `ServabilityDecision`.

2. **The `epistemic_state` Literals (§4/§5) ⇒ reuse `core.epistemic_state.EpistemicState`.** That
   ratified enum already carries the richer taxonomy (`DECODED`, `EVIDENCED_INCOMPLETE`, `INFERRED`,
   `UNVERIFIED_POSSIBLE`/`NOVEL`, `CONTRADICTED`, `AMBIGUOUS`, `UNDETERMINED`, … + reserved
   `VERIFIED`, `SCOPE_BOUNDARY`, `COMPUTATIONALLY_BOUNDED`, …), and `response_governance/policy.py`
   already partitions it into ACTIVE / RESERVED / RECONCILE. The six-value Literal drafted in §4/§5
   is a parallel, smaller rename — **drop it and import the enum**; do not commit a new closed vocab
   ([[feedback-defer-substrate-vocab-commitment]]).

3. **`ProblemAttemptSession` ⇒ extend `core/comprehension_attempt/`, don't fork.** §4 already names
   this as the home; make it **binding**: firm up `ComprehensionAttempt`'s evidence shape rather than
   adding a parallel dataclass — and only extend the existing type, never shadow it.

**First activation, already scoped.** The natural first widening past STRICT is the reserved
`VERIFIED` state via a canonical-comparison pass —
[`VERIFIED-canonical-comparison-scoping-2026-06-06`](../analysis/VERIFIED-canonical-comparison-scoping-2026-06-06.md)
+ ADR-0206 (`VERIFIED` is the only state that licenses widening past gold). The disciplined loop:
**produce one reserved state → consume it through `govern_response`/`shape_surface` → prove the
served mode on the capability-index yardstick → keep `sealed_eval` verified/refuse → repeat.** One
state at a time, no bulk taxonomy expansion, no parallel policy object.

> **Why the amendment, not a rewrite:** this is a session/research-trail doc; the original reasoning
> is preserved intact above. The fault was a *missing cross-reference*, not a wrong idea — the
> bindings here are what keep the next agent from building `ServabilityDecision`/`PRA` beside
> ADR-0206 instead of inside it.

## Decision & sequencing

- **Decided (doctrine, not yet ADR):** `wrong=0` ≡ **no false presentation of
  epistemic status** — a disclosure discipline. Serving becomes graded controlled
  disclosure; the answer/refuse binary is retained verbatim only at the strict end
  (`sealed_eval` / `safety_critical`). **This is the ADR-0206 `ReachLevel` spectrum,
  gated STRICT today** — see the Amendment.
- **Decided:** typed + isolated candidate guesses are admissible at **practice
  time** (they already are, via the sealed lane + CMB; we are naming the law).
- **Proposed:** `ProblemAttemptSession` (PRA) as the practice-lane evidence
  object; `ServabilityDecision` (SRV) as the serving-lane policy object.
- **Sequencing (do not invert): PRA → REL → SRV.** The blade consumes candidate
  evidence, so it cannot precede the attempt layer. Data models may be drafted now
  (above); wiring waits.
- **Preserved / not touched:** the wrong=0 verify gate, determinism/replay, the
  fail-closed safety/refusal path. The blade *consumes* these; it never weakens
  them. Any future wiring PR bundles `docs/runtime_contracts.md` + contract-test
  updates (the surface contract changes shape), and gives the `context → admissible
  modes` table a meaningfully-failing test per branch (per the
  schema-defined-proof-obligation rule in CLAUDE.md).

## Open / next

**Immediate (capability rung, unrelated to this doctrine — finish first):** the CMB ladder —
**CMB-b** (exact solver, landed), **CMB-c** (reader), **CMB-d** (router/contemplation wiring),
**CMB-e** (ledger) — plus the **R3-vac** oracle patch (port `_canonical_outcome` non-vacuous
validation to `evals/rate_oracle`). None of these touch serving or this doctrine.

**Then (this doctrine, as ADR-0206 activation — per the Amendment, reuse don't reinvent):**

- **PRA** — firm the attempt evidence shape **on `core/comprehension_attempt/`** (extend
  `ComprehensionAttempt`: verified + eliminated candidates + residual ambiguity), reusing
  `core.epistemic_state.EpistemicState`. Not a new parallel dataclass.
- **REL** — relevance / distractor grounding so `confidence_basis` is grounded, not asserted —
  consolidating the grounding that already exists (R2 referent guard, R1 distractor refusal,
  derivation `verify.py`, `epistemic_state_for_grounding_source`), not a greenfield organ.
- **SRV** — **activate the ADR-0206 seam**: produce the reserved `VERIFIED` state (canonical
  comparison, scoping doc above) and let `govern_response`/`shape_surface` emit one widened
  `ReachLevel` for one measured case. Wire through the existing `shape_surface` (already the
  realizer-facing seam); unify `refuse_*` / `contradiction_report` under the existing refusal
  taxonomy. **Not** a parallel `ServabilityDecision`/blade.
- **Yardstick gate (non-negotiable):** every widening shows a capability-index delta before it
  counts ([[milestone-agi-spine-A-to-E-complete]] discipline); `sealed_eval` stays verified/refuse.
- **(Optional) second scorecard** — measure `over_refusal` / `mode_misclassification` as truthful-
  but-suboptimal, distinct from `wrong`, so over-refusal becomes visible debt. Must never alter
  sealed-eval scoring.
- **ADR** — promote to an ADR (likely an **ADR-0206 amendment**, not a new ADR) *only* once a
  reserved state is produced, consumed through `govern_response`, and the `risk → ReachLevel`
  mapping is a closed, tested contract.
