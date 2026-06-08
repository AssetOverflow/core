# Stage 2 — the Epistemic Disclosure Bus (VERIFIED v1) — scoping

**Date:** 2026-06-08 · **Status:** scoping (NO CODE) · **HOLD for review** ·
**Branch:** `docs/stage2-bus-and-q1-scoping`

**Pivot this doc records.** The comprehension-organ ladder (R1→R4, all merged and
frozen — [[combined-rate-capability-ledger-2026-06-08]]) answered *"what can CORE
comprehend off-serving?"* Stage 2 turns to a different question:

```text
What may CORE disclose through the served surface — and under what governed disposition?
```

This is a **scoping document for an implementation frontier**, not the
implementation. It defines the bus, names VERIFIED as the only tenant built in
v1, reserves the future tenants so the bus is not designed too narrowly, and —
most importantly — records the one honest constraint that already killed a
naive version of this work, so v1 does not revive a dead path.

> Companion brief: [[q1-epistemic-question-articulation-v1-scoping-2026-06-08]]
> (the `ASK` tenant, scoped now so the bus reserves a seat for it). Off-serving
> mirror / design-of-record: the session doc
> `docs/sessions/2026-06-08-epistemic-question-articulation-first-skill-of-contemplation.md`
> §1.5 (the pre-question limitation pass / intake gate).

---

## 0. Why a *bus*, not a *VERIFIED feature*

The earlier framing ("build the VERIFIED producer and widen math serving") is
correct but too small. VERIFIED is one **disposition** of one general machine.
The machine is:

```text
EpistemicState + LimitationAssessment  →  ServedDisposition
        (what is true)  (what is blocking)     (what reaches the user, and how)
```

The same machine that decides *"this answer is VERIFIED → disclose it at a wider
reach"* also decides *"this is missing information → ASK a question"*, *"this is a
capability gap → emit a PROPOSAL"*, *"this is out of scope → disclose the SCOPE
BOUNDARY"*, *"this contradicts the supplied key → REPORT it"*. If we build a
bespoke VERIFIED path, the question organ (Doc 2) and every later disposition have
to re-derive the same served-surface governance. So Stage 2 builds the **bus**
and lights up **one** tenant.

This is not new infrastructure invented here. The bus *is* ADR-0206's
`govern_response` / `shape_surface` seam, already wired into serving and already
inert at the math end (§2). Stage 2 = **add a VERIFIED reach to the seam that
exists**, behind a kill-switch, gated by a validate-first probe — nothing parallel.

### The two axes

A `ServedDisposition` is a point in a 2-D space, both axes already present in code:

- **DISPOSITION** — *what kind of move* the served surface makes:
  `{ commit, disclose, ask, report, explain, refuse }`.
  These mirror the contemplation terminals and the failure-family policy
  (`must_remain_refused` / `proposal_allowed` / `answer_key_contradiction` /
  `input_shape`) — the bus is a **consolidating view** over them, never a fourth
  taxonomy (see §7 and session-doc §1.5.7).
- **REACH** — *how far past fully-grounded fact* a disclosure may go:
  the existing `core/response_governance/policy.py::ReachLevel`
  `STRICT < APPROXIMATE < EXTRAPOLATE < CREATIVE`.

| | STRICT (today) | APPROXIMATE (Step E, built) | wider (reserved) |
|---|---|---|---|
| **commit** | fully-grounded answer | — | — |
| **disclose** | — | `[approximate]` cognition estimate | VERIFIED math answer **(v1 target)** |
| **ask** | — | — | QUESTION_NEEDED *(reserved — Doc 2)* |
| **report** | contradiction report | — | — |
| **explain** | — | — | SCOPE_BOUNDARY disclosure *(reserved)* |
| **refuse** | typed refusal | typed refusal | typed refusal |

VERIFIED v1 occupies exactly one new cell: **disclose — under a distinct
`[verified]` mode — an answer a comprehension organ produced and an independent
canonical comparison confirmed.** Everything else in the table is either already
shipped (STRICT commit/refuse/report; APPROXIMATE cognition estimate) or reserved.

### A caution on the REACH axis — VERIFIED is a disclosure *claim*, not an approximation

The `DISPOSITION × REACH` framing is right for scoping, but VERIFIED **stretches**
the REACH axis and the design must not paper over it. `ReachLevel` orders responses
by *how far past fully-grounded fact* they speculate (`STRICT < APPROXIMATE <
EXTRAPOLATE < CREATIVE`). VERIFIED is **not more speculative than STRICT** — it is
*more **licensed***: an answer past the strict/gold line that an independent
canonical comparison has confirmed. It is therefore a **disclosed-surface license /
verification claim**, not a point further out on the speculation scale.

> **Decision (locks S2-1 in principle).** VERIFIED is a disclosed-surface license,
> not an approximation. If it is implemented as a `ReachLevel` value for
> compatibility with the existing seam, it **must** carry distinct semantics **and
> distinct disclosure text** from `APPROXIMATE` — never the `[approximate]` prefix.

The principled decomposition separates the two ideas onto their own axes:

```text
Disposition     = commit | disclose | ask | report | explain | refuse
DisclosureClaim = verified | approximate | scope_boundary | question_needed   ← the claim a disclosure makes
ReachLevel      = strict | approximate | extrapolate | creative               ← how far past fact it reaches
```

`DisclosureClaim` is the new idea VERIFIED really introduces; "verified" is a claim
about *verification status*, not a reach. For **v1 the smallest coherent
implementation** may collapse this into a distinct `ReachLevel.VERIFIED` (so the
existing `policy.py` / `shape_surface` seam carries it without a new axis) — that is
acceptable **provided** it gets its own admissible-set, rationale, and `[verified]`
prefix. The exact enum shape (distinct `ReachLevel.VERIFIED` vs. a separate
`DisclosureClaim` axis) is the one remaining S2-A choice; the *principle* —
distinct from APPROXIMATE — is settled here.

---

## 1. The 8 serving questions (the scoping agenda)

The pivot question above decomposes into eight. This doc commits to answering all
eight for VERIFIED v1; the reserved tenants answer them later, on the same bus.

> These are reconstructed from the design discussion (the verbal agenda was lost
> to compaction). They are the doc's contract; correct/extend on review.

- **SQ-1. What is the unit of disclosure governance?** A per-response
  `ServedDisposition = (DISPOSITION, REACH, disclosed_surface?)`, produced by the
  bus from `(EpistemicState, LimitationAssessment, license/verification evidence)`.
- **SQ-2. What states may be disclosed, and at what reach?** The DISPOSITION×REACH
  matrix above. v1 adds exactly one cell (VERIFIED → disclose).
- **SQ-3. What earns the right to widen past STRICT/gold?** *Only* `VERIFIED`, and
  only via a **canonical-comparison proof of correctness** — not a statistical
  license, not gold agreement (§3). VERIFIED is "the only state that will license
  widening past gold" (ADR-0206 §4; `policy.py` RESERVED_STATES comment).
- **SQ-4. How is the producer's independence guaranteed?** Independence must live
  in the **reading**, not the solving (§3.2). This is the lesson that killed the
  fold-reader path and the reason R1–R4 organs are the unblock.
- **SQ-5. How is a widened answer presented?** Via the existing `shape_surface`:
  STRICT is identity (verbatim commit); a wider mode surfaces a **disclosed**
  alternative with a prefix. VERIFIED v1 discloses under its **own distinct
  `[verified]` mode** — never the `[approximate]` prefix, and never a silent
  overwrite of the STRICT surface (§0 caution, §4).
- **SQ-6. What is the blast radius / kill-switch?** A new default-`False`
  `RuntimeConfig.verified_serving_enabled`, sibling to `estimation_enabled`
  (§5). Off ⇒ byte-identical to today.
- **SQ-7. How do we prove no regression?** A **validate-first holdout probe**
  (INV-25 discipline) runs *before* any widening is built; the sealed GSM8K lanes
  and pinned SHAs stay untouched and must show wrong=0 preserved (§6).
- **SQ-8. How do we measure that widening *helped*?** Extend the
  `evals/capability_index/` yardstick with a served-usefulness scorecard
  `{wrong, over_refusal, mode_misclassification}` — wrong=0 alone proves we did no
  harm; it does not prove we did any good (§8).

The implementation sub-questions S2-0..S2-6 (§9) and the build order S2-A..D (§10)
operationalise these.

---

## 2. Substrate — what is already built (do not re-research, do not rebuild)

The disclosure machine is **far more built than the headline suggests**, and the
math end is **wired but deliberately inert**. Verified against the tree on this
branch:

- **`core/response_governance/policy.py`** — `ReachLevel` (4 levels),
  `ReachPolicy` (frozen: `level`, `admissible_states`, `rationale`,
  `license_ratio`), `govern_response(*, epistemic_state, license_decision,
  stakes) -> ReachPolicy`, `shape_surface(policy, *, committed_surface,
  decode_state, disclosed_alternative=None) -> str`. STRICT path of
  `shape_surface` is the **identity transform**; the wider branch prepends a
  `_DISCLOSURE_PREFIX` to a *disclosed alternative*. `STRICT_POLICY` and
  `APPROXIMATE_POLICY` both admit only `{DECODED}` (APPROXIMATE keeps the same
  admissible set on purpose — a less-grounded state is *disclosed*, never
  committed). This is **live wiring**, not dead code.
- **`core/epistemic_state.py`** — `EpistemicState` (15 members). `VERIFIED =
  "verified"` is a **RESERVED** state today; `policy.py::RESERVED_STATES`
  documents the unlock: *"needs canonical-comparison pass (soundness != correctness);
  the ONLY state that will license widening past gold."*
- **Cognition end is ALREADY widened (Step E / ADR-0206 §5).**
  `govern_response` returns `APPROXIMATE_POLICY` iff a genuine licensed
  `Action.SERVE` `LicenseDecision` is passed; the converse-guess estimate then
  rides `shape_surface` out as a disclosed `[approximate]`. Gated by
  `RuntimeConfig.estimation_enabled = False` (`core/config.py:336`). **This is the
  exact pattern VERIFIED v1 copies** — different producer, same bus, same
  kill-switch shape.
- **Math end is wired and INERT.** `generate/derivation/verify.py`:
  `select_self_verified(..., policy=...)` (line 208) takes a `ReachPolicy`; a
  wider reach may resolve a disagreement STRICT refuses **only** via
  `_canonically_verified(...)` (line 188) — which **`return None` today**. So the
  widening is *structurally* inert: disagreement refuses regardless of `policy`,
  and the absolute math `wrong == 0` holds **by construction, not convention**.
  This `None` is the precise, tested integration point a VERIFIED producer plugs
  into.
- **Yardstick** — `evals/capability_index/index.py`: `DomainResult{correct,
  wrong, refused}` with `coverage`/`accuracy`; `CapabilityIndex` hard-gates
  `capability_score` to 0 on any `wrong` (`assert_mode_valid`). The served-
  usefulness scorecard extends this, it does not replace it.

**Consequence.** Stage 2 v1 is not "build a disclosure system." It is: write a
**VERIFIED producer**, wire it into the one `return None`, add a kill-switch and a
yardstick column, and prove it on a holdout *before* flipping the switch. The bus
already exists.

---

## 3. The VERIFIED producer — the one hard part, and its honest constraint

### 3.1 The dead-path constraint (read before designing anything)

There is a **load-bearing prior result** that v1 must not contradict:
[[VERIFIED-canonical-comparison-scoping-2026-06-06]] already **killed**, with a
validate-first probe and *before any build*, the obvious VERIFIED producer — a
certifier over the existing GSM8K fold/derivation readers:

- The serving `verify` is **solver-replay soundness**, not correctness — it proves
  the solver executed the graph faithfully, not that the *parse* is right.
- No independent second reader helped: the R1 graph reader is **nested** in
  candidate-graph (`0/44` complementary coverage on the refused set), and the one
  genuinely complementary reader (fold-derivation) is **~98% wrong** on the
  refused set (`2 correct / 87 WRONG` on holdout_dev). A certifier strict enough
  to reject the 87 rejects the 2 too — the mis-reads carry no shallow structural
  signature, because *separating them is the comprehension problem itself*.
- **Verdict:** "Math serving is comprehension-bound… Re-open **only** if a
  genuinely complementary, independently-validated reader lands."

**That reader has now landed.** R1–R4 are exactly "genuinely complementary,
independently-validated readers": each carries its **own** `_canonical_outcome`
gold oracle, disjoint from the GSM8K candidate-graph path (off-serving, AST-checked
to import no `generate.derivation` / `core.reliability_gate`). So the dead-path
verdict does not block VERIFIED v1 — **it scopes it.** v1's VERIFIED producer is a
comprehension-organ answer, *not* a GSM8K-fold-reader certifier. The dead path
stays dead; we walk a different, narrower one.

### 3.2 Independence must be in the READING, not the solving

The single most important design lesson, and the one most easily violated:

> Back-substitution / constraint re-checking catches **solve** errors. It does
> **not** catch **read** errors. If the reader mis-parsed the problem, the
> candidate answer can satisfy the (wrongly-read) constraints perfectly and still
> be wrong. A second *solver* over one *reading* is **fake** independence.

So VERIFIED for a comprehension-organ answer requires **two** things, and the first
is the one that carries wrong=0:

1. **A conservative reader that refuses on doubt** (R2/R4 already do this: they
   step aside or refuse on anything not cleanly in-shape). wrong=0 lives here.
2. **A canonical-comparison check** layered on top: an *independent* re-derivation
   to canonical normal form **plus** back-substitution of the candidate into the
   problem's *stated* quantities — and **no organ boundary fired**. The check is a
   *necessary pre-filter*, never the sole gate (convergence is evidential, not a
   proof; ADR-0206-scoping §"Candidate mechanisms" item 2).

R2 (finite-integer constraint satisfaction) is the **cleanest first class**: a
solved count must satisfy the stated total/weighted constraints exactly —
back-substitution is a genuine correctness check against the problem's own
structure, with no gold. R4 (combined-rate) is the **second** class. Neither
touches the GSM8K candidate-graph.

### 3.3 What "VERIFIED" must mean (the contract, scoped not built)

`EpistemicState.VERIFIED` is emitted for a candidate answer **iff all** hold:

```text
1. A conservative comprehension organ (R2 first, R4 second) produced the answer
   — i.e. it did NOT refuse / step aside / hit a boundary.
2. An independent canonical re-derivation converges on the same canonical value.
3. Back-substitution into the problem's STATED quantities satisfies every
   constraint exactly (integer-exact; never round).
4. No organ boundary (unit-mismatch, ambiguity, underdetermined, non-integer,
   non-positive-net, over-determined) fired anywhere in the chain.
```

The obligation is **real only if it can meaningfully fail** (CLAUDE.md
"Schema-Defined Proof Obligations"): the v1 contract's first test must be that it
**rejects a sound-but-wrong answer** (the `20/5 == 4`-style class — a faithful
solve of a wrong read). A VERIFIED predicate that passes such a case is decoration,
not proof, and must not be wired to the seam.

---

## 4. How a VERIFIED answer reaches the user — disclose, never silently widen

VERIFIED v1 rides the **existing** `shape_surface`. Two non-negotiables:

- It only ever resolves a case STRICT would **refuse** (a disagreement /
  past-gold case). It never *changes* an answer STRICT already commits.
- It **discloses**. Even when correctness is proven, v1 surfaces the answer through
  the disclosed-alternative path of `shape_surface`, not as an unmarked commit, so
  the served record always shows the reach that produced it. (Whether the
  user-visible prefix is empty for proven-correct answers is an S2-B decision; the
  *plumbing* is the disclosed path regardless.)

The bus contract for v1:

```text
govern_response(epistemic_state=VERIFIED, verification=<canonical-comparison evidence>)
    → ReachPolicy(level=<distinct VERIFIED mode>, admissible_states={DECODED, VERIFIED})
shape_surface(policy, committed_surface=<organ answer>, decode_state=VERIFIED, ...)
    → "[verified] <answer>"        # distinct mode + distinct prefix — NEVER [approximate]
```

**S2-1 decision (settled in this doc, not deferred):**

> **VERIFIED must not reuse `ReachLevel.APPROXIMATE` or the `[approximate]`
> disclosure prefix. VERIFIED receives a distinct disclosed-surface mode/level with
> its own deterministic prefix, e.g. `[verified]`. APPROXIMATE is for bounded
> estimates; VERIFIED is for independently confirmed answers under the
> canonical-comparison contract.**

The two are not neighbours on one scale: `APPROXIMATE` means *"useful but less
certain — disclosed as approximate"*; `VERIFIED` means *"independently confirmed
under the canonical-comparison contract."* Reusing APPROXIMATE's prefix would put a
proven answer behind an "I'm not sure" label — semantically wrong. The only choice
left to S2-A is the **enum shape** (a distinct `ReachLevel.VERIFIED` value, or a
separate `DisclosureClaim` axis per §0); both honour the decision above. A distinct
`ReachLevel.VERIFIED` is the acceptable smallest-coherent v1 **iff** it carries its
own admissible-set, rationale, and `[verified]` prefix.

---

## 5. The kill-switch (blast radius)

Add a sibling to `estimation_enabled`:

```python
# core/config.py, RuntimeConfig
verified_serving_enabled: bool = False
```

- **Off (default).** `govern_response` for math never receives a VERIFIED state;
  `_canonically_verified` keeps returning `None`; every serving call is
  byte-identical to today. The flag's *absence of effect* when off is itself a
  test (the live-wiring discipline `policy.py` already follows).
- **On.** Only the VERIFIED producer's narrow class can widen, and only via
  disclosure. wrong=0 is still structural: the producer returns a derivation or
  `None`, and `None` still refuses.

No flag flips in this batch (scoping only). The flag lands with S2-C and is
**not** turned on in production until S2-D's holdout passes.

---

## 6. Proving no regression — validate-first, sealed lanes untouched

This is the wrong=0 discipline made concrete, and it is **ordered before the build**:

1. **Validate-first holdout probe (S2-D-pre, runs BEFORE widening is wired).**
   Mirroring the 2026-06-06 probe that killed the fold-reader path: run the VERIFIED
   producer (R2 first) over an **independent holdout gold lane** (INV-25 discipline —
   gold from a *separate* oracle than the one the producer uses internally) and
   confirm `wrong == 0` on the *widened* set. If the probe shows any wrong, the
   producer is not buildable at wrong=0 for that class — **stop**, exactly as the
   fold-reader path stopped. No code-first optimism.
2. **GSM8K seal is untouched.** The candidate-graph serving path, its pinned
   eval-lane SHAs (`scripts/verify_lane_shas.py`), and `CLAIMS.md`
   (`scripts/generate_claims.py --check`) are **not modified by VERIFIED v1**. v1's
   producer is an off-serving organ; it does not import `generate.derivation` /
   `core.reliability_gate`, so it *structurally cannot* move the sealed metric.
3. **Re-pin is a deliberate reviewed act, with the eval delta as truth test.** If
   v1 ever does emit a served `reach_level` on a frozen lane, re-pinning the SHAs is
   an explicit reviewed step; the sealed run must show wrong=0 preserved **and** the
   new served class (ADR-0206-scoping §"Recommended arc" item 4).

---

## 7. Consolidation discipline — the bus is a VIEW, not a 4th taxonomy

Binding constraint inherited from session-doc §1.5.7 and CLAUDE.md ("no parallel
correction/decision paths"):

CORE already encodes served disposition in three overlapping places —

- the **failure-family registry** (`core/comprehension_attempt/failure_family.py`:
  `must_remain_refused` / `proposal_allowed` / `input_shape` / `owner`),
- the **contemplation terminals** (`SOLVED_VERIFIED` / `REFUSED_KNOWN_BOUNDARY` /
  `PROPOSAL_EMITTED` / `CONTRADICTION_DETECTED` / …),
- and the **reach policy** (`ReachLevel` / `admissible_states`).

The bus's `ServedDisposition` must **derive from and unify** these, adding only the
genuinely new disclosure cell (VERIFIED → disclose) — never a fourth source of
truth. Concretely, the DISPOSITION axis maps onto what already ships:

```text
commit   ← STRICT-admissible DECODED answer (today)
disclose ← APPROXIMATE estimate (today) + VERIFIED answer (v1, new)
report   ← answer_key_contradiction terminal
refuse   ← must_remain_refused families / STRICT non-admissible
ask      ← reserved (Doc 2: missing_information / ambiguous_structure)
explain  ← reserved (scope_boundary)
```

If a Stage-2 PR finds itself defining a new enum that re-states the terminal set or
the family policy, that is the smell of a fourth taxonomy — stop and derive instead.

---

## 8. Measuring that widening *helped* (the yardstick extension)

wrong=0 proves v1 did no **harm**. It cannot prove v1 did any **good** — a producer
that emits VERIFIED for *nothing* is trivially wrong=0. So extend
`evals/capability_index/`:

- Keep `DomainResult{correct, wrong, refused}` and the wrong-gated
  `capability_score` exactly as-is (the anti-gaming headline).
- Add a **served-usefulness scorecard** alongside it:
  `{ wrong, over_refusal, mode_misclassification }` —
  - `wrong` — must stay 0 (the hard gate; already enforced).
  - `over_refusal` — cases the VERIFIED producer *could* have correctly disclosed
    but refused (the coverage v1 is buying). Measured against the holdout gold.
  - `mode_misclassification` — cases routed to the wrong disposition (disclosed
    when it should have refused/asked, or vice-versa). This is the bus-level
    analogue of the intake-gate failure modes in session-doc §1.5.1.
- **Sealed-eval scoring is UNCHANGED.** The scorecard is a *new* lane over the
  organ holdouts; it does not touch the GSM8K sealed report or its digest.

The headline v1 success metric is: **`over_refusal` on the R2 (then R4) class drops,
`wrong` stays 0, `mode_misclassification` stays 0.**

---

## 9. The implementation sub-questions (S2-0..S2-6)

To be answered by the S2-A..D PRs, not here:

- **S2-0. Contract.** Exact `ServedDisposition` dataclass + the VERIFIED predicate
  signature, with the meaningful-fail test (rejects sound-but-wrong) written first.
- **S2-1. Reach. (SETTLED in §0/§4 — distinct from APPROXIMATE.)** VERIFIED gets a
  distinct disclosed-surface mode and a distinct `[verified]` prefix, never
  `[approximate]`. The only S2-A choice left is the **enum shape**: a distinct
  `ReachLevel.VERIFIED` value vs. a separate `DisclosureClaim` axis — both must carry
  their own admissible-set, rationale, and prefix.
- **S2-2. Producer class order.** R2 constraint-satisfaction first; R4 second;
  nothing else in v1.
- **S2-3. Independence proof.** How the canonical re-derivation is made provably
  *reading-independent*, not just a second solver over one reading (§3.2).
- **S2-4. Kill-switch + wiring.** `verified_serving_enabled`; the `None` →
  producer wiring at `verify.py:188`; off-by-default byte-identity test.
- **S2-5. Holdout probe.** The INV-25 validate-first lane; gold from a separate
  oracle; run **before** S2-C wires anything live.
- **S2-6. Yardstick.** The served-usefulness scorecard lane (§8); sealed scoring
  untouched.

---

## 10. Build order (S2-A..D) — each its own wrong=0-gated PR

1. **S2-A — Contract + meaningful-fail test (no producer).** Define the VERIFIED
   predicate's obligation and the `ServedDisposition`/reach decision; ship the test
   that rejects a sound-but-wrong answer. No serving change.
2. **S2-B — VERIFIED producer for the R2 class (off-serving).** Canonical
   re-derivation + back-substitution + boundary-clear check, emitting
   `EpistemicState.VERIFIED`. Still not wired to serving.
3. **S2-C — Wire + kill-switch.** Replace the `verify.py:188` `return None` with a
   call to the producer guarded by `verified_serving_enabled` (default off); add
   the off-by-default byte-identity test. Flag stays off.
4. **S2-D — Validate-first holdout, then (only if green) flip.** Run the INV-25
   probe (§6 item 1); if `wrong == 0` on the widened set holds, enable the flag for
   the R2 class and add the served-usefulness scorecard. If not green, the producer
   is not buildable at wrong=0 for that class — record and stop, as the fold-reader
   path was stopped.

R4 repeats S2-B..D as a follow-on once R2 is proven end-to-end.

---

## 11. What VERIFIED v1 is NOT (non-claims)

- **Not** a re-opening of the GSM8K fold-reader certifier (dead per §3.1).
- **Not** a statistical/Wilson license substituting for proof — math serving is
  absolute wrong=0, not disclosed-estimate like the cognition path (the
  `_canonically_verified` docstring forbids this explicitly).
- **Not** a reuse of `APPROXIMATE` — VERIFIED carries its own distinct disclosure
  mode and `[verified]` prefix; a proven answer never wears the `[approximate]`
  label (§0 caution, §4 S2-1 decision).
- **Not** the ASK / PROPOSE / REPORT / SCOPE tenants — those are **reserved** seats
  on the bus, built later (Doc 2 is the ASK scope). The intake-gate excitement
  (session-doc §1.5) must **not** widen v1: ASK is a future tenant, not Stage 2 v1.
- **Not** a change to the sealed GSM8K serving metric, pinned SHAs, or `CLAIMS.md`.
- **Not** a fourth disposition taxonomy — it is a consolidating view (§7).
- **Not** a flag flipped in this batch. This doc is scoping; no code, HOLD for review.

---

## 12. Verification lanes (when built)

- `core test --suite full -q` — VERIFIED contract + meaningful-fail (S2-A),
  off-by-default byte-identity (S2-C).
- The new served-usefulness scorecard lane over the R2/R4 organ holdouts (S2-D).
- `scripts/verify_lane_shas.py` + `scripts/generate_claims.py --check` — must stay
  **green and unchanged** through S2-A..C (proof the seal is untouched).
- The INV-25 validate-first holdout probe (S2-D) — the go/no-go gate.

> **Stop boundary.** This document is scoping. No code lands until review approves
> the agenda and the S2-A..D order. The companion Q1 brief
> ([[q1-epistemic-question-articulation-v1-scoping-2026-06-08]]) reserves the ASK
> seat on this bus; it, too, is scoping-only.
