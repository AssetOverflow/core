# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for the CORE project.

ADRs record significant architectural decisions: what was decided, why, what alternatives were considered, and what consequences follow. They are permanent records — superseded ADRs are archived, not deleted.

---

## Index

| ADR | Title | Status |
|---|---|---|
| [ADR-0080](ADR-0080-contemplation-loop.md) | Contemplation Loop | Accepted (2026-05-22) |
| [ADR-0091](ADR-0091-domain-pack-contract-v1.md) | Domain Pack Contract v1 | Accepted (2026-05-22) |
| [ADR-0092](ADR-0092-reviewer-registry-v1.md) | Reviewer Registry v1 | Accepted (2026-05-22) |
| [ADR-0093](ADR-0093-domain-pack-contract-v1-implementation.md) | Domain Pack Contract v1 implementation | Accepted (2026-05-22) |
| [ADR-0094](ADR-0094-proposal-source-provenance.md) | Proposal Source Provenance | Accepted (2026-05-22) |
| [ADR-0095](ADR-0095-miner-sourced-teaching-proposals.md) | Miner-Sourced Teaching Proposals | Accepted (2026-05-22) |
| [ADR-0096](ADR-0096-fabrication-control-eval-lane.md) | Fabrication-Control Eval Lane | Accepted (2026-05-22) |
| [ADR-0097](ADR-0097-mathematics-logic-reasoning-capable-ratification.md) | Mathematics-Logic Reasoning-Capable Ratification | Accepted (2026-05-22) |
| [ADR-0098](ADR-0098-demo-composition-contract.md) | Demo Composition Contract | Accepted (2026-05-22) |
| [ADR-0099](ADR-0099-public-showcase-demo.md) | Public Showcase Demo | Accepted (2026-05-22) |
| [ADR-0100](ADR-0100-physics-reasoning-capable-ratification.md) | Physics Reasoning-Capable Ratification | Accepted (2026-05-22) |
| [ADR-0101](ADR-0101-systems-software-reasoning-capable-ratification.md) | Systems-Software Reasoning-Capable Ratification | Accepted (2026-05-22) |
| [ADR-0102](ADR-0102-hebrew-greek-reasoning-capable-ratification.md) | Hebrew-Greek Textual-Reasoning Reasoning-Capable Ratification | Accepted (2026-05-22) |
| [ADR-0103](ADR-0103-fluency-lane-attachment-for-adr-0102.md) | Fluency Lane Attachment for ADR-0102 | Accepted (2026-05-22) |
| [ADR-0104](ADR-0104-curriculum-sourced-teaching-proposals.md) | Curriculum-Sourced Teaching Proposals | Accepted (2026-05-22) |
| [ADR-0105](ADR-0105-sealed-holdout-encryption.md) | Sealed Holdout Encryption via age | Accepted (2026-05-22) |
| [ADR-0106](ADR-0106-expert-demo-promotion-contract.md) | Expert-Demo Promotion Contract | Accepted (2026-05-22) |
| [ADR-0107](ADR-0107-mathematics-logic-expert-demo-deferred.md) | `mathematics_logic` Expert-Demo Promotion — Deferred | Accepted (2026-05-22) |
| [ADR-0108](ADR-0108-proposed-adr-sequencing.md) | Proposed-ADR Sequencing Post-ADR-0105 | Accepted (2026-05-22) |
| [ADR-0109](ADR-0109-lane-shape-aware-thresholds.md) | Lane-Shape-Aware Thresholds (ADR-0106 Amendment) | Accepted (2026-05-22) |
| [ADR-0110](ADR-0110-mathematics-logic-expert-demo-promotion.md) | `mathematics_logic` Expert-Demo Promotion | Accepted (2026-05-22) |
| [ADR-0111](ADR-0111-physics-expert-demo-promotion.md) | `physics` Expert-Demo Promotion | Accepted (2026-05-22) |
| [ADR-0112](ADR-0112-runnable-expert-demo-showcase.md) | Runnable Audit-Passed Showcase (originally "Expert-Demo") | Accepted (2026-05-22) |
| [ADR-0113](ADR-0113-rename-expert-demo-to-audit-passed.md) | Rename `expert-demo` → `audit-passed`; Reserve `expert` for Future Capability Tier | Accepted (2026-05-22) |
| [ADR-0114](ADR-0114-expert-capability-roadmap-gsm8k-first.md) | Expert-Capability Roadmap: GSM8K-Math First | Proposed (2026-05-22) |
| [ADR-0114a](ADR-0114a-anti-overfitting-proof-obligations.md) | Anti-Overfitting Proof Obligations for `expert` Promotion | Accepted (2026-05-22) |
| [ADR-0115](ADR-0115-math-problem-parser-and-graph.md) | Math Problem Parser and Typed Proposition Graph | Phase 1.1+1.2+1.3 Accepted (2026-05-22) |
| [ADR-0116](ADR-0116-deterministic-solver.md) | Deterministic Solver (`MathProblemGraph` → `SolutionTrace`) | Accepted (2026-05-22) |

---

## Current frontier

The ADR-0091..0114 slate is fully accepted (0091..0113) plus one proposed-roadmap entry (0114) and mechanically evidenced:

- Domain Pack Contract v1 — ADR-0091
- Reviewer Registry v1 — ADR-0092
- Domain Contract v1 enforcement — ADR-0093
- Proposal Source Provenance — ADR-0094
- Miner-Sourced Teaching Proposals — ADR-0095
- Fabrication-control negative eval lane — ADR-0096
- `mathematics_logic` reasoning-capable ratification — ADR-0097
- Demo Composition Contract — ADR-0098
- Public Showcase Demo — ADR-0099
- `physics` reasoning-capable ratification — ADR-0100
- `systems_software` reasoning-capable ratification — ADR-0101
- `hebrew_greek_textual_reasoning` multi-pack reasoning-capable ratification — ADR-0102
- Hebrew/Greek fluency lane attachment for ADR-0102 — ADR-0103
- Curriculum-Sourced Teaching Proposals — ADR-0104
- Sealed Holdout Encryption via age — ADR-0105
- Expert-Demo Promotion Contract — ADR-0106
- `mathematics_logic` Expert-Demo Promotion deferred (first attempt) — ADR-0107
- Proposed-ADR Sequencing — ADR-0108
- Lane-Shape-Aware Thresholds (ADR-0106 amendment) — ADR-0109
- `mathematics_logic` Expert-Demo Promotion (first successful) — ADR-0110
- `physics` Expert-Demo Promotion (second successful) — ADR-0111
- Runnable Audit-Passed Showcase (originally "Expert-Demo"; renamed) — ADR-0112 + ADR-0113
- Rename `expert-demo` → `audit-passed`; reserve `expert` namespace — ADR-0113
- Expert-Capability Roadmap (GSM8K-Math first); proposed — ADR-0114
- Math Problem Parser & Typed Graph (Phase 1.1 schema + 5 seeds + Phase 1.2 45 more cases + Phase 1.3 parser engine; 50/50 byte-equal) — ADR-0115
- Anti-Overfitting Proof Obligations for any future `expert` promotion (10-point falsifiable framework) — ADR-0114a
- Deterministic Solver (Phase 2; SolutionTrace + en_arithmetic_v1 pack; discharges ADR-0114a obligations #3, #4, #9, #10) — ADR-0116

ADR-0080 has also landed: Contemplation Loop Phase 1 adds a read-only frontier-compare miner that emits `SPECULATIVE` findings only.

Seven lanes are SHA-pinned in `scripts/verify_lane_shas.py` and gated by the `lane-shas` GitHub Actions workflow:

- `reviewer_registry`
- `domain_contract_validation`
- `miner_loop_closure`
- `curriculum_loop_closure`
- `fabrication_control_summary`
- `demo_composition`
- `public_demo`

### Proposed-but-unimplemented ADRs

Sequencing per ADR-0108. Listed in priority order:

1. **[ADR-0084](ADR-0084-definitional-layer.md) — Definitional Layer for Lexicon Packs.** Optional per-entry definitional block. Deferred — value surfaces during a worked expert promotion that needs definitional depth.
2. **[ADR-0087](ADR-0087-rhetorical-style-axis.md) — Rhetorical Style Axis.** A third substantive selection axis sibling to anchor-lens. Lowest current priority — no active downstream consumer; register + anchor-lens already demonstrate the orthogonality pattern.

ADR-0080 (Contemplation Loop, Phase 1), ADR-0110 (math audit-passed), and ADR-0111 (physics audit-passed) have all landed — `mathematics_logic` and `physics` are at `audit_passed=true`; the contemplation loop emits read-only `SPECULATIVE` findings from `frontier_compare` reports. The remaining two ratified domains (`systems_software`, `hebrew_greek_textual_reasoning`) need their own promotion ADRs.

### Open candidate directions (no ADR yet)

- **Multi-reviewer holdout governance and threshold signing.** ADR-0105 seals holdout payloads with a single recipient identity; multi-reviewer governance remains future work.

---

## Accepted reasoning-capable domains

Per ADR-0106, `audit_passed` is **contract-gated**, not threshold-only: a domain row may carry `audit_passed=true` only when a reviewer-signed `audit_passed_claims` entry exists whose evidence-bundle digest reproduces byte-for-byte. ADR-0107 attempted the first worked promotion and the contract refused; ADR-0109 amended the threshold rules; ADR-0110 then successfully promoted `mathematics_logic` (the first domain at `audit_passed=true`); ADR-0111 promoted `physics` second without further contract change, retiring the "math-only" objection. The other two ratified domains remain at `reasoning-capable` pending their own promotion ADRs.

| Domain | Ratification ADR | Pack(s) | Evidence summary |
|---|---|---|---|
| `mathematics_logic` | ADR-0097 + ADR-0110 | `en_mathematics_logic_v1` | All nine ADR-0091 predicates pass; ledger row is **`audit-passed`** (first such promotion, ADR-0110); all three attached lanes meet ADR-0109 shape thresholds on public + holdout. |
| `physics` | ADR-0100 + ADR-0111 | `en_physics_v1` | All nine predicates pass; causal/modal operator coverage meets threshold; ledger row is **`audit-passed`** (second such promotion, ADR-0111); `foundational_physics_ood` 117/117 public + 39/39 holdout; shares `inference_closure` + `fabrication_control` results with math (distinct digest via `domain_id`). |
| `systems_software` | ADR-0101 | `en_systems_software_v1` | All nine predicates pass; transitive/causal operator coverage meets threshold; ledger row is `reasoning-capable`; `symbolic_logic` is the v1 closest-fit eval lane. |
| `hebrew_greek_textual_reasoning` | ADR-0102 + ADR-0103 | `grc_logos_micro_v1`, `grc_logos_cognition_v1`, `he_logos_micro_v1`, `he_core_cognition_v1` | First multi-pack ratification; all four packs carry uniform contract fields; causal/contradiction operator coverage meets threshold; ADR-0103 attaches Hebrew and Koine Greek fluency lanes with `dev/public/holdout` coverage. |

---

## ADR chain notes

### Forward Semantic Control closure — ADR-0022 through ADR-0026

ADR-0022 through ADR-0026 form a single coherent chain that closes forward semantic control as a non-stochastic, replay-deterministic, trace-evidenced mechanism.

1. **ADR-0022** establishes `AdmissibilityRegion` and the contract that a region restricts the admissible token set at generation time.
2. **ADR-0023** records proof evidence that the admissibility region is honored at the region-intersection level.
3. **ADR-0024** adds destination-side per-step admissibility and honest `InnerLoopExhaustion` when all admissible candidates are rejected.
4. **ADR-0025** adds rotor/frame admissibility when a region carries a `frame_versor`.
5. **ADR-0026** replaces static threshold tuning with ranked admissibility and a scale-invariant margin gate.

Runtime contracts for the chain are pinned in [`docs/runtime_contracts.md`](../runtime_contracts.md).

### Pack-layer chain — ADR-0027 through ADR-0045

ADR-0027 through ADR-0045 establish the identity / safety / ethics pack architecture with deterministic remediation, audit completeness, telemetry, operator readout, audit-tour demo, pack measurements, a worked-example medical ethics pack, and long-context comparison measurements.

### Evidence-governed domain chain — ADR-0091 through ADR-0111

ADR-0091 through ADR-0111 establish the current domain-ratification substrate and the audit-passed promotion gate that distinguishes contract-passing from demonstrated:

```text
contract definition (0091)
    ↓
reviewer trust root (0092)
    ↓
validator / ledger enforcement (0093)
    ↓
negative-control fabrication lane (0096)
    ↓
reasoning-capable domain ratification (0097 / 0100 / 0101 / 0102)
    ↓
language-specific fluency lane attachment (0103)
    ↓
audit-passed promotion contract (0106 + 0109 amendment)
    ↓
worked audit-passed promotion (0110 — mathematics_logic, first)
    ↓
worked audit-passed promotion (0111 — physics, second; no contract change)
```

No domain claim should be treated as mature merely because a pack exists. `reasoning-capable` means the nine ADR-0091 predicates pass; `audit-passed` requires a reviewer-signed evidence-bundle digest that reproduces byte-for-byte from on-disk lane results.

The contract has been demonstrated end-to-end: refused once honestly (ADR-0107), amended once cleanly (ADR-0109), succeeded against `mathematics_logic` (ADR-0110), and succeeded against `physics` without further contract change (ADR-0111).

---

## Session Logs

Session logs record the decisions and rationale from individual working sessions. They are not ADRs — they are the narrative record that informed the ADRs.

| Date | File |
|---|---|
| 2026-05-12 | [SESSION-2026-05-12.md](SESSION-2026-05-12.md) |
| 2026-05-12 (addendum) | [SESSION-2026-05-12-b.md](SESSION-2026-05-12-b.md) |
| 2026-05-12 (language packs) | [SESSION-2026-05-12-language-packs-addendum.md](SESSION-2026-05-12-language-packs-addendum.md) |
| 2026-05-13 | [SESSION-2026-05-13.md](SESSION-2026-05-13.md) |
