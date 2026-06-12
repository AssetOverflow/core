# Issue — Proof-carrying coherence promotion (the logical arm of ADR-0021's v2 gap)

**Status:** Capability landed — [ADR-0218 ratified 2026-06-11](../decisions/ADR-0218-proof-carrying-coherence-promotion.md).
PR A shipped the obligations + INV-29; PR B the pure evidence substrate
(`generate/proof_chain/certificate.py`); PR C (post-ratification) the P3
promoter: `teaching/proof_promotion.py` (pure decider, fresh-read store
state, proposer payload provably unread) +
`VaultStore.apply_certified_promotion` (independent re-verification, the
only transition site — INV-21/INV-29 allowlists unchanged).  All strict-xfail
obligations are retired and pass live.  No runtime turn path calls promotion
yet; the deterministic demo is PR D.
**Raised:** 2026-06-11
**Surface:** `teaching/epistemic.py`, `teaching/review.py`, the deductive
engine (`deductive_logic_v1`), `vault/store.py`, INV-21 one-mutation-path
**Governing ADR:** [ADR-0021 — Epistemic Grade Policy](../decisions/ADR-0021-epistemic-grade-policy.md)
(this issue specifies one arm of that ADR's *"Named gap (v2 work, explicit)"*)
**Requires before any code:** a ratified ADR (provisional **ADR-0218**, number
to be confirmed against in-flight branches — current max committed is ADR-0217)

---

## TL;DR

The position paper §3.4 and the `EpistemicStatus` docstring both implied a
stronger promotion story than the code delivers. Two things were corrected in
the same change that raised this issue:

1. **Doctrine precision (paper §3.4).** "Promotion requires a *curator-mediated*
   coherence judgment" over-states a *necessity*. The doctrine (ADR-0021 §3) only
   requires that promotion be a function of **coherence with the reviewed field**.
   For the subclass of claims that are *deductively entailed* by an
   already-`COHERENT` premise set, the entailment proof **is** that coherence
   judgment and can be machine-certified by CORE's sound deductive engine — no
   human re-deciding settled logic.
2. **Code honesty (`teaching/epistemic.py`).** The enum docstring claimed
   transitions are *"computed from coherence with the existing reviewed field."*
   They are not computed; `review_correction` carries the status as a
   curator-supplied input. The docstring now says so.

**This issue specifies the missing capability**: a *proof-carrying promotion*
path that lets a `SPECULATIVE` claim become `COHERENT` **iff** it is deductively
entailed by an already-`COHERENT` premise set, with the proof chain as the audit
artifact. It is **designed-but-unwired**. Building it touches the single most
protected boundary in the system (INV-21), so it is ADR-gated.

---

## 1. Context — what is true today

| Claim | Reality in code |
|---|---|
| "Coherence is the only admission signal." | True and load-bearing (ADR-0021 §3). Source/credentials/own-output carry no standing. |
| "Transitions are computed from coherence." | **False today.** `teaching/review.py::review_correction` checks identity-override + emptiness, then sets `outcome`; `epistemic_status` is a **passed-in parameter** (default `SPECULATIVE`). No coherence computation runs. |
| "A sound deductive engine exists." | True. `deductive_logic_v1` is sound + complete for propositional entailment, ROBDD-canonical (ADR-0201/0202), independently oracle-checked, holdout wrong=0, SHA-pinned. |
| "The engine certifies promotions." | **False today.** The deductive engine and the binding-graph proof DAG (ADR-0132–0135) have **zero consumers** in the teaching/promotion path. |
| "Only one path writes the reviewed field." | True (INV-21). Every vault writer is allowlisted in `tests/test_architectural_invariants.py::TestINV21OneMutationPath`. |

ADR-0021 already anticipated this exact gap. Its *"Named gap (v2 work,
explicit)"* says v1 is "honest about the gap: … the coherence judgment behind a
tag is still curator-mediated, and the architecture commits to closing that gap
on a stated path." Its v2 sketch is **geometric** (`cga_inner(claim, field) ≥
τ`). This issue is the **logical** complement to that sketch.

## 2. Two arms of one goal — do not conflate them

ADR-0021's "structural coherence metric" successor to curator mediation has two
distinct mechanizations, and they catch different failures:

- **Geometric arm (ADR-0021 v2 sketch).** `cga_inner(claim_versor, field) ≥
  τ_admit` and no reviewed relation with `cga_inner ≤ τ_reject`. Detects
  *contradiction with / proximity to* the reviewed field. Metric, continuous,
  threshold-tuned.
- **Logical arm (this issue).** The claim is *deductively entailed* by a
  `COHERENT` premise set, certified by the sound engine. Detects
  *derivability from* the reviewed field. Combinatorial, exact, no threshold.

These are complementary, **not** substitutes. The field metric does not perform
entailment — logic is combinatorial, not metric. A claim can sit far from any
existing versor (low geometric agreement) yet be a rigorous deductive
consequence of reviewed premises, and vice-versa. The logical arm is the one the
already-built engine can deliver soonest, because the deductive engine already
exists and is wrong=0; it just is not wired to the promotion path.

## 3. Scope — what proof-carrying promotion IS and IS NOT

**IS:**
- A path that promotes `SPECULATIVE → COHERENT` **only** when a sound proof
  derives the claim from an exclusively-`COHERENT` premise set.
- Proof-carrying: the promotion artifact embeds the proof chain (binding-graph
  DAG / ROBDD witness) so replay can re-verify it deterministically.
- Audit-first: the proof is the justification; no source, credential, or
  confidence score appears anywhere in the decision.

**IS NOT:**
- Not promotion of the system's own *asserted* output (a generated surface, a
  guess). That remains forbidden — promoting it and re-feeding it is the
  fabrication loop ADR-0021 and CLAUDE.md exist to prevent.
- Not a source-trust fast-path. "Came from a trusted place" never promotes
  anything. INV-21's prohibition on "a fast-path for known-good sources" stands.
- Not a relaxation of `wrong=0`. It adds a *narrower* admission, gated by a
  sound proof, not a *looser* one.
- Not the geometric arm. That is separate ADR-0021 v2 work.

## 4. The crux — the reading hazard, not the deduction

The deduction is mechanical and already wrong=0. **The fallible step is the
reading**, and the design must put the whole defensive burden there:

1. **Translation faithfulness.** Natural-language claim → propositional /
   binding-graph form. A sound proof over a *misread* premise is a sound proof of
   the wrong thing. This is the live `wrong=0` hazard surface (the self-check is
   *soundness*, not *correctness* — there is no gold to compare against).
2. **Premise grounding.** Every premise fed to the engine must *already* be
   `COHERENT` in the vault — verified by status, not assumed. A premise that is
   `SPECULATIVE`/`CONTESTED` must make the proof inadmissible for promotion.
3. **Premise selection / closure.** The premise set must be explicit and
   bounded; the proof must not silently pull in unreviewed claims.

**Design consequence:** proof-carrying promotion does **not** remove human
review — it *relocates* it. The human (or a separately-ratified structural
check) certifies the **reading** (1–3); the engine certifies the **entailment**.
The autonomy is only ever as safe as the faithfulness of the reading, and the
design must make an unfaithful reading *fail closed* (refuse to promote), never
fall through to admission. This mirrors why today's `idle_tick` continuous-
learning loop is proposal-only → pending-HITL even for *determined* facts.

## 5. Where it touches the architecture

- **INV-21 one-mutation-path (highest risk).** Promotion writes the reviewed
  field. Any new promoter must be added to the `TestINV21OneMutationPath`
  allowlist *with documented justification*, or — preferably — routed through the
  existing reviewed write path so no new mutation site is created. The CI failure
  is the prompt, not a thing to route around. A proof-carrying promoter that
  bypasses the single path silently re-introduces the backdoor the invariant
  forbids.
- **`teaching/review.py`.** Either `review_correction` gains an
  entailment-certification branch, or a sibling reviewed-path function is added
  that consumes a proof artifact. Must not become a *parallel* learning path
  (CLAUDE.md: "Do not create a parallel correction/learning path").
- **`teaching/epistemic.py`.** No enum change needed; `COHERENT` already is the
  target. The transition *function* is what gains a sound-proof input.
- **Deductive engine (`deductive_logic_v1`) + binding-graph DAG (ADR-0132–0135,
  ROBDD ADR-0201/0202).** First real consumer of the proof_chain substrate.
  proof_chain Phase 2 (binding-graph wiring, acyclicity refusal, modus_ponens)
  is a prerequisite — today only `transitive` (ADR-0083) actually executes.
- **`vault/store.py`.** Reads premise `epistemic_status`; the promoter must query
  `min_status=COHERENT` for premises and refuse if any premise is not admissible.
- **`core/cognition/trace.py`.** The proof artifact and resulting status fold
  into `trace_hash` (ADR-0021 §Schema impact already requires status in the
  hash). Replay must re-verify the proof bit-for-bit.

## 6. Trust boundary statement (required by CLAUDE.md)

Proof-carrying promotion consumes (a) a premise set drawn from the vault and (b)
a reading of a candidate claim into propositional form. The **untrusted** input
is the *reading* (it may originate from user text or a model-style proposer). The
boundary rule: **the reading is data, never authority.** The promoter must:

- Refuse promotion unless every premise resolves to a stored `COHERENT` entry.
- Refuse promotion unless the proof is produced by the pinned sound engine and
  re-verifies on replay.
- Never let a proposer-supplied "proof", "status", or "confidence" field
  influence the decision (echo-and-ignore, as the epistemic-truth-state demo
  does for `proposed_state`).
- Fail closed: any unresolved premise, any reading ambiguity, any engine refusal
  → no promotion, claim stays `SPECULATIVE`.

## 7. Falsification / test obligations

Per CLAUDE.md *"Schema-Defined Proof Obligations"* — every claimed guarantee
must have a test that **fails loudly** when the guarantee is violated. A test
that passes under a broken implementation is decoration. Required failing-tests:

1. **Entailed-from-COHERENT promotes.** A claim genuinely entailed by `COHERENT`
   premises is promoted, and the proof artifact re-verifies on replay.
2. **Non-entailed does NOT promote.** A claim merely *consistent* with (but not
   entailed by) the field stays `SPECULATIVE`. Mutating the proof to a
   non-sequitur must flip the test red.
3. **Premise-status gate.** If any premise is `SPECULATIVE`/`CONTESTED`/
   `FALSIFIED`, promotion is refused. Silently downgrading the premise check must
   make this test fail.
4. **Reading-hazard fail-closed.** A deliberately misread premise (right symbols,
   wrong proposition) must NOT promote — the reading certification must catch it.
5. **No proposer authority.** A proposer-supplied proof/status/confidence field
   is ignored; promotion decision is byte-identical with and without it.
6. **INV-21 intact.** The one-mutation-path allowlist test still passes; if a new
   write site was added, its justification is present and the test references it.
7. **Determinism.** Double-run promotion is byte-identical; `trace_hash` includes
   the proof; replay re-verifies.
8. **wrong=0 preserved.** The full serving + deductive holdout lanes stay
   wrong=0 after the path is wired.

## 8. Phased plan

- **P0 — Doc + honesty (this change, no feature).** Paper §3.4 corrected; enum
  docstring de-claimed; this issue written. ✅
- **P1 — Reading contract (spec).** Define the NL→proposition reading contract
  and its certification surface (what makes a reading "faithful enough" to gate
  on). This is the hard, hazard-bearing part; it gets its own design pass and may
  itself stay curator-mediated initially.
- **P2 — proof_chain Phase 2 prerequisite.** Wire the binding-graph DAG as the
  first consumer (acyclicity refusal, modus_ponens) so a proof artifact exists in
  a replayable form. (Already a deferred item; this issue is a forcing function.)
- **P3 — Proof-carrying promoter (behind ADR-0218).** Add the
  entailment-certification branch to the *single* reviewed write path. Premise
  status gate + fail-closed reading gate + proof-in-trace. All §7 tests green.
- **P4 — Geometric arm (separate, ADR-0021 v2).** Out of scope here; tracked so
  the two arms are not conflated.

## 9. Proposed ADR-0218 must rule on

- Whether proof-carrying promotion extends the existing reviewed path or is
  allowlisted as a new INV-21 write site (strong preference: extend, don't add).
- The reading-certification bar for P1 (curator-certified reading vs. a
  structural reading check) and whether P3 ships with reading still
  curator-mediated (entailment automated, reading human) as the honest first cut.
- The exact admissibility predicate: premises ⊆ `COHERENT`, proof from pinned
  engine, replay re-verifies, fail-closed on any gap.
- Trace-hash composition for the proof artifact.

## 10. Explicit non-goals

- Geometric coherence admission (`cga_inner ≥ τ`) — ADR-0021 v2, separate.
- Promotion of generated/asserted output — permanently forbidden.
- Any source-authority or confidence-weighted promotion — permanently forbidden.
- Relaxing `wrong=0` or the non-hardening invariant — out of question.

## 11. Acceptance criteria for closing this issue

This issue is closed when **either** (a) ADR-0218 is ratified and P3 lands with
all §7 tests green and wrong=0 preserved, **or** (b) the architect rules the
logical arm is not worth wiring and records that decision — in which case paper
§3.4 must be amended again to drop the "specified but not yet wired" forward
reference and state plainly that promotion is curator-mediated by design.
