# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for the CORE project.

ADRs record significant architectural decisions: what was decided, why, what alternatives were considered, and what consequences follow. They are permanent records — superseded ADRs are archived, not deleted.

---

## Index

| ADR | Title | Status |
|---|---|---|
| [ADR-0001](ADR-0001-vocab-layer-invariants.md) | VocabManifold Versor Invariant | Accepted |
| [ADR-0002](ADR-0002-ingest-layer-design.md) | Ingest Layer Architecture | Accepted |
| [ADR-0003](ADR-0003-coordinate-system-dissolution.md) | Coordinate System Dissolution | Accepted |
| [ADR-0004](ADR-0004-rotor-as-operator-not-property.md) | Rotor as Operator, Not Vocabulary Property | Accepted |
| [ADR-0005](ADR-0005-language-pack-contract.md) | Language Pack Contract | Accepted |
| [ADR-0006](ADR-0006-field-energy-operator.md) | The Field Energy Operator (Hamiltonian Companion Field) | Implemented |
| [ADR-0007](ADR-0007-valence-layer.md) | The Valence Layer | Accepted |
| [ADR-0008](ADR-0008-allocation-physics.md) | Allocation Physics | Accepted |
| [ADR-0009](ADR-0009-compositional-physics.md) | Compositional Physics | Accepted |
| [ADR-0010](ADR-0010-identity-physics.md) | Identity Physics | Accepted |
| [ADR-0011](ADR-0011-renderer.md) | Renderer Layer Contract | Accepted |
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
| [ADR-0022](ADR-0022-forward-semantic-control.md) | Forward Semantic Control | Accepted (2026-05-17 — all five TBDs addressed; all |
| [ADR-0023](ADR-0023-forward-semantic-control-proof.md) | Forward Semantic Control: Proof Evidence | — |
| [ADR-0024](ADR-0024-inner-loop-admissibility.md) | Inner-Loop Per-Rotor Admissibility | — |
| [ADR-0025](ADR-0025-rotor-frame-admissibility-design-note.md) | Rotor / Frame Admissibility | — |
| [ADR-0026](ADR-0026-ranked-admissibility-with-margin.md) | Ranked Admissibility with Margin | Accepted (2026-05-17) |
| [ADR-0027](ADR-0027-identity-packs.md) | Identity Packs — Load-Bearing, Swappable, Ratified | Accepted (2026-05-17) — Phases 1–6 complete; Phase 7 (this doc + the operational reference) complete; deep realizer wiring landed under [ADR-0028](ADR-0028-identity-surface-wiring.md) (2026-05-17). |
| [ADR-0028](ADR-0028-identity-surface-wiring.md) | Identity Surface Wiring — Pack-Driven Hedge & Claim Strength | Accepted (2026-05-17) |
| [ADR-0029](ADR-0029-safety-packs.md) | Safety Packs — Always-Loaded, Never-Replaceable Boundaries | Accepted (2026-05-17) |
| [ADR-0030](ADR-0030-depth-language-hedge.md) | Depth-Language Hedge Wiring | Accepted (2026-05-17) |
| [ADR-0031](ADR-0031-score-decomposition-surface.md) | Score-Decomposition Surface — Per-Axis Hedge Phrases | Accepted (2026-05-17) |
| [ADR-0032](ADR-0032-safety-check-surface.md) | SafetyCheck — Structural Surface for Safety-Pack Boundaries | Accepted (2026-05-17) |
| [ADR-0033](ADR-0033-ethics-packs.md) | Ethics Packs — Swappable Domain Commitments | Accepted (2026-05-17) |
| [ADR-0034](ADR-0034-ethics-check-surface.md) | EthicsCheck — Structural Surface for Ethics-Pack Commitments | Accepted (2026-05-17) |
| [ADR-0035](ADR-0035-turn-loop-verdict-surfacing.md) | Turn-Loop Verdict Surfacing for SafetyCheck and EthicsCheck | Accepted (2026-05-17) |
| [ADR-0036](ADR-0036-safety-refusal-policy.md) | Safety-Only Typed Refusal Policy | Accepted (2026-05-17) |
| [ADR-0037](ADR-0037-per-predicate-ethics-refusal.md) | Per-Predicate Ethics Refusal Opt-In | Accepted (2026-05-17) |
| [ADR-0038](ADR-0038-hedge-injection.md) | Hedge Injection as a Runtime-Level Affordance | Accepted (2026-05-17) |
| [ADR-0039](ADR-0039-audit-completeness.md) | Audit Completeness — `TurnVerdicts` Bundle, Stub-Path `TurnEvent`, `hedge_injected` Signal | Accepted (2026-05-17) |
| [ADR-0040](ADR-0040-telemetry-sink.md) | Structured-Logging Sink for Turn-Event Audit | Accepted (2026-05-17) |
| [ADR-0041](ADR-0041-cli-verdicts-and-fanout.md) | `core chat --show-verdicts` + Sink Fan-Out | Accepted (2026-05-17) |
| [ADR-0042](ADR-0042-audit-tour-demo.md) | Audit Tour Demo — `core demo audit-tour` | Accepted (2026-05-17) |
| [ADR-0043](ADR-0043-pack-measurements-phase2.md) | Phase-2 pack measurements: claims → numbers | Accepted (2026-05-17) |
| [ADR-0044](ADR-0044-medical-clinical-ethics-pack.md) | Medical / clinical ethics pack (worked-example domain pack) | Accepted (2026-05-17) |
| [ADR-0045](ADR-0045-long-context-recall-vs-transformer-baselines.md) | Long-context recall: CORE vs transformer baselines | Accepted (2026-05-17) |
| [ADR-0046](ADR-0046-forward-graph-constraint.md) | PropositionGraph as Forward Admissibility Constraint | Accepted |
| [ADR-0047](ADR-0047-wire-forward-graph-constraint.md) | Wire the Forward Graph Constraint into the Chat Hot Path | Accepted |
| [ADR-0048](ADR-0048-pack-grounded-surface.md) | Pack-Grounded Surface for Cold-Start DEFINITION / RECALL | Accepted |
| [ADR-0049](ADR-0049-intent-subject-extraction.md) | Intent Classifier Head-Noun Subject Extraction | Accepted |
| [ADR-0050](ADR-0050-pack-grounded-comparison.md) | Pack-Grounded Surface for Cold-Start COMPARISON | Accepted |
| [ADR-0051](ADR-0051-trust-boundary-hardening.md) | Trust-Boundary Hardening Pass | Accepted |
| [ADR-0052](ADR-0052-teaching-grounded-surface.md) | Teaching-Grounded Surface for Cold-Start CAUSE / VERIFICATION | Accepted |
| [ADR-0053](ADR-0053-cognition-lane-closure.md) | Cognition Lane Closure: Dev-Driven Corpus Expansion + CORRECTION Acknowledgement | Accepted |
| [ADR-0054](ADR-0054-vault-recall-indexing-batching.md) | Vault Recall: Matrix-Cache Indexing + Batched API; Holdout Split Wired | Accepted |
| [ADR-0055](ADR-0055-inter-session-memory-discovery-promotion.md) | Inter-Session Memory: Reviewed Discovery Promotion | Phase A + Phase B Accepted; Phase C Implemented (ADR-0056/0057); Phases D–E substantially landed |
| [ADR-0056](ADR-0056-contemplation-loop-c1.md) | Contemplation Loop: Question Decomposition + Polarity + Domain Typing (Phase C1) | Accepted (implemented at `4eecf73`, 2026-05-18) |
| [ADR-0057](ADR-0057-teaching-chain-proposal-review.md) | Teaching-Chain Proposal + Review + Replay-Equivalence Gate (Phase C2) | Accepted |
| [ADR-0058](ADR-0058-forward-graph-constraint-status.md) | `forward_graph_constraint`: Engaged but Inert on Today's Cognition Lane | Accepted |
| [ADR-0059](ADR-0059-correction-pass-telemetry.md) | Correction-Pass Telemetry Emission | Accepted |
| [ADR-0060](ADR-0060-correction-acknowledgment-topic-lemma.md) | CORRECTION Acknowledgement Carries the Corrected-Topic Lemma | Accepted |
| [ADR-0061](ADR-0061-procedure-intent-pack-grounded-surface.md) | PROCEDURE Intent Routes to Pack-Grounded Surface | Accepted |
| [ADR-0062](ADR-0062-composed-teaching-grounded-surface.md) | Composed Teaching-Grounded Surface (Chain-of-Chains) | Accepted |
| [ADR-0063](ADR-0063-cross-pack-surface-resolver.md) | Cross-pack surface resolver | Accepted |
| [ADR-0064](ADR-0064-cross-pack-teaching-chains.md) | Cross-pack teaching chains | Accepted |
| [ADR-0065](ADR-0065-oov-gradient-and-relations-v2.md) | OOV gradient + relations v2 (Plan Phase 2) | Accepted |
| [ADR-0066](ADR-0066-turn-level-composition.md) | Turn-level composition (Plan Phase 3) | Accepted |
| [ADR-0067](ADR-0067-cross-pack-teaching-chains.md) | Cross-pack teaching chains (Plan Phase 4) | Accepted |
| [ADR-0068](ADR-0068-register-pack-class.md) | Register pack class (Plan Phase R1) | Accepted |
| [ADR-0069](ADR-0069-realizer-register-parameter.md) | Realizer register parameter (Plan Phase R2) | Accepted (amended 2026-05-19) |
| [ADR-0070](ADR-0070-register-pack-terse-v1.md) | Second ratified register pack: `terse_v1` (Plan Phase R3) | Accepted |
| [ADR-0071](ADR-0071-seeded-surface-variation.md) | Seeded surface variation + discourse markers (Plan Phase R4) | Accepted |
| [ADR-0072](ADR-0072-register-telemetry-operator-surface.md) | Register telemetry + operator surface (Plan Phase R5) | Accepted |
| [ADR-0073](ADR-0073-anchor-lens-substrate.md) | Anchor lens: substrate-driven substantive variation | Accepted (umbrella ratified; sub-ADRs L1.1–L1.4 each ratify in isolation) |
| [ADR-0073a](ADR-0073a-anchor-lens-content-phase.md) | Anchor lens content phase (Plan Phase L1.1) | Accepted |
| [ADR-0073b](ADR-0073b-anchor-lens-class-loader.md) | Anchor lens class + loader (Plan Phase L1.2) | Accepted |
| [ADR-0073c](ADR-0073c-anchor-lens-composer-wiring.md) | First non-trivial lenses + composer wiring (Plan Phase L1.3) | Accepted |
| [ADR-0073d](ADR-0073d-anchor-lens-telemetry-tour.md) | Anchor-lens telemetry, CLI, and tour demo (Plan Phase L1.4) | Accepted |
| [ADR-0074](ADR-0074-orthogonality-tour.md) | Orthogonality tour: anchor-lens × register composition demo | Accepted |
| [ADR-0075](ADR-0075-realizer-slot-type-guard.md) | Realizer slot-type guard (C1: coherence floor) | Accepted |
| [ADR-0076](ADR-0076-confirmation-tag-normalization.md) | Confirmation-Tag Normalization (C2) | Accepted |
| [ADR-0077](ADR-0077-substantive-register-knobs.md) | Substantive register knobs + register-tour gate strengthening (R6) | Ratified |
| [ADR-0078](ADR-0078-composer-graph-atom-equivalence.md) | Composer/Graph atom equivalence telemetry | Ratified |
| [ADR-0078](ADR-0078-phase1-implementation-note.md) | ADR-0078 Phase 1 — Pre-Implementation Planning Note | — |
| [ADR-0080](ADR-0080-contemplation-loop.md) | Contemplation Loop: self-interrogation without self-ratification | Accepted |
| [ADR-0083](ADR-0083-transitive-chain-surface.md) | Transitive Chain Surface (Bounded Multi-Hop Composition) | Accepted |
| [ADR-0084](ADR-0084-definitional-layer.md) | Definitional Layer for Lexicon Packs | Proposed |
| [ADR-0085](ADR-0085-gloss-aware-cause.md) | Gloss-Aware CAUSE Composer | Accepted |
| [ADR-0087](ADR-0087-rhetorical-style-axis.md) | Rhetorical Style as Selection Axis (Pre-Work for Writing Curriculum) | Proposed |
| [ADR-0091](ADR-0091-domain-pack-contract-v1.md) | Domain Pack Contract v1 | Accepted |
| [ADR-0092](ADR-0092-reviewer-registry-v1.md) | Reviewer Registry v1 | Accepted |
| [ADR-0093](ADR-0093-domain-pack-contract-v1-implementation.md) | Domain Pack Contract v1 Implementation | Accepted |
| [ADR-0094](ADR-0094-proposal-source-provenance.md) | Proposal Source Provenance | Accepted |
| [ADR-0095](ADR-0095-miner-sourced-teaching-proposals.md) | Miner-Sourced Teaching Proposals | Accepted |
| [ADR-0096](ADR-0096-fabrication-control-eval-lane.md) | Fabrication-Control Eval Lane | Accepted |
| [ADR-0097](ADR-0097-mathematics-logic-reasoning-capable-ratification.md) | Mathematics-Logic Reasoning-Capable Ratification | Accepted |
| [ADR-0098](ADR-0098-demo-composition-contract.md) | Demo Composition Contract | Accepted |
| [ADR-0099](ADR-0099-public-showcase-demo.md) | Public Showcase Demo | Accepted |
| [ADR-0100](ADR-0100-physics-reasoning-capable-ratification.md) | Physics Reasoning-Capable Ratification | Accepted |
| [ADR-0101](ADR-0101-systems-software-reasoning-capable-ratification.md) | Systems-Software Reasoning-Capable Ratification | Accepted |
| [ADR-0102](ADR-0102-hebrew-greek-reasoning-capable-ratification.md) | Hebrew-Greek Textual-Reasoning Reasoning-Capable Ratification | Accepted |
| [ADR-0103](ADR-0103-fluency-lane-attachment-for-adr-0102.md) | Fluency Lane Attachment for ADR-0102 | Accepted |
| [ADR-0104](ADR-0104-curriculum-sourced-teaching-proposals.md) | Curriculum-Sourced Teaching Proposals | Accepted |
| [ADR-0105](ADR-0105-sealed-holdout-encryption.md) | Sealed Holdout Encryption via age | Accepted (2026-05-22) |
| [ADR-0106](ADR-0106-expert-demo-promotion-contract.md) | Expert-Demo Promotion Contract | Accepted |
| [ADR-0107](ADR-0107-mathematics-logic-expert-demo-deferred.md) | `mathematics_logic` Expert-Demo Promotion: Deferred | Accepted (decision: defer promotion) |
| [ADR-0108](ADR-0108-proposed-adr-sequencing.md) | Proposed-ADR Sequencing Post-ADR-0105 | Accepted |
| [ADR-0109](ADR-0109-lane-shape-aware-thresholds.md) | Lane-Shape-Aware Thresholds (ADR-0106 Amendment) | Accepted |
| [ADR-0110](ADR-0110-mathematics-logic-expert-demo-promotion.md) | `mathematics_logic` Expert-Demo Promotion | Accepted |
| [ADR-0111](ADR-0111-physics-expert-demo-promotion.md) | `physics` Expert-Demo Promotion | Accepted |
| [ADR-0112](ADR-0112-runnable-expert-demo-showcase.md) | Runnable Expert-Demo Showcase | Accepted |
| [ADR-0113](ADR-0113-rename-expert-demo-to-audit-passed.md) | Rename `expert-demo` → `audit-passed`; Reserve `expert` for Future Capability Tier | Accepted |
| [ADR-0114](ADR-0114-expert-capability-roadmap-gsm8k-first.md) | Expert-Capability Roadmap: GSM8K-Math First | Proposed |
| [ADR-0114a](ADR-0114a-anti-overfitting-proof-obligations.md) | Anti-Overfitting Proof Obligations for `expert` Promotion | Accepted (documentation-only; no code change) |
| [ADR-0114a.2](ADR-0114a.2-ood-ratio-auditor.md) | OOD-Ratio Auditor (Obligation #2 wired for B3) | Accepted |
| [ADR-0114a.5](ADR-0114a.5-perturbation-suite.md) | Reasoning-Isolation Perturbation Suite (Obligation #5, B3) | Accepted |
| [ADR-0114a.6](ADR-0114a.6-depth-curve-auditor.md) | Compositional-Depth Curve Auditor (Obligation #6 wired for B3) | Accepted (mechanism); coverage gap deferred to B3-owner follow-up |
| [ADR-0114a.8](ADR-0114a.8-adversarial-auditor.md) | Adversarial Generation Auditor (Obligation #8 wired) | Accepted (obligation passes; surfaces 2 known parser-layer gaps) |
| [ADR-0114a.10](ADR-0114a.10-pack-provenance-auditor.md) | Pack-Provenance Auditor (Obligation #10 wired for B3) | Accepted |
| [ADR-0115](ADR-0115-math-problem-parser-and-graph.md) | Math Problem Parser and Typed Proposition Graph | Phase 1.1 Accepted (schema + 5 seed cases + tests); Phases 1.2–1.4 In Progress |
| [ADR-0116](ADR-0116-deterministic-solver.md) | Deterministic Solver (`MathProblemGraph` → `SolutionTrace`) | Accepted |
| [ADR-0117](ADR-0117-solution-trace-verifier.md) | `SolutionTrace` Verifier | Accepted |
| [ADR-0118](ADR-0118-stepped-realizer.md) | Stepped Realizer (`SolutionTrace` → Prose) | Accepted |
| [ADR-0118a](ADR-0118a-ood-surface-generator.md) | OOD Surface Generator for GSM8K-Style Parser Dev | Accepted |
| [ADR-0119](ADR-0119-gsm8k-eval-lane-roadmap.md) | GSM8K Eval Lane Roadmap (Phase 5) | Proposed (roadmap-only) |
| [ADR-0119.1](ADR-0119.1-sealed-holdout-fabrication-control.md) | Seal fabrication_control Holdout (ADR-0105 Amendment) | Accepted |
| [ADR-0119.2](ADR-0119.2-gsm8k-eval-corpus-dev-public.md) | GSM8K Eval Corpus Dev/Public Splits | Accepted |
| [ADR-0119.3](ADR-0119.3-lane-runner.md) | gsm8k_math Lane Runner (Phase 5.3) | Accepted |
| [ADR-0119.4](ADR-0119.4-frontier-baseline-comparison.md) | GSM8K Math: Frontier-Baseline Comparison (ADR-0114a §Obligation #7) | Accepted |
| [ADR-0119.5](ADR-0119.5-adversarial-generation.md) | Adversarial Generation (ADR-0114a Obligation #8) | Accepted |
| [ADR-0119.6](ADR-0119.6-depth-curve-harness.md) | GSM8K Math Depth-Curve Measurement Harness | Accepted |
| [ADR-0119.7](ADR-0119.7-sealed-gsm8k-test.md) | Sealed GSM8K Test Set as gsm8k_math Holdout | Accepted |
| [ADR-0119.8](ADR-0119.8-lane-gate.md) | gsm8k_math Overall Lane Gate (`gsm8k_capability_shape`) | Accepted |
| [ADR-0120](ADR-0120-expert-promotion-contract.md) | First `expert` Promotion Contract | Proposed (contract-only; no domain promoted with this ADR) |
| [ADR-0120](ADR-0120-math-expert-ledger-flip.md) | ADR-0120 (math, ledger flip) — Mathematics-Logic Domain Promoted to `expert` | Accepted — first `expert`-tier domain in the capability ledger |
| [ADR-0120](ADR-0120-math-expert-promotion-wireup.md) | ADR-0120 (math) — Math-Expert Promotion Composer Wire-Up | Accepted (technical pass on first evaluation; awaiting reviewer signature for ledger admission) |
| [ADR-0121](ADR-0121-mathematics-logic-expert-deferred.md) | `mathematics_logic` `expert` Promotion — Deferred (first attempt) | Accepted (the deferral is the decision) |
| [ADR-0122](ADR-0122-parser-rate-per-unit.md) | Parser Expansion: Rate / Per-Unit Reasoning (substrate-only; lift deferred) | Accepted (substrate landed; sealed-lift gate deferred — the |
| [ADR-0122](ADR-0122-systems-software-audit-passed-deferred.md) | `systems_software` Audit-Passed Promotion: Deferred | Accepted (decision: defer promotion) |
| [ADR-0123](ADR-0123-parser-comparison-phrasing.md) | Comparison-Phrasing Realizer (surface increment on the ADR-0123 substrate) | Accepted (surface increment; substrate landed in PR #155) |
| [ADR-0123](ADR-0123-symbolic-logic-shape-remap.md) | `symbolic_logic` Lane-Shape Remap (ADR-0109 Amendment) | Accepted |
| [ADR-0123a](ADR-0123a-inference-shape-synonym.md) | `all_three_pass_rate` Synonym in `inference_shape` (ADR-0109 Amendment) | Accepted |
| [ADR-0124](ADR-0124-systems-software-audit-passed-promotion.md) | `systems_software` Audit-Passed Promotion | Accepted |
| [ADR-0125](ADR-0125-reasoning-isolation-perturbation-suite.md) | Reasoning-Isolation Perturbation Suite | Accepted |
| [ADR-0126](ADR-0126-candidate-graph-parser.md) | Candidate-Graph Parser with Round-Trip Verifier-Filter | Proposed |
| [ADR-0127](ADR-0127-0128-RESULTS.md) | ADR-0127 + ADR-0128 Results — Path-B Triggered | Empirical result; load-bearing for the GSM8K-math arc decision |
| [ADR-0127](ADR-0127-units-pack-and-units-aware-parser.md) | `en_units_v1` Pack + Units-Aware Candidate Extractors | Proposed (scope-only; implementation follow-up to ADR-0126) |
| [ADR-0128](ADR-0128-numerics-pack.md) | `en_numerics_v1` Pack | Proposed (scope-only; sibling to ADR-0127) |
| [ADR-0129](ADR-0129-spaced-correction-replay-deferred.md) | Spaced Reviewed-Correction Replay (Deferred Proposal) | Proposed — Deferred (backlog item; no implementation |
| [ADR-0130](ADR-0130-pre-articulation-calibration-deferred.md) | Pre-Articulation Calibration Logging (Deferred Proposal) | Proposed — Deferred (backlog item; no implementation |
| [ADR-0131](ADR-0131-math-expert-rebench.md) | Re-Target Math Expert Promotion to Architecture-Aligned Benchmarks | Proposed |
| [ADR-0131.1.F](ADR-0131.1.F-frontier-baseline-comparison.md) | B1 Symbolic Equivalence: Frontier-Baseline Comparison | Proposed |
| [ADR-0131.1.S](ADR-0131.1.S-sealed-holdout.md) | Sealed Holdout for Benchmark 1 (Symbolic Equivalence v1) | Accepted |
| [ADR-0131.2](ADR-0131.2-teaching-corpus-eval.md) | Benchmark 2: CORE-native teaching-corpus eval (lane gate) | Accepted |
| [ADR-0131.2.B](ADR-0131.2.B-teaching-corpus-enrichment.md) | Benchmark 2: B2 teaching-corpus enrichment (load-bearing gate) | Accepted |
| [ADR-0131.3](ADR-0131.3-bounded-grammar.md) | Benchmark 3: Bounded-Grammar Word Problems | — |
| [ADR-0131.4](ADR-0131.4-composite-math-gate.md) | Composite Math-Expert Promotion Gate (wired) | Accepted |
| [ADR-0131.5](ADR-0131.5-gsm8k-probe-retirement.md) | GSM8K Coverage Probe: Retirement After G.x Axis Completion | Accepted |
| [ADR-0131.G](ADR-0131.G-gsm8k-coverage-probe.md) | GSM8K Coverage Probe: Honest Measurement Under the Safety Rail | Proposed |
| [ADR-0131.G.0](ADR-0131.G.0-probe-substrate.md) | Probe Substrate: Candidate-Graph Pipeline | Proposed |
| [ADR-0131.G.1](ADR-0131.G.1-verb-classes-initial-state.md) | Capability axis: state-introducing verb classes | Accepted |
| [ADR-0131.G.2](ADR-0131.G.2-comparatives.md) | Capability axis: comparative operations (additive + multiplicative) | Proposed |
| [ADR-0131.G.3](ADR-0131.G.3-numerics.md) | Numeric Literals (money + hyphenated cardinals) | Proposed |
| [ADR-0131.G.3.1](ADR-0131.G.3.1-numerics-extensions.md) | Numerics extensions (fractions + multi-currency + multi-token cardinals + word-num-adjective) | Proposed |
| [ADR-0131.G.4](ADR-0131.G.4-multi-clause.md) | Capability axis: multi-clause composition (conjoined subjects, conjoined objects, embedded quantifiers) | Proposed |
| [ADR-0131.G.5](ADR-0131.G.5-aggregate-answer-composition.md) | Aggregate Answer Composition | Accepted |
| [ADR-0132](ADR-0132-binding-graph-data-model.md) | Semantic-Symbolic Binding Graph: Phase 1 data model | Accepted (Phase 1 only; Phases 2–5 deferred) |
| [ADR-0133](ADR-0133-binding-graph-adapter.md) | Semantic-Symbolic Binding Graph: Phase 2 adapter from `MathProblemGraph` | Accepted (Phase 2 only; Phases 3–5 deferred) |
| [ADR-0134](ADR-0134-binding-graph-admissibility.md) | Binding Graph Phase 3: Unit-Aware Equation Admissibility | accepted |
| [ADR-0135](ADR-0135-binding-graph-question-target.md) | Binding Graph Phase 4: question-target binding refinement | Accepted. |
| [ADR-0136](ADR-0136-statement-layer-corridor.md) | Statement-Layer Corridor: Graduated GSM8K Admission via Parser Extension | Active — *Regex sentence-template prescription superseded by [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) (2026-05-26). Empirical taxonomies preserved.* |
| [ADR-0136.S.1](ADR-0136.S.1-rate-event-statements.md) | Rate/Event Statement Parsing | Accepted — *regex patterns scheduled for removal under [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) Phase 3; closed-set vocabulary preserved as lexicon seed* |
| [ADR-0136.S.2](ADR-0136.S.2-conditional-op-question.md) | Conditional-Op Question (Statement-Layer Corridor) | Active — *regex patterns scheduled for removal under [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) Phase 3; closed-set vocabulary preserved as lexicon seed* |
| [ADR-0136.S2](ADR-0136.S2-post-rescan.md) | post-rescan — Refusal Rescan v2: Barrier-Shift Ledger | Accepted |
| [ADR-0136.S3](ADR-0136.S3-compound-initial-mutation.md) | Compound Initial-Mutation Extractor | Accepted — *regex patterns scheduled for removal under [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) Phase 3; closed-set vocabulary preserved as lexicon seed* |
| [ADR-0136.S3](ADR-0136.S3-post-rescan.md) | post-rescan — Refusal Rescan v3: Barrier-Shift Ledger | Accepted |
| [ADR-0136.S.4](ADR-0136.S.4-novel-initial-form.md) | Novel Initial-Form Subject-Slot Widenings | Accepted — *regex patterns scheduled for removal under [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) Phase 3; closed-set vocabulary preserved as lexicon seed* |
| [ADR-0138](ADR-0138-comparative-reference-layer.md) | Comparative-Reference Layer | Draft (design-only) |
| [ADR-0139](ADR-0139-arithmetic-as-versor-spike.md) | Arithmetic-as-Versor Spike: `add` Only | Draft |
| [ADR-0140](ADR-0140-core-trace-protocol-v0.md) | CORE Trace Protocol v0 | Proposed |
| [ADR-0140](ADR-0140-subtract-and-additive-group-closure.md) | `subtract` as Inverse Translator + Additive Group Closure | Draft |
| [ADR-0141](ADR-0141-multiply-as-dilator-positive-nonzero.md) | `multiply` as Dilator (Positive Non-Zero Multipliers Only) | Draft |
| [ADR-0142](ADR-0142-epistemic-state-taxonomy.md) | Epistemic State Taxonomy — First-Class Vocabulary | Accepted (integration deferred pending ADR-0144) |
| [ADR-0143](ADR-0143-recognition-spike-anti-unification.md) | Teaching-Derived Structural Recognition via Multi-Resolution Anti-Unification | Accepted |
| [ADR-0144](ADR-0144-proposition-graph-epistemic-carrier.md) | PropositionGraph — Epistemic Carrier and Recognition Integration Gate | Accepted |
| [ADR-0145](ADR-0145-energy-modulated-surface-readback.md) | Energy-Modulated Vault Surface Readback | Accepted |
| [ADR-0146](ADR-0146-l10-hybrid-engine-state-persistence.md) | L10 Shape B Hybrid Engine-State Persistence | Accepted |
| [ADR-0148](ADR-0148-vault-promotion-policy-wiring.md) | Wire VaultPromotionPolicy into turn boundary | Accepted |
| [ADR-0149](ADR-0149-derived-recognizer-pipeline-wiring.md) | Integrate DerivedRecognizer into CognitiveTurnPipeline | Accepted |
| [ADR-0150](ADR-0150-autonomous-inter-session-contemplation.md) | Autonomous Inter-Session Contemplation | Accepted |
| [ADR-0151](ADR-0151-auto-proposal-pipeline.md) | Auto-Proposal Pipeline at Load | Accepted |
| [ADR-0152](ADR-0152-learning-arc-demo.md) | Learning-Arc Demo (`core demo learning-arc`) | — |
| [ADR-0153](ADR-0153-turn-event-trace-hash-backstamp.md) | TurnEvent trace_hash back-stamp (W-020a) | accepted |
| [ADR-0154](ADR-0154-recognizer-producer-wiring.md) | DerivedRecognizer producer wiring (W-020b) | accepted |
| [ADR-0155](ADR-0155-ci-contemplation-runner.md) | CI contemplation runner (W-021) | scoping |
| [ADR-0156](ADR-0156-atomic-engine-state-checkpoint.md) | Atomic engine-state checkpoint writes (W-022 / L10b.1) | accepted |
| [ADR-0157](ADR-0157-revision-mismatch-warning.md) | Revision-mismatch warning on engine-state load (W-023 / L10b.2) | accepted |
| [ADR-0158](ADR-0158-reboot-event-audit.md) | reboot_event audit trail entry (W-024 / L10b.3) | accepted |
| [ADR-0159](ADR-0159-contemplation-quality-eval.md) | Contemplation Quality Eval Lane (W-025) | Accepted |
| [ADR-0160](ADR-0160-core-workbench-v1.md) | CORE Workbench v1: operator/auditor UI before public chat | proposed |
| [ADR-0161](ADR-0161-hitl-async-queue.md) | HITL Async Queue (W-009, L11) | Proposed |
| [ADR-0162](ADR-0162-workbench-design-system.md) | Workbench Design System (v1) | Proposed |
| [ADR-0163](ADR-0163-F2-confuser-corpus-spec.md) | F2 — Confuser Corpus: a discrimination probe, not a coverage target | Proposed (spec only — no code). Follow-on to ADR-0163 §F (the Track-B |
| [ADR-0163](ADR-0163-gsm8k-path-to-mastery.md) | Path to GSM8K mastery: candidate-graph admissibility via the contemplation/HITL corridor | Proposed — *Phases B–E prescription superseded by [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) (2026-05-26)* |
| [ADR-0164](ADR-0164-incremental-comprehension-reader.md) | Incremental Comprehension Reader (replaces regex sentence-template parsing) | Partially implemented (Phase 1 + 2 shipped; eval delta pending lexicon expansion) |
| [ADR-0164.1](ADR-0164.1-lexical-primitive-scope.md) | Lexical Primitive Set Scope (seed registry for `en_core_math_v1`) | Proposed |
| [ADR-0164.2](ADR-0164.2-pronoun-entity-resolution.md) | Pronoun / Entity Resolution Policy | Proposed |
| [ADR-0164.3](ADR-0164.3-cross-sentence-state.md) | Cross-Sentence Reading State | Proposed |
| [ADR-0164.4](ADR-0164.4-phase2-statement-frame-reader.md) | Phase 2 Statement-Frame Reader | Proposed |
| [ADR-0165](ADR-0165-regex-scope-rule.md) | Regex Scope Rule: Lexemes Only, Never Grammar | Proposed |
| [ADR-0166](ADR-0166-measurement-capability-sequencing.md) | Measurement-Capability Sequencing Discipline | Proposed |
| [ADR-0167](ADR-0167-audit-as-teaching-evidence.md) | Audit-as-Teaching-Evidence (Math Reader → Contemplation) | Proposed (scoping ADR; no code in this PR) |
| [ADR-0168](ADR-0168-frameclaim-ratification.md) | FrameClaim Ratification Doctrine | Proposed (doctrine/scoping ADR; no runtime mutation in this PR) |
| [ADR-0168.1](ADR-0168.1-math-frameclaim-proposal-adapter.md) | MathFrameClaimProposal Adapter | Proposed (design bridge; no runtime FrameClaim admission in this PR) |
| [ADR-0169](ADR-0169-compositionclaim-ratification.md) | CompositionClaim Ratification Doctrine | Proposed (doctrine/scoping ADR; no runtime mutation in this PR) |
| [ADR-0169.1](ADR-0169.1-math-compositionclaim-proposal-adapter.md) | MathCompositionClaimProposal Adapter | Proposed (design bridge; no runtime CompositionClaim admission in this PR) |
| [ADR-0170](ADR-0170-injector-contract-widening.md) | Recognizer Injector Contract Widening | Proposed (scoping ADR; no runtime change in this PR) |
| [ADR-0172](ADR-0172-math-corpus-decomposition-mechanism.md) | Math-Domain Corpus-Decomposition Mechanism (Learning-Arc Analog) | Proposed (scoping ADR; no runtime change in this PR) |
| [ADR-0173](ADR-0173-workbench-ratification-trust-boundary.md) | Workbench Ratification Trust Boundary | Accepted (W0 of the workbench-UI wave; doctrine only — UI |
| [ADR-0174](ADR-0174-held-hypothesis-comprehension.md) | Held-Hypothesis Comprehension with Lookback and In-Loop Contemplation | Proposed |
| [ADR-0175](ADR-0175-calibrated-attempt-and-eliminate-learning.md) | Calibrated Attempt-and-Eliminate Learning: Two Regimes Under wrong=0 | Proposed |
| [ADR-0176](ADR-0176-multistep-composition-question-targeting.md) | Multi-Step Grounded Composition with Question-Targeting | Proposed |
| [ADR-0177](ADR-0177-cue-precision-learning.md) | Cue-Precision Learning: from practice eliminations to trusted cue→op patterns | Proposed |
| [ADR-0178](ADR-0178-GB3b-referent-accumulation-scope.md) | ADR-0178 GB-3b — referent-aware accumulation chaining (scope) | Proposed (scope only — no code). Sub-phase of |
| [ADR-0178](ADR-0178-compositional-structure.md) | Compositional Structure: Comprehension-Guided Multi-Step Derivation (Gap B) | Proposed |
| [ADR-0179](ADR-0179-extraction-richness.md) | Extraction Richness: feeding the comprehension composer real quantities | Proposed |
| [ADR-0180](ADR-0180-crdt-sharded-vault-concurrency.md) | Delta-CRDT Sharded Substrate for Multimodal Concurrency | Accepted (2026-05-31 — G1 reference-contract lock) |
| [ADR-0181](ADR-0181-audio-compiler-delta-crdt.md) | CORE-native Audio Compiler over the Delta-CRDT Substrate | Proposed |
| [ADR-0182](ADR-0182-cross-composer-disagreement-pooling.md) | Cross-composer disagreement pooling: refuse distractor-quantity confusers without a reactive cue rule | Proposed (spec only — no code). Follow-on to |
| [ADR-0183](ADR-0183-lawful-audio-lexeme-path.md) | Lawful Audio→Lexeme Path (stub) | Proposed (stub — placeholder to record the fork; not yet a full design) |
| [ADR-0184](ADR-0184-distinct-unit-product-rule.md) | Distinct-unit product rule: cut the product-of-all over-commit | Accepted / Implemented |
| [ADR-0185](ADR-0185-division-reading.md) | Division reading (rate / partition): eliminate-then-solve | Superseded by [ADR-0186](ADR-0186-sealed-candidate-graph-injector-lane.md) |
| [ADR-0186](ADR-0186-sealed-candidate-graph-injector-lane.md) | Sealed candidate-graph injector lane: resume ADR-0170 W2–W5 under the ADR-0175 seal | Proposed (scoping + seal-mechanism ADR; first injector ships behind the seal) |
| [ADR-0189](ADR-0189-comparative-verb-unit-widening.md) | Comparative reading: anchor-verb widening + multi-word units | Proposed (implemented in this PR) |
| [ADR-0191](ADR-0191-candidate-graph-completeness-guard.md) | Candidate-graph completeness guard (the missing wrong=0 leg) | Proposed (implemented in this PR) |
| [ADR-0192](ADR-0192-discrete-count-open-noun-class.md) | Open the discrete_count counted-noun class (firewall-backed) | Proposed (implemented in this PR) |
| [ADR-0193](ADR-0193-aggregate-existential-question-frame.md) | Aggregate total-across: the existential question frame | Proposed (implemented in this PR) |
| [ADR-0194](ADR-0194-labeled-container-subject.md) | Labeled-container subject entity shape | Proposed (implemented in this PR) |
| [ADR-0195](ADR-0195-product-promotion-bridge.md) | Product Promotion Bridge | Accepted / Implemented |
| [ADR-0196](ADR-0196-native-substrate-language-doctrine.md) | Native Substrate Language Doctrine (Python / Rust / Zig) | Accepted (2026-05-31) |
| [ADR-0197](ADR-0197-vision-compiler-delta-crdt.md) | CORE-native Vision Compiler over the Delta-CRDT Substrate | Proposed |
| [ADR-0198](ADR-0198-motor-efferent-decoder-spike.md) | Motor as Efferent Modality — Protocol Gap & Governance (Design Spike) | Proposed (design spike — no implementation) |
| [ADR-0199](ADR-0199-cross-domain-learning-arena-contract.md) | Cross-Domain Learning Arena Contract | Proposed |

---

## Current frontier

_Current as of 2026-05-29 (ADR-0183)._

The development frontier has moved beyond the audit-passed foundations (ADR-0091–0125) into native multi-modal execution and autonomous calibration. Key active arcs include:

- **Auditory Modality & CRDT Substrate (ADR-0180, ADR-0181, ADR-0183)**: Shifting from text-only to concurrent multi-modal pipelines. Introduces a lock-free Delta-CRDT shared vault substrate to eliminate thread contention under continuous vision/audio ingestion, and ships `audio_core_v1` as a deterministic acoustic compiler lowerable to unit-versors. ADR-0183 stubs the serving-time ASR boundary, ensuring lexical extraction is either text-side or deterministically decoded under `wrong=0`.
- **Calibrated Attempt-and-Eliminate Learning (ADR-0175)**: Establishes a formal precision-only reliability ledger and ratio-gate using the one-sided Wilson lower bound (`conservative_floor`). It separates the safe serving regime (`wrong=0`) from a sealed practice regime where failures are treated as elimination signals to prune the solver's search.
- **Incremental Comprehension & Verification (ADR-0164, ADR-0174)**: Transitioned sentence extraction from brittle regex sentence templates to a deterministic incremental reader based on shift-reduce over semantic categories. The reader is backed by held-hypothesis evaluation, lookback, and in-loop contemplation.
- **Measurement & Evaluation Discipline (ADR-0166, ADR-0163-F2)**: Establishes the `capability-before-measurement` rule to ensure eval lanes are only built when operators exist and can admit at least one case. F2 defines a confuser corpus discrimination probe rather than a mere coverage target.

### Proposed-but-unimplemented ADRs

The following ADRs carry a status of **Proposed** in the Index:

#### Core Infrastructure & Metadata
- [ADR-0084](ADR-0084-definitional-layer.md) — Definitional Layer for Lexicon Packs
- [ADR-0087](ADR-0087-rhetorical-style-axis.md) — Rhetorical Style Axis
- [ADR-0129](ADR-0129-spaced-correction-replay-deferred.md) — Spaced Reviewed-Correction Replay (Deferred Proposal)
- [ADR-0130](ADR-0130-pre-articulation-calibration-deferred.md) — Pre-Articulation Calibration Logging (Deferred Proposal)
- [ADR-0140](ADR-0140-core-trace-protocol-v0.md) — CORE Trace Protocol v0

#### Auditory Modality & Delta-CRDT Concurrency
- [ADR-0180](ADR-0180-crdt-sharded-vault-concurrency.md) — Delta-CRDT Sharded Substrate for Multimodal Concurrency
- [ADR-0181](ADR-0181-audio-compiler-delta-crdt.md) — CORE-native Audio Compiler over the Delta-CRDT Substrate
- [ADR-0183](ADR-0183-lawful-audio-lexeme-path.md) — Lawful Audio→Lexeme Path (stub)

#### Expert Promotion & Evaluation (Math/GSM8K)
- [ADR-0114](ADR-0114-expert-capability-roadmap-gsm8k-first.md) — Expert-Capability Roadmap: GSM8K-Math First
- [ADR-0119](ADR-0119-gsm8k-eval-lane-roadmap.md) — GSM8K Eval Lane Roadmap (Phase 5)
- [ADR-0120](ADR-0120-expert-promotion-contract.md) — First `expert` Promotion Contract
- [ADR-0131](ADR-0131-math-expert-rebench.md) — Re-Target Math Expert Promotion to Architecture-Aligned Benchmarks
- [ADR-0131.1.F](ADR-0131.1.F-frontier-baseline-comparison.md) — B1 Symbolic Equivalence: Frontier-Baseline Comparison
- [ADR-0131.G](ADR-0131.G-gsm8k-coverage-probe.md) — GSM8K Coverage Probe: Honest Measurement Under the Safety Rail
- [ADR-0131.G.0](ADR-0131.G.0-probe-substrate.md) — Probe Substrate: Candidate-Graph Pipeline
- [ADR-0131.G.2](ADR-0131.G.2-comparatives.md) — Capability axis: comparative operations (additive + multiplicative)
- [ADR-0131.G.3](ADR-0131.G.3-numerics.md) — Numeric Literals (money + hyphenated cardinals)
- [ADR-0131.G.3.1](ADR-0131.G.3.1-numerics-extensions.md) — Numerics extensions (fractions + multi-currency + multi-token cardinals + word-num-adjective)
- [ADR-0131.G.4](ADR-0131.G.4-multi-clause.md) — Capability axis: multi-clause composition (conjoined subjects, conjoined objects, embedded quantifiers)
- [ADR-0163](ADR-0163-F2-confuser-corpus-spec.md) — F2 — Confuser Corpus: a discrimination probe, not a coverage target
- [ADR-0163](ADR-0163-gsm8k-path-to-mastery.md) — Path to GSM8K mastery: candidate-graph admissibility via the contemplation/HITL corridor

#### Incremental Comprehension Reader & Skill Acquisition
- [ADR-0126](ADR-0126-candidate-graph-parser.md) — Candidate-Graph Parser with Round-Trip Verifier-Filter
- [ADR-0127](ADR-0127-units-pack-and-units-aware-parser.md) — `en_units_v1` Pack + Units-Aware Candidate Extractors
- [ADR-0128](ADR-0128-numerics-pack.md) — `en_numerics_v1` Pack
- [ADR-0164.1](ADR-0164.1-lexical-primitive-scope.md) — Lexical Primitive Set Scope (seed registry for `en_core_math_v1`)
- [ADR-0164.2](ADR-0164.2-pronoun-entity-resolution.md) — Pronoun / Entity Resolution Policy
- [ADR-0164.3](ADR-0164.3-cross-sentence-state.md) — Cross-Sentence Reading State
- [ADR-0164.4](ADR-0164.4-phase2-statement-frame-reader.md) — Phase 2 Statement-Frame Reader
- [ADR-0165](ADR-0165-regex-scope-rule.md) — Regex Scope Rule: Lexemes Only, Never Grammar
- [ADR-0166](ADR-0166-measurement-capability-sequencing.md) — Measurement-Capability Sequencing Discipline
- [ADR-0167](ADR-0167-audit-as-teaching-evidence.md) — Audit-as-Teaching-Evidence (Math Reader → Contemplation)
- [ADR-0168](ADR-0168-frameclaim-ratification.md) — FrameClaim Ratification Doctrine
- [ADR-0168.1](ADR-0168.1-math-frameclaim-proposal-adapter.md) — MathFrameClaimProposal Adapter
- [ADR-0169](ADR-0169-compositionclaim-ratification.md) — CompositionClaim Ratification Doctrine
- [ADR-0169.1](ADR-0169.1-math-compositionclaim-proposal-adapter.md) — MathCompositionClaimProposal Adapter
- [ADR-0170](ADR-0170-injector-contract-widening.md) — Recognizer Injector Contract Widening
- [ADR-0172](ADR-0172-math-corpus-decomposition-mechanism.md) — Math-Domain Corpus-Decomposition Mechanism (Learning-Arc Analog)
- [ADR-0174](ADR-0174-held-hypothesis-comprehension.md) — Held-Hypothesis Comprehension with Lookback and In-Loop Contemplation
- [ADR-0175](ADR-0175-calibrated-attempt-and-eliminate-learning.md) — Calibrated Attempt-and-Eliminate Learning: Two Regimes Under wrong=0
- [ADR-0176](ADR-0176-multistep-composition-question-targeting.md) — Multi-Step Grounded Composition with Question-Targeting
- [ADR-0177](ADR-0177-cue-precision-learning.md) — Cue-Precision Learning: from practice eliminations to trusted cue→op patterns
- [ADR-0178](ADR-0178-GB3b-referent-accumulation-scope.md) — ADR-0178 GB-3b — referent-aware accumulation chaining (scope)
- [ADR-0178](ADR-0178-compositional-structure.md) — Compositional Structure: Comprehension-Guided Multi-Step Derivation (Gap B)
- [ADR-0179](ADR-0179-extraction-richness.md) — Extraction Richness: feeding the comprehension composer real quantities
- [ADR-0182](ADR-0182-cross-composer-disagreement-pooling.md) — Cross-composer disagreement pooling: refuse distractor-quantity confusers without a reactive cue rule

#### Workbench UI
- [ADR-0160](ADR-0160-core-workbench-v1.md) — CORE Workbench v1: operator/auditor UI before public chat
- [ADR-0161](ADR-0161-hitl-async-queue.md) — HITL Async Queue (W-009, L11)
- [ADR-0162](ADR-0162-workbench-design-system.md) — Workbench Design System (v1)

_Historical — accurate as of ADR-0125; see the Index for the complete, current list of domain promotions._

ADR-0080 (Contemplation Loop, Phase 1), ADR-0110 (math audit-passed), ADR-0111 (physics audit-passed), and ADR-0124 (systems_software audit-passed) have all landed — `mathematics_logic`, `physics`, and `systems_software` are at `audit_passed=true`; the contemplation loop emits read-only `SPECULATIVE` findings from `frontier_compare` reports. The remaining ratified domain (`hebrew_greek_textual_reasoning`) needs its own promotion ADR.

ADR-0122 attempted `systems_software` promotion and deferred honestly on a lane-shape contract mismatch (`symbolic_logic` output shape vs registered checker), resolved by ADR-0123's shape remap and successfully promoted via ADR-0124.

### Open candidate directions (no ADR yet)

_Historical — accurate as of ADR-0125; see the Index for the complete, current list._

- **Multi-reviewer holdout governance and threshold signing.** ADR-0105 seals holdout payloads with a single recipient identity; multi-reviewer governance remains future work.

---

## Accepted reasoning-capable domains

_Historical — accurate as of ADR-0125; see the Index for the complete, current list of domain promotions._

Per ADR-0106, `audit_passed` is **contract-gated**, not threshold-only: a domain row may carry `audit_passed=true` only when a reviewer-signed `audit_passed_claims` entry exists whose evidence-bundle digest reproduces byte-for-byte. ADR-0107 attempted the first worked promotion and the contract refused; ADR-0109 amended the threshold rules; ADR-0110 then successfully promoted `mathematics_logic` (the first domain at `audit_passed=true`); ADR-0111 promoted `physics` second without further contract change, retiring the "math-only" objection. The other two ratified domains remain at `reasoning-capable` pending their own promotion ADRs.

| Domain | Ratification ADR | Pack(s) | Evidence summary |
|---|---|---|---|
| `mathematics_logic` | ADR-0097 + ADR-0110 | `en_mathematics_logic_v1` | All nine ADR-0091 predicates pass; ledger row is **`audit-passed`** (first such promotion, ADR-0110); all three attached lanes meet ADR-0109 shape thresholds on public + holdout. |
| `physics` | ADR-0100 + ADR-0111 | `en_physics_v1` | All nine predicates pass; causal/modal operator coverage meets threshold; ledger row is **`audit-passed`** (second such promotion, ADR-0111); `foundational_physics_ood` 117/117 public + 39/39 holdout; shares `inference_closure` + `fabrication_control` results with math (distinct digest via `domain_id`). |
| `systems_software` | ADR-0101 + ADR-0124 | `en_systems_software_v1` | All nine predicates pass; transitive/causal operator coverage meets threshold; ledger row is **`audit-passed`** (third promotion, ADR-0124); all three attached lanes meet thresholds on public + holdout. |
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

### Comprehension-reader pivot — ADR-0164 and ADR-0165 (2026-05-26)

The GSM8K admissibility front-end is replaced. The regex sentence-template
parsing layer in `generate/math_candidate_parser.py` and
`generate/recognizer_match.py` is recognized as overfitting by
construction — it enumerates memorized surface shapes while pretending to
encode a closed grammar that English does not have.

- **[ADR-0164](ADR-0164-incremental-comprehension-reader.md)** —
  Incremental Comprehension Reader. Word-by-word state accumulation over a
  closed set of semantic categories. The reader is a deterministic
  shift-reduce parser over *categories*, not over tokens. Output type is
  identical to the regex parser's output, so the binding-graph
  admissibility (ADR-0132/0133/0134/0135) downstream is unchanged.
  Operational lexicon lives in `language_packs/data/en_core_math_v1/`
  alongside the existing packs.

- **[ADR-0165](ADR-0165-regex-scope-rule.md)** — Regex Scope Rule.
  Structural invariant: regex is permitted only at the lexeme level
  (currency literal, fraction literal, percentage literal, time-amount,
  closed-set unit-noun), never at the sentence-structure level. The
  primitive set is a closed registry grown through the same contemplation
  → proposal → HITL review corridor that grows vocabulary.

These ADRs preserve every load-bearing piece of the prior work: the
binding graph (ADR-0132–0135), the solver / verifier / realizer
substrate (ADR-0116–0118), the capability-axis lanes G1–G5 and S1, the
HITL corridor (ADR-0150 / 0152 / 0155 / 0161), the `wrong = 0` doctrine
and the replay-equivalence gate (ADR-0057, ADR-0114a). The
contemplation → proposal → review corridor architecture is reaffirmed
and its scope is generalized: it now ratifies lexicon entries,
categories, and lexeme primitives — not regex recognizers.

ADR-0163's *diagnosis* (the front-end is the bottleneck) is reaffirmed;
its *prescription* (Phases B–E recognizer production) is partially
superseded. ADR-0136 and its S-family have the same disposition.

### Measurement-Capability Sequencing — ADR-0166 (2026-05-27)

Establishes the structural sequencing invariant: capability (operators, rules) must land on `main` and admit at least one test case before the eval lanes that measure it can be authored. Prevents noise of 100% refusing lanes from masking actual development priorities.

### Calibrated learning and reliability — ADR-0175 through ADR-0177 (2026-05-28)

Establishes calibrated attempt-and-eliminate learning under a strict two-regime separation:
1. **Serving**: Safe production path requiring `wrong=0` via a strict, high-reliability Wilson lower bound gate.
2. **Practice**: Sealed evaluation path where mistakes serve as checkable elimination signals to prune solver paths.

### Multimodal Audio modality & CRDT substrate — ADR-0180 through ADR-0183 (2026-05-29)

Shifts the engine toward concurrent multi-modal pipelines. Decouples physical lock contention on vision/audio from the logical manifold using Delta-CRDT sharding in Rust (ADR-0180), implements `audio_core_v1` as a deterministic acoustic compiler (ADR-0181), and stubs ASR serving boundaries to prevent learned Whisper models from contaminating production serving paths (ADR-0183).

---

## Session Logs

Session logs record the decisions and rationale from individual working sessions. They are not ADRs — they are the narrative record that informed the ADRs.

| Date | File |
|---|---|
| 2026-05-12 | [SESSION-2026-05-12.md](SESSION-2026-05-12.md) |
| 2026-05-12 (addendum) | [SESSION-2026-05-12-b.md](SESSION-2026-05-12-b.md) |
| 2026-05-12 (language packs) | [SESSION-2026-05-12-language-packs-addendum.md](SESSION-2026-05-12-language-packs-addendum.md) |
| 2026-05-13 | [SESSION-2026-05-13.md](SESSION-2026-05-13.md) |
| 2026-05-26 (comprehension reader) | [SESSION-2026-05-26-comprehension-reader.md](SESSION-2026-05-26-comprehension-reader.md) |
| 2026-05-27 (parallel dispatch) | [SESSION-2026-05-27-adr-0167-parallel-dispatch.md](SESSION-2026-05-27-adr-0167-parallel-dispatch.md) |
| 2026-05-27 (tier 3 sequencing) | [SESSION-2026-05-27-tier3-sequencing.md](SESSION-2026-05-27-tier3-sequencing.md) |
