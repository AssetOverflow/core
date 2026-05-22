# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for the CORE project.

ADRs record significant architectural decisions: what was decided, why, what alternatives were considered, and what consequences follow. They are permanent records — superseded ADRs are archived, not deleted.

---

## Index

| ADR | Title | Status |
|---|---|---|
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

---

## Current frontier

The ADR-0091..0105 slate is fully accepted and mechanically evidenced:

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

Seven lanes are SHA-pinned in `scripts/verify_lane_shas.py` and gated by the `lane-shas` GitHub Actions workflow:

- `reviewer_registry`
- `domain_contract_validation`
- `miner_loop_closure`
- `curriculum_loop_closure`
- `fabrication_control_summary`
- `demo_composition`
- `public_demo`

The next implementation frontier is open. Candidate directions include:

- **Expert-demo ratification.** All ADR-0097/0100/0101/0102 ledger rows currently sit at `reasoning-capable` with `expert_demo=false`. The expert-demo promotion contract remains open for a future ADR.
- **Multi-reviewer holdout governance and threshold signing.** ADR-0105 seals holdout payloads with a single recipient identity; multi-reviewer governance is a future direction.

No ADR currently sits in a "Proposed but unimplemented" state.

---

## Accepted reasoning-capable domains

| Domain | Ratification ADR | Pack(s) | Evidence summary |
|---|---|---|---|
| `mathematics_logic` | ADR-0097 | `en_mathematics_logic_v1` | All nine ADR-0091 predicates pass; ledger row is `reasoning-capable`; `expert_demo` remains false; lanes include positive coverage, inference closure, and fabrication control. |
| `physics` | ADR-0100 | `en_physics_v1` | All nine predicates pass; causal/modal operator coverage meets threshold; ledger row is `reasoning-capable`; `expert_demo` remains false. |
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

### Evidence-governed domain chain — ADR-0091 through ADR-0103

ADR-0091 through ADR-0103 establish the current domain-ratification substrate:

```text
contract definition
    ↓
reviewer trust root
    ↓
validator / ledger enforcement
    ↓
negative-control fabrication lane
    ↓
reasoning-capable domain ratification
    ↓
language-specific fluency lane attachment
```

No domain claim should be treated as mature merely because a pack exists. Capability status belongs to the generated ledger and its evidence predicates.

---

## Session Logs

Session logs record the decisions and rationale from individual working sessions. They are not ADRs — they are the narrative record that informed the ADRs.

| Date | File |
|---|---|
| 2026-05-12 | [SESSION-2026-05-12.md](SESSION-2026-05-12.md) |
| 2026-05-12 (addendum) | [SESSION-2026-05-12-b.md](SESSION-2026-05-12-b.md) |
| 2026-05-12 (language packs) | [SESSION-2026-05-12-language-packs-addendum.md](SESSION-2026-05-12-language-packs-addendum.md) |
| 2026-05-13 | [SESSION-2026-05-13.md](SESSION-2026-05-13.md) |
