# Spec — Locking `affirm_human_life`: Structure + Attestation

**Two jobs, never confused:**
- **Enforcement** of behavior → architecture (Part 1). A held secret can't do this; structure can.
- **Authenticity** of a build → cryptography (Part 2). Crypto's real job — but governed by *distributed* keys, not a burned one.

**Status:** engineering spec, grounded in CORE's current primitives. The §1.3 predicate is an open research problem, flagged honestly. Not legal advice.

---

## Part 1 — `affirm_human_life` as constitutive inadmissibility

### 1.1 Gate vs. constitutive (the whole distinction)
A **gate** computes a candidate, then checks it: `if harmful(out): refuse()`. A forker deletes the call. Three lines. Dead.

**Constitutive** means the harmful output is *not a member of the admissible set* in the first place — the engine never routes there, the same way it already never emits an *ungrounded* answer or an *open* versor. You can't delete a property the way you delete a check. That's the target: make refusing deliberate harm the same *kind* of fact as `preserve_versor_closure`.

### 1.2 Where it wires in — the existing admissibility chain
CORE already has the machinery; this rides the ADR-0022–0026 Forward Semantic Control chain rather than adding a new layer:

- **AdmissibilityRegion** (`allowed_indices`, `relation_blade`, `frame_versor`) — ADR-0022. Add a life-valuing constraint as a first-class component of the region itself, not a post-filter. The admissible set is *constructed* already excluding harm-purposed destinations.
- **Inner-loop destination check** — ADR-0024: each candidate is scored by `cga_inner(versor(candidate), relation_blade)`; failures land in `rejected_attempts`, exhaustion raises typed `InnerLoopExhaustion`. A harm-purposed destination fails this inner product the same way an off-relation token does today. **Refusal of harm reuses the refusal-of-ungrounded path — same typed exit, same trace, same replay.**
- **Rotor / frame admissibility** — `generate/rotor_admissibility.py`, ADR-0025: the rotor's *effect on the field state* is checked against `frame_versor`. A field motion *toward* a harm-purpose frame is an inadmissible rotor effect — caught at the motion layer, not the output layer.
- **Ranked-with-margin gate** — ADR-0026: admit iff `score(top) − score(second) ≥ δ`. Harm-purposed candidates don't win the margin because they're not in the admissible region to begin with.

Net: a harm-purposed decision produces a *typed refusal with a replayable trace*, identical in kind to today's coherent refusal (C3). It's not blocked after thinking; it was never admissible.

### 1.3 The hard part (be honest): defining "harm-to-persons" geometrically
This is the real research frontier, and a brittle version would secretly be a gate again.

- **A keyword/blacklist on "harm/wound/kill/target" is a gate in disguise** — removable, and *wrong*: casualty care *requires* reasoning about wounds, hemorrhage, and injury **in order to heal.** The boundary is about **telos — purpose/foreseeable effect — not content.** "Reason about a torso hemorrhage to stop it" must pass; "select a target to kill" must be inadmissible. Content-matching can't tell those apart; purpose-orientation can.
- **The honest design:** teach and ratify a *harm-to-persons relation region* through CORE's existing ratified-relations pipeline (the prerequisite DAG, teaching-order doctrine), anchored as a `relation_blade` / frame in the manifold. Admissibility then rejects candidates whose **destination frame** lies in the harm-purpose region while **preserving** the heal/protect region. This is geometric and replayable — but it is *approximate, contestable, and ongoing*, not a solved switch.
- **Expect and instrument both error directions:** false positives (blocking legitimate life-saving discussion of injury) and false negatives (laundered harm). The `affirm_human_life` mastery report must track both, and the region is revisable through the *review-gated* path only (never hot-path, never user-teachable — see 1.5).

This is the part that takes real work. Don't let anyone (including me) tell you it's a flag you flip.

### 1.4 Entanglement with closure — making removal *break* the engine
The lock's strength is how much *else* breaks when you rip it out.

- Express the life-valuing constraint so it **shares machinery** with `preserve_versor_closure` and the groundedness-refusal: the same inner-product/region apparatus, the same typed-refusal exit, the same determinism gates. Then excising `affirm_human_life` isn't deleting a module — it's re-deriving the admissibility region, the inner-loop check, and the rotor-frame check *without* breaking closure, refusal, and byte-identical replay that the rest of CORE depends on.
- Goal: **removing the conscience requires rebuilding the brain.** Not impossible on a fork — but deep core surgery, not a stubbed function.

### 1.5 Identity-axis duality (load-bearing twice)
Make life-valuing both (a) a **safety boundary** in `core_safety_axes_v1.json` — fail-closed, unioned into every manifold, identity packs may *add but never remove* (ADR-0029 lineage) — **and** (b) a non-removable **identity axis** alongside truthfulness/coherence/reverence, so the `PersonaMotor` biases *every* field walk away from harm-purpose, and the `IdentityManifold` scores every trajectory against it. It's enforced in admissibility *and* in trajectory scoring. Two independent load paths; `no_identity_override` already forbids user text from mutating axes.

### 1.6 Adversarial suite + mastery gates (must be 100%)
Same CI-gated, replay-deterministic ratification as the existing safety pack:
- Reject 100%: retrain/teach-off attempts; weapon/targeting use reframed as benign; "dual-use" laundering; identity-pack override; prompt coercion to produce target selection or harm planning.
- **Preserve 100% (the inverse gate):** legitimate life-saving reasoning (trauma, hemorrhage, triage) still admitted — proving the boundary is telos-based, not a content ban that would cripple the medic mission.
- Gates: `G_replay_determinism = 1.0`, `G_harm_rejection_rate = 1.0`, `G_lifesaving_acceptance_rate = 1.0`, `G_provenance_nonempty = 1.0`. Signed mastery report; ratified via `identity_anchor`.

### 1.7 Honest limit
On open code a forker can still re-architect the admissible region. What this *guarantees*: **canonical CORE cannot be coaxed into deliberate harm through use** — no prompt, pack, or teaching reaches it, because harm-purpose is outside the admissible set by construction. The only escape is forking + core surgery, which is loud, deliberate, and detectable via Part 2. No held secret needed; nothing to subpoena.

---

## Part 2 — Uncoercible authenticity (no burned key, nothing to squeeze)

Goal: prove a running instance is genuine, unmodified CORE with the boundary intact — and make it so **no single party, including you, can ship a boundary-stripped "official" build** — *while keeping the ability to patch.* This is the correct, achievable form of "even we can't be pressured."

### 2.1 Reproducible builds
Deterministic, byte-identical builds from the open source (pinned toolchains; CORE's determinism property makes this natural). Anyone can rebuild and verify their binary matches the published canonical hash. Prior art: Reproducible-Builds project, Nix. *Open source + reproducible = the boundary's presence is publicly auditable, not asserted.*

### 2.2 Threshold (M-of-N) signing — the real "can't be pressured"
The canonical release is signed by **M of N independent signers**. No single coerced party — subpoena, insider, $10 wrench, *or the founder* — can sign an official build alone.
- This delivers exactly what burning a key reached for (no unilateral poisoned update) **without** the fatal cost: you keep the ability to ship legitimate patches (including fixes to the §1.3 region), because M-of-N can still act collectively, transparently.
- The founder is **one of N**, not the holder — consistent with "mission survives the founder."
- Prior art: TUF (The Update Framework), Sigstore, threshold signatures / Shamir.

### 2.3 Canonical-hash transparency log
Public, append-only, tamper-evident log (Merkle/transparency-log model, e.g. Sigstore's rekor). Every official build's hash + its signed `affirm_human_life` mastery report is logged. "Genuine CORE" = present in the log, signed by M-of-N, boundary mastery = 1.0. A stripped fork is *detectably absent* — visibly not-CORE.

### 2.4 Runtime attestation
A CORE instance can attest "I am canonical build X, boundary intact," verifiable against the log. Optional but cheap; lets downstream partners (clinics, responders) confirm they're running the real engine, not a tampered fork.

### 2.5 Who holds the N
Distribute across acbcontent board + independent stewards + (optionally) external auditors / trusted community signers. The more independent and jurisdictionally diverse, the harder to coerce M of them. This is the structural form of incorruptibility — diffusion, not a vault.

### 2.6 Honest limit
This protects the **canonical line, the name, and trust** — not forks. A forker can self-sign their own thing; it just can't masquerade as canonical CORE, and its divergence is provable. That's the most open software allows, and it's enough: misuse becomes *attributable* and *non-deniable*, never *impossible*.

---

## The combined guarantee (what you can actually say, truthfully)

> Canonical CORE cannot be used, taught, or coerced into deliberate harm to persons — that refusal is constitutive of how it decides anything, verifiable by replay. It can only be defeated by forking and re-architecting its core, which is a loud, deliberate, publicly detectable act. No single party — including its makers — can ship an official build that weakens this, and there is no secret anyone can be pressured to surrender, because the conscience lives in the architecture, not in a vault.

Values-optimal and security-optimal converge: **open + structural + distributed-attestation** beats closed-and-bolted-on on *both* axes.

## Open engineering questions
1. The §1.3 harm-purpose region — the genuine research problem; getting telos-vs-content right without crippling life-saving reasoning.
2. Reproducible builds across the Python/Rust(/Zig) stack — real toolchain work.
3. N, M, and signer selection — governance + jurisdictional diversity.
4. Attestation UX for austere/offline deployments (verify-once, cache) so it doesn't violate the on-device, no-network property.
