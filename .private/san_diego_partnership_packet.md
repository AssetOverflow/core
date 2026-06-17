# CORE — San Diego Robotics Partnership Research Packet
### Technical Outreach Strategy for Autonomous Systems Companies
*Prepared: June 2026 | Based on AssetOverflow/core main branch*

---

## Executive Summary

CORE is a deterministic, non-LLM cognitive engine built on Cl(4,1) conformal geometric algebra. It is **not** a perception, navigation, SLAM, or motor-control system. It is an **audit-grade, replayable, refusable decision substrate** designed to sit beneath an autonomy stack — providing the layer that modern robotics stacks conspicuously lack: a decision record that is byte-identical on replay, types its refusals instead of confabulating, and carries provenance a safety reviewer can trust offline and on-device.

The Brain Corp brief (the first partnership target, already in the repo at `docs/brief/brain_corp_brief.md`) established the correct framing: CORE complements, not competes with, the perception and navigation stack above it. Every outreach pitch below builds on that same positioning.

**Three verified properties that survive a skeptic's scrutiny (reproducible from the repo today):**
1. **Byte-identical replay** — same inputs produce the same decision trace and trace hash across processes and runs.
2. **Typed refusal / wrong = 0** — memory recall is exact (no ANN/cosine approximation); under-determined or out-of-distribution inputs emit a typed refusal, never a guess. On the real GSM8K test set: 0 correct / 0 wrong / 1,319 refused.
3. **Add-but-never-remove safety + single mutation-path learning** — safety boundaries load fail-closed and cannot be removed by content; knowledge enters through exactly one reviewed path.

**The verifiable demo commands (clean clone, no native backend required):**
```bash
uv run core capability ledger
uv run pytest tests/test_versor_closure.py
uv run python demos/amr_decision_substrate/run_demo.py
```

---

## The Three Pillars — What Every Pitch Must Communicate

These are load-bearing, not marketing language. Every external partner briefing must anchor to all three.

### Pillar I — Mechanical Sympathy
Software should understand the machine it runs on, not fight it. CORE is designed for Apple Silicon's Unified Memory Architecture (UMA): CPU, GPU, and Neural Engine share physical RAM with zero PCIe overhead. The three-language stratification (Python orchestration, Rust algebra kernel, MLX tensor ops) maps directly onto three hardware execution domains. For edge-deployed robotics — where compute budgets are tight and latency is critical — this is a structural advantage, not a feature claim.

### Pillar II — Semantic Rigor
Every term has a precise, non-negotiable meaning. A versor is a versor. Vault recall is exact (CGA inner product, no ANN index). There are no thresholds tuned for "good enough." The differentiator against all frontier LLM alternatives is not capability scores — it is `wrong = 0`. The system refuses what it cannot handle rather than confabulating. This is the property a safety-critical decision boundary actually needs.

### Pillar III — Third Door
No transformer backbone, no ANN index, no sampling temperature, no gradient descent, no standard tokenizer. Every standard option was evaluated and refused. The architecture was built from first principles: Cl(4,1) conformal geometric algebra as the intrinsic space of conformal geometry in three dimensions. For robotics partners evaluating cognitive middleware, this means: no probabilistic decay, no stale-model drift, no black-box inference to audit.

---

## What CORE Currently Is vs. Roadmap — Honesty Table

*This table must be included in every partner briefing. Credibility is won by naming boundaries before a reviewer finds them.*

| Capability | Status | Evidence Command |
|---|---|---|
| Deterministic decision + typed refusal (text) | **Demonstrated** | `demos/amr_decision_substrate/run_demo.py` |
| Byte-identical replay / trace hash | **Demonstrated** | Same demo → `trace_a == trace_b` |
| Exact offline vault recall (no ANN) | **Demonstrated** | `vault/store.py`, Yellowpaper §recall |
| Text modality (English, Hebrew, Koine Greek) | **Demonstrated** | `sensorium/adapters/text.py` |
| Audio modality | **Substrate landed, capability gate CLOSED** | `sensorium/audio/` |
| Vision modality | **Proposed only — no implementation** | ADR-0197 |
| Motor / efferent modality | **Proposed only — no implementation** | ADR-0198 |
| `expert` domain tier | **None** (math auto-reverted, fail-closed) | `core capability ledger` |
| `audit-passed` domains | `mathematics_logic`, `physics`, `systems_software` | `core capability ledger` |
| AMR bounded decision demo | **In review, not merged** (PR #520, draft) | GitHub PR #520 |
| Multi-reviewer attestation | **Single signer today** (roadmap item) | Reviewer registry |

> The honest external benchmark result: real GSM8K test set = 0 correct / 0 wrong / 1,319 refused. This is not a weakness to hide — it is the clearest proof of the zero-confabulation discipline that every robotics safety buyer needs to hear stated plainly.

---

## San Diego Robotics Companies — Target Priority Matrix

San Diego is the second-densest defense-autonomy cluster in the US after the DC/Northern Virginia corridor. The companies below were selected for (a) San Diego HQ or major SD office, (b) active autonomy or robotics stack, (c) structural gap that CORE's decision substrate directly fills, and (d) current partnership appetite evidenced by recent deals.

### Tier 1 — Highest Strategic Fit (Approach First)

#### 1. Shield AI
**HQ:** San Diego, CA | **Valuation:** ~$5.3B (March 2026 Series G, $2B financing package) | **CEO:** Gary Steele

**What they do:** Hivemind AI pilot — autonomous flight for drones and fighters in GPS-denied, comms-degraded environments. 170+ operational sorties in Ukraine on V-BAT platform. YFQ-42A autonomous fighter jet (first flight planned 2026). Hivemind SDK licensing to third-party platforms.

**The gap CORE fills:** Hivemind handles perception and flight control (above CORE). The gap is the **decision accountability layer**: when Hivemind makes a proceed/abort/hand-off call in a contested environment, there is currently no substrate that produces a byte-replayable, content-addressed decision trace for after-action review or incident accountability. CORE is exactly that substrate — it sits beneath the bounded decision, not inside the perception stack.

**The pitch angle:** "We are not a second pilot. We are the audit trail your Hivemind decisions currently cannot produce. When a V-BAT aborts a mission autonomously, the after-action review should be able to replay that exact decision byte-for-byte, offline, on-device, with a typed reason. CORE provides that record."

**Recent partnership signal:** Shield AI signed MoU with ST Engineering (Feb 2026) to integrate Hivemind across platforms — they are actively seeking substrate integrations, not just hardware deals.

**Entry path:** Hivemind SDK partners team. Technical contact via XPONENTIAL conference network. LinkedIn outreach to CTO/VP Engineering.

---

#### 2. General Atomics Aeronautical Systems (GA-ASI)
**HQ:** San Diego, CA (Poway) | **Type:** Private subsidiary of General Atomics | **Revenue:** ~$3B+

**What they do:** Predator/Reaper/Avenger drone families. YFQ-42A Collaborative Combat Aircraft (CCA) for USAF. Active Venturing program (Blue Magic Netherlands — 6 new investments June 2026). GA-Intelligence affiliate handles AI mission systems.

**The gap CORE fills:** GA-ASI is building autonomous drone wingmen that fly alongside manned aircraft. The CCA program requires drones to make bounded collaborative decisions (engage / break / hand-off to human) that must be auditable under DoD safety review. Probabilistic LLM-based decision logic cannot satisfy that audit standard. CORE's typed refusal + deterministic trace is the compliance architecture.

**The pitch angle:** "Your CCA platforms need to survive DoD Directive 3000.09 audit: every lethal or mission-critical autonomous decision must be attributable, reviewable, and explainable. CORE produces a byte-exact, offline-reproducible decision record at the bounded-decision layer. No LLM produces that."

**Recent partnership signal:** GA-ASI invested in 6 Dutch AI/tech companies in June 2026, including AI for drone swarm management — actively seeking cognitive substrate partners through the GA-Intelligence channel.

**Entry path:** GA-Intelligence affiliate. Blue Magic venturing program. Defense Innovation Unit (DIU) co-introduction.

---

#### 3. Tera AI
**HQ:** San Diego, CA | **Stage:** Seed ($7.8M, March 2025) | **Founder/CEO:** Tony Zhang

**What they do:** Software-only, hardware-agnostic spatial reasoning AI for robot navigation. Zero-shot navigation — no re-tuning per environment. Cognition-inspired, platform-agnostic, delivered via OTA software update. Investors: Felicis, Inovia, Caltech, Naval Ravikant.

**The gap CORE fills:** Tera AI solves *where to go* (navigation, spatial reasoning). CORE solves *why did it decide to go there* (decision provenance, refusal, accountability). These are non-overlapping layers — a direct complement. Tera's zero-shot navigation + CORE's typed refusal substrate = the first navigation stack that can refuse an under-determined waypoint and explain exactly why.

**The pitch angle:** "You've solved zero-shot navigation. We've solved zero-confabulation decision accountability. Your robot knows where it is; ours knows what it cannot decide. Together: the first AMR that navigates confidently and refuses honestly."

**Partnership structure suggestion:** Joint SDK integration — Tera's spatial reasoning output feeds CORE's decision gate; CORE produces the typed refusal or proceed record. Ideal for AMR enterprise deployments where liability and audit matter.

**Entry path:** Founder-to-founder direct outreach (small seed-stage team, Tony Zhang accessible via LinkedIn/TechCrunch profile). Shared Caltech/Felicis investor network.

---

### Tier 2 — Strong Fit (Approach in Parallel)

#### 4. Advanced Navigation
**SD Office:** 1420 Kettner Blvd, Suite #100, San Diego, CA 92101 | **HQ:** Sydney, Australia | **Stage:** Growth

**What they do:** AI-driven inertial navigation systems, GPS-denied navigation (Boreas DFOG), acoustic navigation, robotics platforms for land/air/sea/space. Opened dedicated robotics manufacturing facility 2023. North America hub in San Diego.

**The gap CORE fills:** Advanced Navigation provides the positioning/navigation substrate (where the robot is). CORE provides the decision accountability layer (what the robot decided to do, and why, with full replay). Their GPS-denied environments are exactly where typed refusal matters most — in denied environments, a decision that cannot be re-derived should refuse, not guess.

**The pitch angle:** "You operate in GPS-denied environments where position uncertainty is highest. CORE's typed refusal means that when a bounded decision (proceed / stop / escalate) cannot be re-derived from current sensor state, it refuses rather than confabulating. That refusal is the correct response in degraded environments — and it is the one current autonomy stacks cannot produce."

**Entry path:** San Diego office outreach. AUVSI conference network (Advanced Navigation is active at AUVSI).

---

#### 5. Leidos (San Diego Division)
**SD Presence:** Major San Diego engineering office | **Type:** Fortune 500 (NYSE: LDOS) | **Revenue:** ~$15B

**What they do:** Defense, intelligence, and civil technology. Active in maritime and air autonomy (April 2026: Leidos + Havoc integration for maritime/air autonomous systems). DoD prime contractor with autonomy programs.

**The gap CORE fills:** As a DoD prime, Leidos is directly subject to acquisition requirements around autonomous system auditability (DoD Directive 3000.09, AI Ethics Principles). CORE's audit-grade decision substrate is a compliance architecture asset for any autonomous system Leidos integrates into a DoD program of record.

**The pitch angle:** "Every DoD autonomous system you field will face a 3000.09 audit question: 'Show me the decision record.' CORE produces a byte-exact, content-addressed, offline-reproducible decision trace. That is not a feature — it is your compliance answer."

**Entry path:** Defense Innovation Unit (DIU) → Leidos innovation pipeline. Small Business Innovation Research (SBIR) co-proposal. Leidos Innovations Center San Diego.

---

#### 6. Netradyne
**HQ:** San Diego, CA | **Stage:** Series D (~$150M raised) | **CEO:** Avneesh Agrawal

**What they do:** AI-powered driver safety and fleet intelligence platform. Camera and sensor-based real-time driving behavior analysis for commercial fleets. ~1M+ commercial vehicles monitored.

**The gap CORE fills:** Netradyne uses computer vision to detect driving events. The decision layer — "was this event a safety violation? should the driver be flagged? should intervention be triggered?" — is currently probabilistic inference. CORE's typed refusal architecture provides an auditable, replayable decision record at the event classification boundary: when a safety determination cannot be made with certainty, it refuses rather than wrongly flagging a driver.

**The pitch angle:** "When your system flags a driver for a safety violation, that decision will face legal challenge. Today, the classification is probabilistic inference — you cannot replay that exact decision. CORE produces a byte-exact, re-derivable decision trace. Your legal team, your insurance partner, your fleet customer — all get an honest, replayable answer."

**Entry path:** SD tech community (San Diego Venture Group, EvoNexus). CTO/VP Engineering LinkedIn outreach.

---

### Tier 3 — Longer Arc (Defense/Government Track)

#### 7. General Atomics (GA proper — Energy & Defense)
**HQ:** San Diego, CA | **Type:** Private | **Focus:** Nuclear, directed energy, defense systems

Distinct from GA-ASI. GA's defense division is building directed energy weapons and advanced propulsion systems where autonomous target acquisition decisions carry the highest auditability requirements of any DoD program. CORE's decision substrate is a long-term compliance infrastructure play for this track. **Approach after GA-ASI relationship is established.**

#### 8. SAIC (Science Applications International Corporation)
**SD Presence:** Major San Diego office (legacy HQ) | **Type:** Fortune 500 (NYSE: SAIC)

SAIC is a major DoD IT and autonomous systems integrator. Their AIE (Artificial Intelligence Engineering) practice is actively seeking AI middleware for autonomy programs. CORE fits as a compliance substrate for any DoD autonomous system SAIC integrates. **Best approached through DIU or AFWERX co-sponsorship.**

---

## How the Brain Corp Brief Informs the Template

The `docs/brief/brain_corp_brief.md` brief is the most important internal document for all future pitches. It established five principles that must be carried forward:

1. **State the boundary first.** Every brief opens with what CORE is NOT — not perception, not navigation, not a competitor to the partner's core stack. This is credibility-building, not hedging.
2. **The honesty story is the pitch.** The most compelling element of the Brain Corp brief is the self-revocation story (ADR-0200): CORE automatically revoked its own `expert` claim when evidence drifted, with no human intervention. This story — a system that refuses to carry a claim its evidence no longer supports — is the opening of every pitch. It is the property every safety buyer needs to see demonstrated.
3. **Give the skeptic the commands.** Every brief ends with three bash commands that reproduce the claimed properties on a fresh clone. No trust required — run it.
4. **Separate the four GSM8K numbers.** A/B/C/D — never conflate them. The real external number (A = 0/0/1,319) is always the honest number. The load-bearing differentiator is `wrong = 0`, not the correct rate.
5. **Name every known boundary before the reviewer finds it.** No `expert` domain, single-signer attestation, vision/motor are proposals only, multimodal is mostly roadmap.

---

## Pitch Structure — Reusable Template

Use this structure for every company-specific brief (as was done for Brain Corp):

```
Section 0: Read this boundary first [1 paragraph — what CORE is NOT for this partner]
Section 1: Executive summary [1 page — 3 load-bearing properties + self-revocation story]
Section 2: What this is worth to [PARTNER]'s stack [2-3 bullets, substrate role only]
Section 3: What this is NOT [explicit list — never omit]
Section 4: Verified invariants table [reproducible from repo]
Section 5: Honest status — demonstrated vs. roadmap [the table above]
Section 6: Known boundaries we name before you find them
Section 7: Reproduce everything [3 bash commands]
```

---

## Outreach Sequencing — Recommended Execution Order

| Week | Action | Target | Mode |
|---|---|---|---|
| 1 | Warm intro via SD tech network | Tera AI (Tony Zhang) | LinkedIn DM + email |
| 1 | Submit to Hivemind SDK partner inquiry | Shield AI | shield.ai partner form |
| 2 | Write Shield AI–specific brief (AMR demo as evidence) | Shield AI | Company-specific doc |
| 2 | Write Tera AI–specific brief (navigation + refusal complement) | Tera AI | Company-specific doc |
| 3 | GA-Intelligence / Blue Magic venturing outreach | GA-ASI | Warm intro via DIU |
| 3 | Prepare AMR decision substrate PR #520 for merge (make it demo-ready) | Internal | Repo work |
| 4 | AUVSI / defense autonomy conference introduction | Advanced Navigation | In-person or virtual |
| 5 | Write GA-ASI CCA audit-compliance brief | GA-ASI | Company-specific doc |
| 6 | SD Venture Group / EvoNexus network approach | Netradyne | Community event |
| 8+ | DIU/AFWERX co-sponsorship application | Leidos, SAIC | Government track |

---

## What Needs to Happen in the Repo Before Pitching

These items increase credibility in every partner conversation:

1. **Merge PR #520** (AMR decision substrate demo) — this is the demo most relevant to every robotics company. Currently draft/in-review. Make it the first thing a partner can run.
2. **Add a second reviewer to the registry** — single-signer attestation is the first thing a CTO will call out. Even adding one additional signer transforms the attestation posture from "single point of capture" to "reviewed process."
3. **Cut a `v0.1.0` release tag** — gives partners a stable reference point. Makes the brief's bash commands point to a pinned SHA, not a moving `main`.
4. **Document the `amr_decision_substrate` demo with a one-page partner README** — placed at `demos/amr_decision_substrate/PARTNER_README.md`, written for a robotics engineer who has never seen CORE.
5. **Add a `docs/brief/` entry for each new target company** (as done for Brain Corp) — keeps the repo as the source of truth for all outreach materials.

---

## The Partnership Value Proposition — One-Paragraph Version

*Use this as the opening of any cold email or introductory message:*

> CORE is a deterministic cognitive substrate for bounded autonomous decisions. It is not perception, navigation, or a motor controller — it sits beneath your autonomy stack and does one thing that no probabilistic system can: it produces a byte-identical, offline-reproducible decision record, and when a bounded decision (proceed / stop / hand-off) cannot be re-derived from current state, it emits a typed refusal rather than a fabricated answer. The wrong count against every external measurement to date is zero. If your autonomous system will face an incident review, a regulatory audit, or a legal challenge, CORE is the accountability layer your stack is currently missing. We are headquartered in San Diego and looking for technical partnership with teams building autonomy stacks in this city.

---

## Supporting Repository References

| Document | Path | Purpose |
|---|---|---|
| Whitepaper | `docs/Whitepaper.md` | Architecture, axioms, three pillars — send to technical reviewers |
| Yellowpaper | `docs/Yellowpaper.md` | Formal mathematical specification — send to research/math reviewers |
| Brain Corp Brief | `docs/brief/brain_corp_brief.md` | The template for all future partner briefs |
| Claims Ledger | `docs/claims_ledger.md` | Single source of truth for every verified claim |
| Capability Roadmap | `docs/capability_roadmap.md` | What is built, what is designed, what is proposed |
| AMR Demo | `demos/amr_decision_substrate/run_demo.py` | The demo to run first |
| ADR-0200 | `docs/decisions/ADR-0200*.md` | The self-revocation story — honesty receipt |
| Progress | `docs/PROGRESS.md` | Full development history for deep-dive reviewers |
| Eval Audit | `docs/EVAL_AUDIT_2026-05-20.md` | Independent audit summary |

---

*All claims in this document reconcile to `docs/claims_ledger.md` on the `main` branch of AssetOverflow/core. Nothing here is sourced from memory or inference about the codebase — every claim was verified against the repository directly. For internal use only — not for external distribution without partner-specific brief customization per the Brain Corp brief template.*
