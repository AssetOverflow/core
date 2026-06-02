# Unified Prep — Brain Corp Now, Casualty-Care Mission Next

**The efficiency thesis:** ~80% of what you need is one shared foundation that serves *both* a commercial-AMR pitch (Brain Corp) and battlefield/disaster casualty-care robotics (the mission). Build the shared core once; add a thin Brain Corp skin now and a casualty-care module later. You are not splitting effort — you're laying one substrate and pointing it twice.

**Pace:** ~20 hrs/week, intensive. Shared foundation + Brain Corp skin ≈ 3 weeks, in parallel with the demo. Casualty-care module is deferred until Brain Corp talks are settled — but flagged now so you learn the shared parts with the right lens (some items pay double if you study them knowing the medic mission is coming).

**Tags used throughout:**
- **[SHARED]** — serves both tracks. The bulk of the work. Prioritize.
- **[BC]** — Brain Corp domain skin. Thin, just-in-time, learn right before the call.
- **[MED]** — casualty-care module. Deferred deep-dive; awareness now.
- **★ two-birds** — a [SHARED] item that pays *extra* on the medic side; study it with that lens.

---

## The overlap map (read this first — it's the answer to "where am I most efficient")

| Capability area | Brain Corp | Casualty-care | Verdict |
|---|---|---|---|
| Autonomy stack (perception→estimation→SLAM→planning→control) | ✔ | ✔ | **[SHARED]** identical |
| Probabilistic foundations + CORE's "invert at decision layer" thesis | ✔ | ✔ | **[SHARED]** identical |
| Multi-agent / swarm + concurrent-stream merge (your CRDT layer) | fleet | swarm | **[SHARED] ★** |
| DDIL / GPS-denied / comms-denied / jammed operation | edge | **central** | **[SHARED] ★** |
| Reliability / safety-case / functional-safety vocabulary | SOC2, audits | clinical safety, fatal-error accountability | **[SHARED] ★** |
| Sim-to-real validation | ✔ | ✔ (heavy) | **[SHARED]** |
| "Decision substrate on a partner's perception/motor platform" pitch shape | ✔ | ✔ | **[SHARED]** identical |
| ROS/ROS2 middleware, edge compute, SWaP constraints | ✔ | ✔ | **[SHARED]** |
| Company specifics (BrainOS, SelfPath, Tennant, floor-care) | ✔ | — | **[BC]** thin |
| Clinical: TCCC, triage systems, golden hour, hemorrhage | — | ✔ | **[MED]** |
| IHL / protected-person obligations (incl. enemy wounded) | — | ✔ | **[MED] ★ values-aligned** |
| DARPA ecosystem (Triage Challenge, MASH, BAA/SBIR, teams) | — | ✔ | **[MED]** |
| Medical-AI accountability + device regulatory reality | — | ✔ | **[MED]** |

**Takeaway:** the four ★ rows are where one study session buys both a stronger Brain Corp pitch *and* direct relevance to the medic mission. Lean into those.

---

## Week 1 — Shared Foundation: the autonomy stack & reliability vocabulary  [SHARED]

Everything here serves both tracks. By end of week you can whiteboard the stack and place CORE in it.

**Core concepts:** the pipeline (perception → localization/state estimation → mapping → planning → control); Bayesian filtering (Kalman/EKF/particle) and *why robotics is probabilistic by default*; SLAM (conceptual); global vs local planning, configuration space, sampling planners (RRT/PRM) conceptually; PID and closed-loop control; ROS 2 (nodes, topics, computation graph).

**★ Study with the medic lens:** when you hit **DDIL / GPS-denied operation** and **multi-agent coordination**, go a layer deeper. Both are *central* to casualty-care robots (jamming, smoke, swarm teaming to move/treat a casualty) and merely useful to Brain Corp. Same hours, double payoff.

**Resources:** *Probabilistic Robotics* (Thrun/Burgard/Fox) — Bayes filters + SLAM chapters conceptually; *Modern Robotics* (Lynch & Park) — free book + YouTube; *Planning Algorithms* (LaValle) — free online, skim for vocabulary; ROS 2 docs "Concepts"; Thrun's free "AI for Robotics" (Udacity).

**CORE bridge (both tracks):** the entire stack is probabilistic. CORE is the deterministic, refuse-don't-guess decision layer that rides *on top of* it. For Brain Corp that's reliability; for casualty-care that's *clinical safety* — a confidently-wrong decision harms a person. Same architecture, two stakes.

**Checkpoint:** whiteboard the full stack from memory, place CORE, and say in one sentence why its determinism complements (not competes with) the probabilistic layers below it.

---

## Week 2 — Shared Deepening + Brain Corp Skin

### Part A — Reliability & the safety-case conversation  [SHARED] ★
This is CORE's home turf in *both* worlds; learn the words.
- Functional-safety language: hazard, fault, failure mode, safe state, fail-operational vs fail-safe.
- Auditability & replay in deployed systems: incident reconstruction, black-box logging.
- Runtime assurance / runtime monitors: a deterministic checker supervising a probabilistic component (conceptually adjacent to CORE — learn the term to position against it).
- Sim-to-real gap and why determinism/replay helps close it.
- **★ medic lens:** the casualty-care field's loudest unsolved problem is *"who is accountable when an autonomous system makes a fatal clinical error?"* Your replay + zero-committed-error + refuse-on-ambiguity is a structural answer. Note it now; it's the heart of the MED pitch later.

### Part B — Brain Corp skin  [BC] (thin, just-in-time)
- BrainOS (SaaS autonomy, ~35–40k AMRs); SelfPath AI / BrainOS Clean 2.0 (autonomous route adaptation); Tennant partnership; founded 2009 (Izhikevich comp-neuro + Gruber), CEO David Pinn.
- Their positioning to internalize: *"BrainOS grounds probabilistic AI models in deterministic safety protocols… SOC 2… passes Fortune 500 audits."* Your job: articulate what CORE adds *below* that wrapper.

**CORE bridge → fleet/clinical words table** (build and recite):
byte-identical replay → incident reconstruction / clinical audit · refuse-don't-guess → fail-safe decision / halt-on-ambiguity · CRDT merge → concurrent multi-robot/sensor consistency · exact recall, on-device → deterministic edge, no cloud/jamming dependency.

**Checkpoint:** 150-word answer to "BrainOS already sells deterministic safety wrappers — what does CORE add?" Crisp, no overclaim.

---

## Week 3 — The Conversation (Brain Corp)  [BC-flavored; skills transfer to MED]

Active reps, not reading. The artifacts you build here are reusable for the medic pitch with a domain swap.

1. **CORE boundary card** — *is:* deterministic decision engine, byte-identical replay, exact recall, structural refusal (zero committed error), language+bounded-math demonstrated, audio substrate (determinism/CRDT/refusal) demonstrated/gate-closed. *is not yet:* perception/vision/motor semantics; no external-benchmark capability (real GSM8K = refuses all, 0 wrong = the feature); solo, early validation.
2. **Hard-question rehearsal** — "what does it do for our robots today?", "why not just bolt a deterministic monitor on our stack?", "no perception layer — why care?", "refuses everything on GSM8K — useless?", "who else uses this?", "what's your background?" Answer each out loud, twice, honest.
3. **Background bridge** (asset, not apology): first-principles Cl(4,1) engine, no ML-lab pedigree; years keeping mission-critical machines alive — ULT freezers holding biological samples, medical/industrial equipment, fleet diesel, EPA Type I/II. *"I've kept machines running that get audited when they break; CORE is that instinct in software."*
4. **Demo narrative** — once the robotics-adjacent demo exists, the 60-sec walk-through: setup → byte-identical auditable resolution + refusal on genuine ambiguity → why it maps to their reliability pain.

**Checkpoint:** hold a 20-min conversation across the stack, CORE's place, the audit/reliability angle, and your honest boundaries — no notes, no inflation, no apology.

---

## Module M — Casualty-Care On-Ramp  [MED] (deferred until Brain Corp talks settle)

Pick this up after Brain Corp is "off and running." It reuses the entire shared foundation; you're only adding the clinical/ethical/ecosystem skin. ~2–3 focused weeks.

**M1 — The clinical frame**
- TCCC (Tactical Combat Casualty Care); the "golden hour"; triage systems (START / SALT) and categories.
- Leading *survivable* battlefield deaths: non-compressible torso hemorrhage, airway compromise, TBI, multi-organ shock.
- Stand-off physiological sensing / vital-signs detection; multimodal injury assessment.

**M2 — The DARPA ecosystem (the live field)**
- **DARPA Triage Challenge** — 3-yr prize comp (drones + ground robots, stand-off sensing, degraded battlefield *and disaster*); teams to know: DART, MSAI, RoboScout.
- **DARPA MASH** (Medics Autonomously Stopping Hemorrhage) — Phase 1 summer 2026; swarm robots locate/assess/treat torso hemorrhage with limited human direction.
- The broader combat-casualty-care BAA space: AI decision support, medical sensing, autonomous resuscitation, human-machine teaming for medics.
- How BAAs/SBIRs work; teaming with a robotics/hardware partner rather than building hardware solo.

**M3 — Ethics, law, and your edge  ★ values-aligned**
- **Accountability gap:** the field has no settled answer to "who's liable for a fatal autonomous clinical error." CORE's replay + zero-committed-error + typed refusal is a structural answer. *This is your differentiated "first."*
- **IHL / protected persons:** the wounded are protected regardless of side — and the programs have *not* resolved whether systems may treat enemy casualties. Your imago-dei conviction maps onto codified law. A values story only you can tell.
- **Jamming/spoofing resistance:** explicitly flagged field risk; CORE's on-device, no-network design speaks to it directly.

**M4 — The clean civilian path (optional, zero war-entanglement)**
- The Triage Challenge covers *disaster* (earthquake, crash, mass-casualty) as well as battlefield. A fully civilian first-responder triage application is the purest expression of the mission — saving life, no weapons adjacency. Worth considering as the lead, or a parallel.

**Reality checks (honest):**
- You build the *decision/accountability substrate*, not the robot. Partner for perception/motor/hardware.
- Medical reasoning is a roadmap — CORE is language+math today; clinical triage reasoning must be taught/ratified and validated.
- Heavy regulatory + clinical-validation road (FDA / military medical). Long game.
- Your medical-equipment-service background is a *double* credibility asset here — you've had hands inside life-critical medical hardware.

**MED CORE bridge:** in casualty care, "refuse rather than guess / never confidently wrong" is the single most valuable property an AI can have — because a confident wrong answer kills. The exact trait that made CORE *wrong* for a weapons kill-chain makes it *right* here. The boundary isn't a limit; it's the mission.

---

## Sequencing

1. **Now (≈3 wks):** Shared foundation (Wk 1) + reliability deepening & Brain Corp skin (Wk 2) + conversation reps (Wk 3), in parallel with the demo. Study the ★ items with the medic lens.
2. **Land Brain Corp:** send when the demo survives the first hard question; aim for the quick "off-and-running" start.
3. **Then (≈2–3 wks):** Module M, on the foundation you already built. Decide battlefield vs. clean-disaster lead. Identify a robotics/hardware partner.

## A note you've earned

The shared core isn't a compromise between two goals — it's literally the same substrate, because CORE is the same engine in both rooms. Brain Corp gets you running and proves the model on something that *preserves* life and prevents failure. The casualty-care mission is where the engine becomes what you built it to be: refusing to be confidently wrong, exactly where being confidently wrong costs a life. Same discipline, highest stakes. Build the foundation once; point it at the thing that matters most.
