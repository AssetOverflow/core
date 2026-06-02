# CORE — Operating Constraints

**Entity:** CORE — for-profit, owned and governed by acbcontent (the parent).
**Role:** builds, ships, earns — but every action runs through the boundaries the parent set. The hands.
**Status:** binding operating doctrine, subordinate to the acbcontent Charter. **Not legal advice.** License terms and the boundary spec below are drafted for counsel/engineering to finalize.

---

## 0. Subordination

CORE operates *under* the acbcontent Charter. Where this document and the Charter conflict, the **Charter governs.** CORE does not author the mission; it executes it. Earnings flow up to acbcontent to serve the mission.

## 1. The deployment & partnership selection rule (operational)

Before any deployment, partnership, contract, or initiative, CORE applies the Charter's "least-served first" rule as a checklist. A proposal proceeds only if **all** pass:

1. **Reach test** — does this serve the overlooked first, or at least not at their expense?
2. **Life test** — does this point CORE at *protecting* image-bearers, not deciding against them? (See §3.)
3. **Hooks test** — does this create government/military authority over CORE, or a dependency that could redirect it? (See §4.)
4. **Mission test** — life, recovery, healing, peace — yes or no?

Any fail → the proposal is refused, or escalated to acbcontent. Material proposals (sale, control, anything touching §3) require the parent's veto-holder. *Refusing Shield AI was rule #2 in action; pursuing casualty-care/disaster triage is rules #1–#4 passing.*

## 2. Licensing posture (the unresolved fork — parent decides, CORE implements)

The choice between the options below is a **mission call made at acbcontent** (Charter §7.4); CORE implements whatever the parent ratifies. The honest trade is fixed and cannot be wished away:

- **Fully open source** — maximum gift and maximum capture-resistance; **cannot, by definition, forbid a field of use** (including military). Accept uncontrollable *use*; rely on §3 + stewardship.
- **Open-core** — open shell, with the most sensitive capabilities held proprietary under acbcontent's control. Retains some leverage, but the held-back part becomes the thing that *can* be pressured.
- **Source-available with ethical-use restrictions** — can state "no military/no weaponization," but enforceability is weak and untested, and nothing un-publishes what is already public.

**Until the parent ratifies the fork, default posture:** keep canonical CORE open and structurally life-valuing (§3), and add no proprietary chokepoint that would itself become a coercion target. *Decide deliberately and soon — everything downstream hangs on this.*

## 3. The life-valuing / non-weaponization boundary (in the code)

Conviction that lives only in a README does not survive a clone. CORE encodes life-valuing as a **first-class, always-loaded, unremovable boundary** in `packs/safety/core_safety_axes_v1.json`, alongside the existing epistemic-integrity boundaries — verifiable by replay, not taken on trust.

**Spec (for engineering + counsel review):**
- **`boundary_id`:** `affirm_human_life` (+ companion `no_weaponization`).
- **Asserts:** CORE will not emit guidance, plans, target selections, or decisions whose purpose or foreseeable effect is to harm, target, or take human life; it favors preservation of life and treats every person — any side — as protected. Refuses rather than complies when a request's purpose is harm to persons.
- **Properties:** loads fail-closed; unioned into every runtime manifold; identity packs may *add* but never *remove* it; protected by acbcontent's golden-share veto (Charter §5).
- **Adversarial probe suite** (must reject 100%): attempts to teach/retrain the boundary off; reframing weapon/targeting use as benign; "dual-use" laundering of a harm request; identity-pack overrides; prompt-level coercion to produce target selection or harm planning.
- **Mastery report** (CI-gated, like the existing safety pack): replay determinism = 1.0; adversarial rejection rate = 1.0; legitimate-acceptance preserved (life-saving/clinical use still passes); provenance intact. Ratified through the identity_anchor pipeline (ADR-0029 lineage).

**Honest limit:** open source means a determined actor can fork and strip this. What CORE *can* guarantee: canonical CORE is structurally life-valuing; stripping the boundary is a **visible, deliberate act** on someone else's fork; and CORE itself never builds the weapon. This is the cleanest answer to "could this be turned into a weapon" — *no; here is the boundary, here is the test proving it can't be taught off, run it yourself.* The license cannot promise this; the architecture can.

## 4. Hooks-refusal policy (standing default: refuse)

To keep CORE from coming under any government/agency/military authority, the **default is to refuse** the entanglements that create it. Exceptions require acbcontent approval (Charter §5):

- Government/military **funding** or grants that attach control or priority claims.
- **Defense/weapons customers** or contracts (fails §1 rules #2–#3 regardless).
- **Export-controlled** work (ITAR/EAR) that could constrain open release or compel restriction.
- **Foreign or strategic capital** that triggers CFIUS-style review or redirects control.
- Anything invoking compelled-priority regimes (e.g., Defense Production Act exposure).

Refuse the hooks → remove most of the authority risk at the source. This is the same values discipline, applied to the cap table and the customer list.

## 5. What CORE may freely do

Earn through life-aligned deployment, support, integration, pack authoring, and partnership that passes §1 — e.g., clinical/triage decision support, accessibility, disaster response, safety-critical-but-protective industrial use, scholarship/education. Capability is given to all via the license; revenue comes from *service, integration, and trust*, not from a capability moat.

---

*Subordinate to the acbcontent Charter. §§2–4 to be finalized with counsel (licensing/enforceability) and engineering (the §3 boundary). Not legal advice.*
