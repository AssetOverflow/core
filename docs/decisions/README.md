# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for the CORE project.

ADRs record significant architectural decisions: what was decided, why, what alternatives were considered, and what consequences follow. They are permanent records — superseded ADRs are archived, not deleted.

---

## Index

| ADR | Title | Status |
|---|---|---|
| [ADR-0001](ADR-0001-vocab-layer-invariants.md) | Vocab Layer Invariants | Accepted |
| [ADR-0002](ADR-0002-ingest-layer-design.md) | Ingest Layer Design (original) | Archived — superseded by ADR-0012 |
| [ADR-0003](ADR-0003-coordinate-system-dissolution.md) | Coordinate System Dissolution | Accepted |
| [ADR-0004](ADR-0004-rotor-as-operator-not-property.md) | Rotor as Operator, Not Property | Accepted |
| [ADR-0005](ADR-0005-language-pack-contract.md) | Language Pack Contract | Accepted |
| [ADR-0006](ADR-0006-field-energy-operator.md) | Field Energy Operator | Accepted |
| [ADR-0007](ADR-0007-valence-layer.md) | Valence Layer | Accepted |
| [ADR-0008](ADR-0008-allocation-physics.md) | Allocation Physics | Accepted |
| [ADR-0009](ADR-0009-compositional-physics.md) | Compositional Physics | Accepted |
| [ADR-0010](ADR-0010-identity-physics.md) | Identity Physics | Accepted |
| [ADR-0011](ADR-0011-renderer.md) | Renderer | Accepted |
| [ADR-0012](ADR-0012-core-ingest-governance-layer.md) | `core_ingest` Governance Layer | Accepted |
| [ADR-0013](ADR-0013-sensorium-multimodal-protocol.md) | `sensorium/` Multimodal Protocol Layer | Accepted |
| [ADR-0014](ADR-0014-train-learning-loop.md) | `train/` Learning Loop | Accepted (Stub) |
| [ADR-0015](ADR-0015-language-packs-and-holonomy-resonance.md) | Language Packs as Compiled Linguistic Manifolds | Accepted |
| [ADR-0016](ADR-0016-capability-roadmap.md) | Capability Roadmap and Eval Methodology | Accepted |
| [ADR-0017](ADR-0017-agency-scope.md) | Agency Scope: Responsive-with-Axiology | Accepted |
| [ADR-0018](ADR-0018-tool-use-scope.md) | Tool Use Scope: Typed Deterministic Operators | Accepted |
| [ADR-0019](ADR-0019-exact-vault-recall-acceleration.md) | Exact Vault Recall Acceleration | Accepted |
| [ADR-0020](ADR-0020-phase5-rust-parity-sequencing.md) | Phase 5 / Rust Parity Sequencing | Accepted (2026-05-16) |
| [ADR-0021](ADR-0021-epistemic-grade-policy.md) | Epistemic Grade Policy | Accepted |
| [ADR-0022](ADR-0022-forward-semantic-control.md) | Forward Semantic Control | Accepted (2026-05-17) |
| [ADR-0023](ADR-0023-forward-semantic-control-proof.md) | Forward Semantic Control: Proof Evidence | Accepted |
| [ADR-0024](ADR-0024-inner-loop-admissibility.md) | Inner-Loop Per-Rotor Admissibility | Accepted |
| [ADR-0025](ADR-0025-rotor-frame-admissibility-design-note.md) | Rotor / Frame Admissibility | Accepted (2026-05-17) |
| [ADR-0026](ADR-0026-ranked-admissibility-with-margin.md) | Ranked Admissibility with Margin | Accepted (2026-05-17) |
| [ADR-0027](ADR-0027-identity-packs.md) | Identity Packs — swappable, ratified | Accepted (2026-05-17) |
| [ADR-0028](ADR-0028-identity-surface-wiring.md) | Identity Surface Wiring | Accepted (2026-05-17) |
| [ADR-0029](ADR-0029-safety-packs.md) | Safety Packs — never-swappable, fail-closed | Accepted (2026-05-17) |
| [ADR-0030](ADR-0030-depth-language-hedge.md) | Depth-Language Hedge | Accepted (2026-05-17) |
| [ADR-0031](ADR-0031-score-decomposition-surface.md) | Score-Decomposition Surface | Accepted (2026-05-17) |
| [ADR-0032](ADR-0032-safety-check-surface.md) | SafetyCheck Predicate Surface | Accepted (2026-05-17) |
| [ADR-0033](ADR-0033-ethics-packs.md) | Ethics Packs — third pack tier | Accepted (2026-05-17) |
| [ADR-0034](ADR-0034-ethics-check-surface.md) | EthicsCheck Predicate Surface | Accepted (2026-05-17) |
| [ADR-0035](ADR-0035-turn-loop-verdict-surfacing.md) | Turn-Loop Verdict Surfacing | Accepted (2026-05-17) |
| [ADR-0036](ADR-0036-safety-refusal-policy.md) | Safety-Only Typed Refusal | Accepted (2026-05-17) |
| [ADR-0037](ADR-0037-per-predicate-ethics-refusal.md) | Per-Predicate Ethics Refusal Opt-In | Accepted (2026-05-17) |
| [ADR-0038](ADR-0038-hedge-injection.md) | Hedge Injection as Runtime Affordance | Accepted (2026-05-17) |
| [ADR-0039](ADR-0039-audit-completeness.md) | Audit Completeness — TurnVerdicts + stub TurnEvent | Accepted (2026-05-17) |
| [ADR-0040](ADR-0040-telemetry-sink.md) | Structured-Logging Sink | Accepted (2026-05-17) |
| [ADR-0041](ADR-0041-cli-verdicts-and-fanout.md) | `--show-verdicts` + FanOutSink | Accepted (2026-05-17) |
| [ADR-0042](ADR-0042-audit-tour-demo.md) | Audit Tour Demo (`core demo audit-tour`) | Accepted (2026-05-17) |
| [ADR-0043](ADR-0043-pack-measurements-phase2.md) | Phase-2 pack measurements — claims → numbers | Accepted (2026-05-17) |
| [ADR-0044](ADR-0044-medical-clinical-ethics-pack.md) | Medical / clinical ethics pack | Accepted (2026-05-17) |
| [ADR-0045](ADR-0045-long-context-recall-vs-transformer-baselines.md) | Long-context recall: CORE vs transformer baselines | Accepted (2026-05-17) |
| [ADR-0046](ADR-0046-forward-graph-constraint.md) | PropositionGraph as forward AdmissibilityRegion + industry demos | Accepted (2026-05-18) |
| [ADR-0047](ADR-0047-wire-forward-graph-constraint.md) | Wire forward graph constraint into the chat hot path (opt-in) | Accepted (2026-05-18) |
| [ADR-0048](ADR-0048-pack-grounded-surface.md) | Pack-grounded surface for cold-start DEFINITION / RECALL | Accepted (2026-05-18) |
| [ADR-0049](ADR-0049-intent-subject-extraction.md) | Intent classifier head-noun subject extraction | Accepted (2026-05-18) |
| [ADR-0050](ADR-0050-pack-grounded-comparison.md) | Pack-grounded surface for cold-start COMPARISON | Accepted (2026-05-18) |
| [ADR-0051](ADR-0051-trust-boundary-hardening.md) | Trust-boundary hardening pass | Accepted (2026-05-18) |
| [ADR-0052](ADR-0052-teaching-grounded-surface.md) | Teaching-grounded surface for cold-start CAUSE / VERIFICATION | Accepted (2026-05-18) |
| [ADR-0053](ADR-0053-cognition-lane-closure.md) | Cognition lane closure + correction acknowledgement | Accepted (2026-05-18) |
| [ADR-0054](ADR-0054-vault-recall-indexing-batching.md) | Vault recall indexing + batched API | Accepted (2026-05-18) |
| [ADR-0055](ADR-0055-inter-session-memory-discovery-promotion.md) | Inter-session memory: reviewed discovery promotion | Phase A + B Accepted; C–E Proposed (2026-05-18) |
| [ADR-0056](ADR-0056-contemplation-loop-c1.md) | Contemplation loop C1 | Accepted (2026-05-18) |
| [ADR-0057](ADR-0057-teaching-chain-proposal-review.md) | Teaching-chain proposal + review + replay-equivalence gate | Accepted (2026-05-18) |
| [ADR-0058](ADR-0058-forward-graph-constraint-status.md) | Forward graph constraint remains opt-in default-false | Accepted (2026-05-18) |
| [ADR-0059](ADR-0059-correction-pass-telemetry.md) | Correction-pass telemetry | Accepted (2026-05-18) |
| [ADR-0060](ADR-0060-correction-acknowledgment-topic-lemma.md) | Correction acknowledgement topic lemma | Accepted (2026-05-18) |
| [ADR-0061](ADR-0061-procedure-intent-pack-grounded-surface.md) | Procedure intent pack-grounded surface | Accepted (2026-05-18) |
| [ADR-0062](ADR-0062-composed-teaching-grounded-surface.md) | Composed teaching-grounded surface | Accepted (2026-05-18) |
| [ADR-0063](ADR-0063-cross-pack-surface-resolver.md) | Cross-pack surface resolver | Accepted (2026-05-18) |
| [ADR-0064](ADR-0064-cross-pack-teaching-chains.md) | Cross-pack teaching chains | Accepted (2026-05-18) |
| [ADR-0065](ADR-0065-oov-gradient-and-relations-v2.md) | OOV gradient + relations v2 | Accepted (2026-05-18) |
| [ADR-0066](ADR-0066-turn-level-composition.md) | Turn-level composition | Accepted (2026-05-18) |
| [ADR-0067](ADR-0067-cross-pack-teaching-chains.md) | Cross-pack teaching chains — explicit cross-domain edges | Accepted (2026-05-18) |
| ADR-0068–ADR-0079 | Reserved / see git history until individual ADR files are added to this index | Not indexed |
| [ADR-0080](ADR-0080-contemplation-loop.md) | Contemplation loop | Proposed |
| ADR-0081–ADR-0082 | Reserved / see git history until individual ADR files are added to this index | Not indexed |
| [ADR-0083](ADR-0083-transitive-chain-surface.md) | Transitive chain surface | Proposed |
| [ADR-0084](ADR-0084-definitional-layer.md) | Definitional layer | Proposed |
| ADR-0085–ADR-0086 | Reserved / see git history until individual ADR files are added to this index | Not indexed |
| [ADR-0087](ADR-0087-rhetorical-style-axis.md) | Rhetorical style axis | Proposed |
| [ADR-0088](../adr/ADR-0088-realizer-grounded-authority.md) | Realizer grounded authority | Proposed |
| [ADR-0089](../adr/ADR-0089-compound-intent-pipeline-dispatch.md) | Compound intent pipeline dispatch | Proposed |
| [ADR-0090](../adr/ADR-0090-unified-ingest-and-batched-recall.md) | Unified ingest and batched recall | Proposed |
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

---

## Current frontier

The ADR-0091..0102 slate is fully accepted and mechanically evidenced:

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

Six lanes are SHA-pinned in `scripts/verify_lane_shas.py` and gated by the `lane-shas` GitHub Actions workflow: `reviewer_registry`, `domain_contract_validation`, `miner_loop_closure`, `fabrication_control_summary`, `demo_composition`, `public_demo`.

The next implementation frontier is open. Candidate directions include:

- **Curriculum-sourced proposals.** ADR-0094 reserved `ProposalSource(kind="curriculum")`; a curriculum ADR can introduce it without secondary schema churn.
- **Holdout splits for language-specific lanes.** ADR-0102 currently relies on universal lanes (`inference_closure`, `fabrication_control`); language-specific fluency lanes (`evals/hebrew_fluency/`, `evals/koine_greek_fluency/`) need sealed holdout splits before they can attach to `reasoning-capable` claims.
- **Expert-demo ratification.** All ADR-0097/0100/0101/0102 ledger rows currently sit at `reasoning-capable` with `expert_demo=false`. The next status tier requires evidence beyond the universal lanes.

No ADR currently sits in a "Proposed but unimplemented" state.

---

## Accepted reasoning-capable domains

| Domain | Ratification ADR | Pack(s) | Evidence summary |
|---|---|---|---|
| `mathematics_logic` | ADR-0097 | `en_mathematics_logic_v1` | All nine ADR-0091 predicates pass; ledger row is `reasoning-capable`; `expert_demo` remains false; lanes include positive coverage, inference closure, and fabrication control. |
| `physics` | ADR-0100 | `en_physics_v1` | All nine predicates pass; causal/modal operator coverage meets threshold; ledger row is `reasoning-capable`; `expert_demo` remains false. |
| `systems_software` | ADR-0101 | `en_systems_software_v1` | All nine predicates pass; transitive/causal operator coverage meets threshold; ledger row is `reasoning-capable`; `symbolic_logic` is the v1 closest-fit eval lane. |
| `hebrew_greek_textual_reasoning` | ADR-0102 | `grc_logos_micro_v1`, `grc_logos_cognition_v1`, `he_logos_micro_v1`, `he_core_cognition_v1` | First multi-pack ratification; all four packs carry uniform contract fields; causal/contradiction operator coverage meets threshold; universal lanes are declared until language-specific holdouts land. |

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

### Evidence-governed domain chain — ADR-0091 through ADR-0102

ADR-0091 through ADR-0102 establish the current domain-ratification substrate:

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
