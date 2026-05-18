# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for the CORE project.

ADRs record significant architectural decisions: what was decided, why, what alternatives were considered, and what consequences follow. They are permanent records — superseded ADRs are archived, not deleted.

---

## Index

| ADR | Title | Status |
|---|---|---|
| [ADR-0001](ADR-0001-vocab-layer-invariants.md) | Vocab Layer Invariants | Accepted |
| [ADR-0002](ADR-0002-ingest-layer-design.md) | Ingest Layer Design (original) | **Archived** — superseded by ADR-0012 |
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
| [ADR-0044](ADR-0044-medical-clinical-ethics-pack.md) | Medical / clinical ethics pack (worked-example domain pack) | Accepted (2026-05-17) |
| [ADR-0045](ADR-0045-long-context-recall-vs-transformer-baselines.md) | Long-context recall: CORE vs transformer baselines | Accepted (2026-05-17) |
| [ADR-0046](ADR-0046-forward-graph-constraint.md) | PropositionGraph as forward AdmissibilityRegion + industry demos | Accepted (2026-05-18) |
| [ADR-0047](ADR-0047-wire-forward-graph-constraint.md) | Wire forward graph constraint into the chat hot path (opt-in) | Accepted (2026-05-18) |
| [ADR-0048](ADR-0048-pack-grounded-surface.md) | Pack-grounded surface for cold-start DEFINITION / RECALL | Accepted (2026-05-18) |
| [ADR-0049](ADR-0049-intent-subject-extraction.md) | Intent classifier head-noun subject extraction | Accepted (2026-05-18) |
| [ADR-0050](ADR-0050-pack-grounded-comparison.md) | Pack-grounded surface for cold-start COMPARISON | Accepted (2026-05-18) |
| [ADR-0051](ADR-0051-trust-boundary-hardening.md) | Trust-boundary hardening pass | Accepted (2026-05-18) |
| [ADR-0052](ADR-0052-teaching-grounded-surface.md) | Teaching-grounded surface for cold-start CAUSE / VERIFICATION | Accepted (2026-05-18) |
| [ADR-0053](ADR-0053-cognition-lane-closure.md) | Cognition lane closure: dev-driven corpus expansion + CORRECTION acknowledgement | Accepted (2026-05-18) |
| [ADR-0054](ADR-0054-vault-recall-indexing-batching.md) | Vault recall matrix-cache indexing + batched API; holdout split wired into eval CLI | Accepted (2026-05-18) |
| [ADR-0055](ADR-0055-inter-session-memory-discovery-promotion.md) | Inter-session memory: reviewed discovery promotion (phased design — DiscoveryCandidate, TeachingChainProposal, replay-equivalence gate); Phase A + Phase B Accepted | **Phase A + B Accepted**; C–E Proposed (2026-05-18) |
| [ADR-0056](ADR-0056-contemplation-loop-c1.md) | Contemplation loop (Phase C1): question decomposition, polarity (affirms/falsifies/undetermined), claim_domain typing (factual/relational/evaluative), sync-only by design | **Accepted** (2026-05-18, implemented `4eecf73`) |
| [ADR-0057](ADR-0057-teaching-chain-proposal-review.md) | Teaching-chain proposal + review + replay-equivalence gate (Phase C2): the only path to active-corpus extension; eligibility predicate; auto-reject on metric regression; operator accept/reject/withdraw; append-only proposal log | **Accepted** (2026-05-18) |
| [ADR-0058](ADR-0058-forward-graph-constraint-status.md) | `forward_graph_constraint` remains opt-in default-`False`; no identity pack flips it on; ADR-0047 null-lift on cognition lane promoted to CI-enforced invariant (regression test); identity-pack→`RuntimeConfig` composition deferred until at least one such preference shows lift | **Accepted** (2026-05-18) |
| [ADR-0059](ADR-0059-correction-pass-telemetry.md) | `ChatRuntime.correct()` emits a discriminated `"type": "correction"` JSONL event to the existing telemetry sink with `target_turn`, `records_count`, `turn_idxs_affected`, `max_delta_norm`, `mean_delta_norm`, SHA-256 correction-versor digest, pack ids — no raw versor coordinates; deterministic; no-op without sink | **Accepted** (2026-05-18) |

---

## ADR-0024 chain — Forward Semantic Control closure

ADR-0022 through ADR-0026 form a single coherent chain that closes
forward semantic control as a non-stochastic, replay-deterministic,
trace-evidenced mechanism.  Read in order:

1. **ADR-0022** — Forward Semantic Control.  Establishes the
   `AdmissibilityRegion` data structure (allowed indices, relation
   blade, frame versor) and the contract that a region restricts the
   admissible token set at generation time.
2. **ADR-0023** — Proof Evidence.  Boundary-only proof that the
   admissibility region is honored at the *region intersection* level
   but not yet at the destination-token level.
3. **ADR-0024** — Inner-Loop Per-Rotor Admissibility.  Adds the
   destination-side check: each per-step selection is re-evaluated by
   `cga_inner(versor(candidate), relation_blade) > threshold`, with
   honest refusal (`InnerLoopExhaustion`) when every admissible
   candidate is rejected.  Six phases of implementation evidence
   (Phases 1-6) plus typed `RefusalReason` taxonomy.
4. **ADR-0025** — Rotor / Frame Admissibility.  Adds the rotor-side
   check: when a region carries a `frame_versor`, the rotor's effect
   on the field state (`versor_apply(V, F)`) is additionally checked
   against the frame for positivity in CGA inner product.  Lives in
   `generate/rotor_admissibility.py` — a sibling-but-separate module,
   not in `algebra/versor.py` (would couple algebra to pack state)
   and not in `field/propagate.py` (forbidden normalization site).
5. **ADR-0026** — Ranked Admissibility with Margin.  Replaces static
   threshold tuning with a scale-invariant margin gate: admit iff
   the top blade-score exceeds the second by ≥ δ.  Defaults to
   δ = 0.4.  Falsifiable; characterization documented in
   `docs/evals/phase5_stratified_findings.md`.

Implementation evidence:

| Phase | Commit | Tests |
|---|---|---|
| Phase 1 — pack-grounded fixtures | `3940290` | (rewrites) |
| Phase 2 — typed refusals + trace fold | `310793a` | +10 |
| Phase 3 — ranked-with-margin gate | `639e107` | +13 |
| Phase 4 — rotor / frame admissibility | `542e13d` | +11 |
| Phase 5 — stratified mechanism-isolation | `b664984` | +20 |
| Phase 6 — comparative demo vs baseline | `a076506` | +17 |
| CLI surface (suite aliases + `core demo`) | `36aad75` | +14 |

Runtime contracts for the chain are pinned in
[`docs/runtime_contracts.md`](../runtime_contracts.md) (Refusal
contract, Margin contract, Rotor admissibility contract sections).

---

## Pack-Layer chain — ADR-0027 through ADR-0045

ADR-0027 through ADR-0045 form the second coherent chain in the
project: a load-bearing three-tier pack architecture (identity /
safety / ethics) with deterministic remediation, full-stream audit,
machine-readable telemetry, an operator-facing CLI readout, and an
investor-facing walkthrough.  Read in order:

| Group | ADRs | What it adds |
|---|---|---|
| **Identity** | ADR-0027 / ADR-0028 | Identity manifold loads from a swappable JSON pack at composition time.  Pack carries `surface_preferences` that visibly drive hedging and claim strength. |
| **Identity surface refinements** | ADR-0030 / ADR-0031 | Depth-language hedge; score-decomposition surface. |
| **Safety** | ADR-0029 / ADR-0032 | Five universal safety boundaries unioned into every runtime manifold; SafetyCheck registry-of-predicates surface (observational). |
| **Ethics** | ADR-0033 / ADR-0034 | Third pack tier — deployment commitments, swappable like identity but propositional like safety; EthicsCheck predicate surface. |
| **Turn-loop wiring** | ADR-0035 | Both checks auto-invoked at end of every turn; verdicts attached to `ChatResponse` and `TurnEvent`. |
| **Remediation tiers** | ADR-0036 / ADR-0037 / ADR-0038 | Safety-only typed refusal → per-commitment ethics refusal opt-in → hedge injection.  Three tiers per ethics commitment: audit / hedge / refuse. |
| **Audit completeness** | ADR-0039 | `TurnVerdicts` bundle + stub-path `TurnEvent` emission + `refusal_emitted` / `hedge_injected` flags.  `rt.turn_log` covers every turn. |
| **Machine + operator surfaces** | ADR-0040 / ADR-0041 | Structured JSONL sink with redact-by-default trust boundary; `FanOutSink` composer; `core chat --show-verdicts` operator readout. |
| **Demo** | ADR-0042 | `core demo audit-tour` — four-scene investor-facing walkthrough; test-gated `all_claims_supported` flag. |
| **Phase-2 measurements** | ADR-0043 | Pack-driven identity-divergence + refusal-calibration runners convert load-bearing claims into CI-enforced numbers across the three ratified packs; combined report at `evals/results/phase2_pack_measurements.json`. |
| **Worked-example domain pack** | ADR-0044 | `medical_clinical_ethics_v1` — six commitments across all three remediation tiers (refuse / hedge / audit); ratified end-to-end through `scripts/ratify_ethics_pack.py`; composes into the runtime manifold alongside the universal safety floor. |
| **Long-context comparison** | ADR-0045 | CORE exact needle-in-a-haystack measurement at N ∈ {100, 1k, 10k, 100k} paired with frozen transformer baselines (Claude 2.1, GPT-4 Turbo 128k, Gemini 1.5 Pro, RULER); `recall_pct=100` for CORE by construction. |

Three sibling pack types compose into every runtime manifold:

```
identity.boundary_ids ∪ safety.boundary_ids ∪ ethics.commitment_ids → manifold.boundary_ids
```

Per-commitment ethics policy lives in two opt-in lists on the
ethics pack: `refusal_commitments` (hard stop) and
`hedge_commitments` (soft prepend), mutually exclusive at load time.
Safety is always in scope for refusal; the floor never moves.

Verification surface:

| Layer | Tests | Live demo |
|---|---|---|
| Identity packs | `tests/test_identity_packs.py`, `tests/test_identity_surface_divergence.py` | `core demo audit-tour` Scene 1 |
| Safety pack + refusal | `tests/test_safety_pack.py`, `tests/test_safety_check.py`, `tests/test_safety_refusal.py` | `core demo audit-tour` Scene 2 |
| Ethics pack + opt-ins | `tests/test_ethics_packs.py`, `tests/test_ethics_check.py`, `tests/test_ethics_refusal_opt_in.py`, `tests/test_hedge_injection.py` | `core demo audit-tour` Scene 3 |
| Turn-loop verdicts + bundle | `tests/test_turn_loop_verdicts.py`, `tests/test_turn_verdicts_bundle.py` | `core chat --show-verdicts` |
| Telemetry sink | `tests/test_telemetry_sink.py`, `tests/test_telemetry_fanout_and_summary.py` | `core demo audit-tour` Scene 4 |
| Audit tour gate | `tests/test_audit_tour.py` — asserts `all_claims_supported` | `core demo audit-tour` |

---

## Pillar 1 → 2 → 3 coupling — ADR-0046 / ADR-0047

ADR-0046 extends the **ADR-0022 → ADR-0026** forward-semantic-control
chain by giving the `AdmissibilityRegion` a new, geometry-derived
source: the `PropositionGraph`.

The graph was previously built **after** `generate()` ran, from the
walk's nearest-node results — a post-hoc descriptor of what the field
had already produced.  ADR-0046 converts each graph's named-node
versors into an `AdmissibilityRegion` **before** `generate()` is
called, via the exact CGA top-k neighbourhood.  The walk is now
constrained by the proposition's geometric meaning rather than
described by it after the fact.

```
geometry (CGA versor neighbourhood)
  → structure (PropositionGraph nodes)
    → propagation (AdmissibilityRegion fed to generate())
```

Three industry-facing demos under `evals/industry_demos/` carry the
falsifiable claims for this coupling.  The exact-recall-at-scale claim
remains under ADR-0045 / `evals/long_context/`, where it is measured
on the real vault path and not duplicated under a weaker construction.

| Layer | Tests | Live demo |
|---|---|---|
| Forward graph constraint (primitive) | `tests/test_graph_constraint.py` — 8 tests | `python -m evals.industry_demos.demo_01_forward_constraint` |
| Forward graph constraint (live wiring) | `tests/test_forward_graph_constraint_wiring.py` — 5 tests | `RuntimeConfig(forward_graph_constraint=True)` then `core eval cognition` |
| Geometry-driven identity | `tests/test_identity_packs.py`, `tests/test_identity_surface_divergence.py` | `python -m evals.industry_demos.demo_02_geometry_drives_identity` |
| Architectural determinism | `tests/test_telemetry_sink.py`, `tests/test_telemetry_fanout_and_summary.py` | `python -m evals.industry_demos.demo_03_deterministic_audit` |

ADR-0047 lands the wire-up behind an opt-in `RuntimeConfig` flag.  The
characterisation it carries (`A/B` on the public cognition split)
shows the wiring is correct and safe but does not move
`surface_groundedness` or `term_capture_rate` on this lane — isolating
the next load-bearing pull to the realizer / surface-assembly path
rather than to propagation.

---

## Session Logs

Session logs record the decisions and rationale from individual working sessions. They are not ADRs — they are the narrative record that informed the ADRs.

| Date | File |
|---|---|
| 2026-05-12 | [SESSION-2026-05-12.md](SESSION-2026-05-12.md) |
| 2026-05-12 (addendum) | [SESSION-2026-05-12-b.md](SESSION-2026-05-12-b.md) |
| 2026-05-12 (language packs) | [SESSION-2026-05-12-language-packs-addendum.md](SESSION-2026-05-12-language-packs-addendum.md) |
| 2026-05-13 | [SESSION-2026-05-13.md](SESSION-2026-05-13.md) |
