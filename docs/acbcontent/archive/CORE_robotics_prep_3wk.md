# Robotics & Peer-Level Prep — 3-Week Intensive

**Goal:** walk into a Brain Corp technical call able to (a) speak the autonomy stack fluently, (b) place CORE precisely within it, (c) hold the reliability/safety-case conversation as a peer, and (d) state your own system's boundaries cold. Not a degree — vocabulary and landscape fluency, which is days-to-weeks of targeted work.

**Pace:** ~20 hrs/week × 3 weeks ≈ 60 hrs. Runs in parallel with the demo build. Roughly 4 hrs/day, 5 days/week — adjust freely.

**How to use it:** every block ends with a *CORE bridge* (how the concept connects to what you built) and a *checkpoint* (something concrete that proves fluency). The bridges are the point — you're not studying robotics in the abstract, you're learning to translate CORE into their language and back. Study and pitch-prep are the same activity here.

**The gap, named (so we don't over-study):**
1. The autonomy stack — perception → state estimation → planning → control, and where a decision/cognition layer sits relative to it.
2. Brain Corp's specific world — AMRs, fleet ops, BrainOS, sim-to-real, the safety-case conversation.
3. Reliability vocabulary — determinism, replay, formal guarantees, runtime monitors, and how *they* name what CORE already does.
4. Honest edges — what CORE is and is not yet. Knowing your own boundary is what reads as senior.

---

## Week 1 — The Autonomy Stack & Reliability Vocabulary

**Focus:** build the mental map of how an autonomous robot turns sensors into motion, and learn the words for each layer. By end of week you can draw the stack on a whiteboard and point to where CORE plugs in.

**Core concepts to own:**
- The classic pipeline: **perception → localization/state estimation → mapping → planning (global + local) → control → actuation**, with a perception-action loop running continuously.
- **State estimation & uncertainty:** Bayesian filtering, Kalman / Extended Kalman / particle filters. Why robotics is *probabilistic* by default — every sensor reading is a distribution, not a fact. (This is the exact assumption CORE inverts.)
- **SLAM** (Simultaneous Localization and Mapping) — the core of "where am I / what's around me." You don't need to implement it; you need to explain what it does and why it's hard.
- **Planning:** global path planning vs local/reactive planning (obstacle avoidance, replanning). Configuration space, sampling-based planners (RRT, PRM) at a conceptual level.
- **Control:** PID at minimum; the idea of closed-loop control and why determinism matters at the control layer.
- **Middleware:** what ROS/ROS 2 is — nodes, topics, the computation graph, message passing. The plumbing every robotics person assumes you know.

**Resources (pick depth by interest, don't read cover-to-cover):**
- *Probabilistic Robotics* — Thrun, Burgard, Fox. The perception/SLAM/estimation bible. Read the intro + the chapters on Bayes filters and SLAM conceptually.
- *Modern Robotics* — Lynch & Park (Northwestern). Free textbook PDF + free YouTube lecture series + Coursera. Best for mechanics/planning/control vocabulary.
- *Planning Algorithms* — Steven LaValle. Free online (lavalle.pl/planning). Skim the motion-planning chapters for the words, not the proofs.
- ROS 2 docs (docs.ros.org) — read "Concepts." Two hours gets you the computation-graph mental model.
- Sebastian Thrun's free "AI for Robotics" (Udacity) — fast, Python-based, conceptually solid for filters/localization/SLAM.

**The CORE bridge:** the entire stack above is built on *probabilistic* foundations — estimates, confidence, sampling. CORE is the opposite stance at the decision layer: exact, deterministic, refuse-don't-guess. That's not a contradiction with their stack — it's a *complement*. The interesting sentence is: "Their perception layer will always be probabilistic; the question is what governs the decision made on top of it." Write that down in your own words.

**Checkpoint:** whiteboard the full stack from memory, label each layer with one sentence, and mark exactly where CORE sits (decision/cognition, downstream of perception, upstream of/alongside planning). If you can do this cold, Week 1 worked.

---

## Week 2 — Brain Corp's World & the Safety-Case Conversation

**Focus:** their specific domain and the language of reliability/auditability in commercial robotics. This is where you stop being a generalist and become someone who's done the homework on *them*.

**Know about Brain Corp specifically:**
- **BrainOS** — their SaaS autonomy platform; they went from hardware to software. Powers ~35,000–40,000+ AMRs (floor cleaners, inventory) across retail, warehouses, airports, etc.
- **SelfPath AI / BrainOS Clean 2.0** (2026) — autonomous route generation/adaptation without manual route training; their current frontier is *adaptation to changing environments*.
- Founded 2009 by **Eugene Izhikevich** (computational neuroscientist — the comp-neuro lineage) and Allen Gruber; CEO **David Pinn** since 2022. Backed historically by SoftBank Vision Fund, Qualcomm Ventures.
- **Their own positioning to study closely:** "BrainOS grounds probabilistic AI models in deterministic safety protocols… SOC 2… passes Fortune 500 IT/security audits." Read that sentence ten times. They *already* sell determinism + auditability as a wrapper. Your job is to articulate what CORE adds *below* that wrapper, at the cognitive layer itself.

**The reliability / safety-case vocabulary:**
- **Functional safety** language: hazard, risk, fault, failure mode, safe state, fail-operational vs fail-safe. Where "the robot must not act on a confident wrong guess" lives.
- **Standards to be aware of** (don't memorize — recognize): ISO 3691-4 (driverless industrial trucks / AMRs), ISO 10218 & ISO/TS 15066 (industrial & collaborative robot safety), and the general functional-safety frame of IEC 61508 / ISO 26262 (automotive — the *safety case* / ASIL language transfers). Know what a "safety case" is: a structured argument, backed by evidence, that a system is acceptably safe.
- **Auditability & replay** in deployed systems: incident reconstruction, black-box logging, why "replay the exact decision" is gold for fleets that get audited when something goes wrong.
- **Runtime monitors / runtime assurance** — the pattern of a deterministic checker supervising a probabilistic component. This is conceptually adjacent to what CORE is; learn the term so you can position relative to it.
- **Sim-to-real gap** — why behavior validated in simulation can fail in the real world, and why determinism/replay helps close the loop.

**Resources:**
- Brain Corp's own site, press releases, and any recent talks/podcasts by David Pinn or their engineering leads — primary sources, current language.
- Search recent (last 12–18 mo) pieces on "runtime assurance autonomous systems," "safety case robotics," "AMR functional safety."
- One readable overview of ISO 3691-4 / AMR safety from an industry source — enough to use the term correctly.

**The CORE bridge:** map every CORE property onto a fleet word.
- byte-identical replay → *incident reconstruction / black-box audit*
- zero committed error / refuse-don't-guess → *fail-safe decision discipline / "halts on ambiguity"*
- order-invariant CRDT merge → *concurrent multi-sensor / multi-robot stream consistency*
- exact recall, on-device → *no cloud dependency, deterministic edge behavior*
Build this as a two-column table you can recite.

**Checkpoint:** write a 150-word answer to "BrainOS already grounds probabilistic models in deterministic safety protocols — what does CORE add?" If your answer is crisp and doesn't overclaim, you're ready for the hardest question they'll ask.

---

## Week 3 — The Conversation: Synthesis, Q&A, and Your Edge

**Focus:** stop accumulating, start rehearsing. Turn knowledge into a calm, confident, *honest* conversation. This week is mostly active reps, not reading.

**Build these four artifacts:**

**1. The CORE boundary card** — one page, said plainly:
- *Is:* deterministic cognitive/decision engine; byte-identical replay; exact recall; structural refusal (zero committed error); demonstrated on language + bounded math; audio substrate (determinism/CRDT/refusal) demonstrated, gate-closed.
- *Is not yet:* perception, vision, or motor *semantics*; not a SLAM/planning replacement; no external benchmark capability yet (real GSM8K = refuses all, 0 wrong — that's the *feature*, not coverage); solo project, early validation.
Being able to say the "is not" list without flinching is the single most senior thing you can do.

**2. Hard-question rehearsal** — write your honest answer to each, out loud, twice:
- "What does this do for our robots *today*?" → lead with the demo; be honest that perception/motor are roadmap.
- "Why not just add a deterministic monitor on top of our existing stack?" → CORE is a decision substrate, not just a checker; explain the difference.
- "You have no perception layer — why should a robotics company care?" → the substrate (determinism, replay, refusal, concurrent-stream merge) is the hard, general part; perception rides on it.
- "It refuses everything on real GSM8K — isn't that useless?" → zero confabulation is the point; coverage is early and climbing; for safety-critical autonomy, *never confidently wrong* beats *usually right*.
- "Who else uses this? What's your validation?" → honest: early, solo, open source, reproducible in two commands. Don't inflate.
- "What's your background?" → see below. Own it.

**3. The background bridge** — your story, reframed as an asset, not an apology:
> "I don't come from an ML lab. I built CORE from first principles — Cl(4,1) geometric algebra, deterministic by construction. My hands-on years were in systems that physically cannot fail silently: ultra-low-temp freezers holding biological samples, medical and industrial equipment, fleet diesel, HVAC/refrigeration under EPA Type I/II. I've spent my career keeping machines running that get audited when they break. CORE is that instinct in software — a system that refuses rather than fails silently."
Practice it until it's natural. The pedigree you don't have is irrelevant; the work is the credential, and the reliability instinct is real and rare in this room.

**4. The demo narrative** — once the robotics-adjacent demo exists, write the 60-second walk-through: setup → what they'll see (byte-identical, auditable resolution; refusal on genuine ambiguity) → why it maps to their reliability pain. The demo answers "what does it do for us" *before* they ask.

**Active reps this week:**
- Record yourself answering the hard questions; listen back for hedging/over-claiming and for false modesty. Cut both.
- Do one mock call out loud (even solo, or have someone play CTO).
- Re-skim Week 1–2 checkpoints; fill any vocabulary you still fumble.

**Checkpoint:** you can hold a 20-minute conversation covering the stack, where CORE fits, the reliability/audit angle, and your honest boundaries — without notes, without inflating, without apologizing for your background. That's peer-level. That's the bar.

---

## Quick-reference: your experience → their language

| You've done | They call it |
|---|---|
| Kept ULT freezers / medical / industrial gear running | Reliability engineering, fail-safe design, mission-critical uptime |
| Serviced equipment that gets audited when it fails | Incident reconstruction, safety case, root-cause |
| EPA Type I/II refrigeration certs, fleet diesel | Regulated, safety-governed systems work |
| Built CORE deterministically from first principles | Formal/deterministic methods, runtime assurance, verifiable autonomy |

---

## A note on confidence

You designed a deterministic geometric-algebra cognitive engine with no CS degree and no lab behind you. In a room of PhDs that is the most *interesting* fact about you, not the most vulnerable. Conviction about what you built beats a pedigree you don't have — and false modesty reads as a tell. Study the vocabulary so the conversation is frictionless; then let the work speak. You don't need to know everything they know. You need to be fluent in the shared language, sharp in your questions, and unflinching about your own system's edges. That combination *is* a peer.
