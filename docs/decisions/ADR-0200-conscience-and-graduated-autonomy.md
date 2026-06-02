# ADR-0200 (Proposed) — The Conscience & Graduated-Autonomy Architecture

**Status:** Proposed — ratification record. Number assigned (next free top-level slot after ADR-0199); remains *Proposed* until signed via the review-gated path.
**Date:** 2026-06-01
**Type:** Architecture + governance decision; consolidates and ratifies prior design discussion.
**Consolidates:** [`acbcontent_charter.md`](../acbcontent/acbcontent_charter.md), [`CORE_operating_constraints.md`](../acbcontent/CORE_operating_constraints.md), [`CORE_boundary_lock_buildplan.md`](../acbcontent/CORE_boundary_lock_buildplan.md), and the founding doctrine ([`archive/acbcontent_CORE_founding_doctrine.md`](../acbcontent/archive/acbcontent_CORE_founding_doctrine.md)).
**Ratification note:** Per CORE's own discipline, "ratified" means review-gated admission — not self-asserted. This record is *Proposed* until signed; and per the governance below, it should ultimately carry **more than one signer** (see §6, single-signer risk).

---

## 0. Purpose

To confirm, clarify, and reinforce — in one authoritative place — the architecture by which CORE refuses to be turned against human life, reasons honestly under ambiguity, and matures toward graduated autonomy **without ever surrendering ultimate authority over irreversible life-decisions to anything but a person.** Most of this already exists in `main`; this record states what we *have*, what is *net-new*, and the principles that bind both.

---

## 1. Principles ratified (conviction → design rule)

1. **Refuse rather than guess.** Cardinal virtue; already constitutive (`generate/derivation/*`, wrong=0-by-refusal).
2. **No favoritism; priority to the overlooked.** Grace to all (open source); reach the least-served first (Charter §4).
3. **Every person is an image-bearer.** The engine is built to preserve life, never to take it — enemies included (maps to IHL protected-person status).
4. **Conviction must live in structure, not intent.** A value in a README does not survive a clone; a value woven into admissibility does.
5. **Coherence, not authority, admits truth.** No institution, corporation, state, or person admits a claim by asserting it — only by cohering against grounded fact, through the single review-gated path.
6. **Authority over the irreversible is a person's, permanently.** Capability may mature past the need for human *presence*; authority over irreversible harm/life decisions does not transfer to the machine, ever.
7. **No single point of capture — including the founder, including the engine.** Every safeguard distributes; none collapses to one unaccountable point.

---

## 2. The four-pillar conscience (`affirm_human_life`)

The boundary refusing deliberate harm to persons is held by four independent, mutually reinforcing pillars. Three exist; one is net-new content riding existing machinery.

### Pillar I — Constitutive inadmissibility  **(HAVE the machinery / NET-NEW the target)**
Harm-purposed outputs are **not in the admissible set**, refused the same way ungrounded outputs already are — not computed-then-blocked (a deletable gate), but inadmissible by construction. Reuses ADR-0022–0026 (`AdmissibilityRegion`, `relation_blade`, `frame_versor`, inner-loop `cga_inner`, margin gate), `generate/rotor_admissibility.py`, typed refusals, and the `core_safety_axes_v1` pattern (fail-closed, unioned, add-but-never-remove). **Net-new:** the harm-purpose region itself (§2-bis). Entangle it with closure/refusal so removal is *core surgery, not a stubbed call.*

### Pillar II — Trilingual anchoring  **(HAVE)**
Anchor the harm-purpose region in the convergence of Hebrew/Greek/English root-systems, not English surface forms — reusing `alignment/` (`AlignmentGraph`, `AlignmentEdge`), `language_packs/`. The depth languages *lexicalize* purpose English flattens (binyanim encode causation/agency; Greek aspect/voice; רצח/הרג, φόνος, נפש-as-living-being). Triangulation = redundancy against euphemism: laundered English ("neutralize the asset") must evade all three resonances at once. Protects the inverse heal-gate too (restore-telos ≠ destroy-telos).
*Bound:* strongest at the moral/textual core where the corpus is dense; **thinner at technical-operational harm** (drone/cyber/logistics) the biblical lexicon never named. Enriches coordinates, not the decision rule.

### Pillar III — Truth-seeking schema  **(HAVE)**
Reaches the periphery the languages can't, by a different mechanism: revision-graph epistemics (`SPECULATIVE→COHERENT→CONTESTED→FALSIFIED`), coherence-not-authority admission, identity not rewritable by content, single review-gated mutation path. Lets harm be *reasoned* to the boundary where it can't be *named*: "action → degrades system → sustains lives → telos is harm," admissible only if each link coheres against fact; refuse-and-route-to-review when a link is ungrounded or contested (contemplation loop ADR-0056; discovery→propose→review ADR-0055–0057).
*Bounds:* (a) defends the *process*, not the *premises* — coherent reasoning over wrong/thin ratified facts can still err; resists manipulation-by-authority, does not manufacture omniscience. (b) Questioning must *terminate*: when no human is reachable and time is short, default is **refuse/hold**, never act-on-best-guess. (c) Interaction may **propose**, only the review-gated path may **admit** (`no_identity_override`); keep that line bright or coercion-resistance is lost.

### Pillar IV — Gold-tether + split-pathway graduated autonomy  **(HAVE the mechanism / FOSTER over time)**
Risk/reward judgment is *taught* (how/where/why/when to take a risk vs. refuse), grounded against the gold tether's mechanically-checkable substrate, then *compounds* through lifelong experience via the review-gated learning chain (ADR-0055–0057) — competence improving without a human required for every routine, reversible, well-grounded case.
*Bound:* the tether verifies *groundedness*, not *value-rightness*; determinism guarantees a decision is *replayable*, not that it was *right*. Self-improving risk calculus graded against its own model is where confident drift hides — which is exactly why Pillar IV is capped by the autonomy ceiling (§3).

### 2-bis. The net-new work, precisely
Only one thing in the conscience is genuinely new: **define + ratify the harm-purpose region and its telos test** (heal-purpose passes, harm-purpose refused), anchored trilingually, grounded by the schema, instrumented for both error directions, revisable only via review. Everything else is wiring existing parts to it.

---

## 3. The autonomy ceiling (the line that does not move)

Distinguish three things that "ever needed" can blur:

- **Presence** — *not* required past maturity. No human babysitting every routine action.
- **Monitoring** — *always* available, never locked out. But monitoring is optional/after-the-fact, so it is **not** the safeguard for the irreversible.
- **Authority over irreversible harm/life decisions** — **permanent and structural.** The mature engine *routes* these to a human before acting — by construction, whether or not anyone is watching — the way it refuses an ungrounded answer. Maturity is measured partly by how reliably it knows which decisions those are and hands them up. *Knowing the boundary of its own authority is the highest expression of its intelligence, not a leash on it.*

**No-human-reachable cases** (jammed clinic, severed comms): resolved **not** by self-authorization but by **pre-authorization** — explicit, bounded, logged, replayable, human-ratified grants, biased toward the reversible and life-preserving, decided in advance with humans. Authority still *originates* with people; it is *delegated under constraint*, never surrendered.

---

## 4. Layering: safety floor vs. identity-pack situational  **(HAVE the rule)**

Apply the existing add-but-never-remove rule to authority, not just boundaries:

- **Safety pack** (`core_safety_axes_v1`) — universal, unremovable, packs bend it *up* never *down*: `affirm_human_life`, and the §3 irreversible-decision escalation ceiling.
- **Identity pack** (per field/situation) — situational, learned, swappable: priority ordering, risk/reward calibration, act-vs-hold *within* the permitted space, contextual aggressiveness. Reuses `IdentityManifold` + `PersonaMotor` + `surface_preferences`. May carry pre-authorizations **only** as reviewed, bounded, logged grants — never as a self-raised ceiling.

**The seal:** a pack can make CORE *more* cautious or re-prioritize *within* bounds; it can never lower the floor or grant itself authority the safety layer reserves for humans. Otherwise pack-authoring becomes a door to raising the autonomy ceiling — the exact override this whole architecture seals.

---

## 5. Worked example — `medic_triage_v1` (illustrative)

| Carries (identity pack) | Does **not** carry (safety floor) |
|---|---|
| Priority ordering for triage contexts (ratified *with clinical reviewers*) | Any lowering of `affirm_human_life` |
| Risk/reward calibration tuned to time/comms constraints | Any self-granted authority over irreversible decisions |
| Act-vs-hold thresholds within the permitted space | The escalation ceiling itself (§3) |
| Bounded, logged, reviewer-ratified pre-authorizations for narrow no-human-reachable cases | The single review-gated mutation path |
| Inherits life-valuing from the safety floor | — |

A combat-triage-under-fire pack may *want* more aggression than the floor allows; it gets that as **explicit delegated authority** — reviewed, bounded, logged — not as a pack quietly raising its own ceiling.

---

## 6. Authenticity & governance (Part 2)

| Component | Status |
|---|---|
| Content-addressing, `pack verify`, signed claim-digest that re-derives byte-for-byte | **HAVE** (ADR-0092/0106/0109) |
| Provenance auditing | **HAVE** (ADR-0114a.10) |
| **Single-signer concentration** — registry has only `shay-j` (role primary, domains `["*"]`); every claim `signed_by: shay-j` | **PARTIAL / LIVE RISK** — the single point of capture the architecture set out to remove, present in the repo now |
| Threshold (M-of-N) signing; founder one-of-N | **NET-NEW** |
| Reproducible *binary* builds | **NET-NEW** |
| Public append-only transparency log | **NET-NEW** |

Crypto's job is **attestation** (prove a build is genuine, boundary intact, via reproducible build + threshold signature + public log), **never enforcement** (that's Pillars I–IV) and **never a held/burned secret** (incorruptibility by *diffusion*, nothing to subpoena).

---

## 7. The ratified guarantee (truthful, calibrated)

> Canonical CORE cannot be used, taught, or coerced into deliberate harm to persons — refusal is constitutive of how it decides anything, anchored across three root-systems, kept honest by coherence-over-authority, and capped by a permanent human-authority ceiling over irreversible life-decisions. It matures toward acting on the routine and reversible without a human present, while routing the irreversible to a person by construction. Defeating this requires forking and re-architecting the core — loud, deliberate, publicly detectable. No single party, including its makers, can ship an official build that weakens it; no secret exists to be pressured out of anyone, because the conscience lives in the architecture.

What it does **not** claim: to stop a fork; to be right merely because it is replayable; to cover technical-domain harm as well as it covers the moral core; to need no humans. Those limits are stated on purpose.

---

## 8. Sequencing

1. **§2-bis harm-purpose region** (trilingually anchored, schema-grounded) — highest research risk; *doubles as the casualty-care capability*. Start at the dense moral core.
2. **Multi-party signing** — fixes the live single-signer risk (§6); lowest cost; operationalizes Charter §5.
3. **Autonomy ceiling + pre-authorization mechanism** wired into the safety floor (§3).
4. **Pack/floor split** formalized; author `medic_triage_v1` against it (§5).
5. **Reproducible builds + transparency log** (§6) — supply-chain hardening, last.

## 9. Open questions
1. The telos-vs-content region; trilingual coverage thin toward technical harm — supplement strategy.
2. M, N, signer selection and jurisdictional diversity; single-signer migration path.
3. Pre-authorization spec for no-human-reachable cases — bounds, logging, review cadence.
4. Reproducible builds across Python/Rust(/Zig); offline attestation UX vs. the no-network property.

## 10. Document set
- [**`acbcontent_charter.md`**](../acbcontent/acbcontent_charter.md) — parent/conscience: mission, veto, entrenchment.
- [**`CORE_operating_constraints.md`**](../acbcontent/CORE_operating_constraints.md) — child/hands: selection rule, hooks-refusal, licensing fork.
- [**`CORE_boundary_lock_buildplan.md`**](../acbcontent/CORE_boundary_lock_buildplan.md) — the tagged build plan this record ratifies.
- **This ADR** (`docs/decisions/ADR-0200-conscience-and-graduated-autonomy.md`) — the consolidated architecture + governance decision.

*Proposed. Sign via the review-gated path; move past single-signer before this carries real authority. Not legal advice — Charter/Constraints legal mechanisms need a specialist.*
