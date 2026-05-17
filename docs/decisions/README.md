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

## Session Logs

Session logs record the decisions and rationale from individual working sessions. They are not ADRs — they are the narrative record that informed the ADRs.

| Date | File |
|---|---|
| 2026-05-12 | [SESSION-2026-05-12.md](SESSION-2026-05-12.md) |
| 2026-05-12 (addendum) | [SESSION-2026-05-12-b.md](SESSION-2026-05-12-b.md) |
| 2026-05-12 (language packs) | [SESSION-2026-05-12-language-packs-addendum.md](SESSION-2026-05-12-language-packs-addendum.md) |
| 2026-05-13 | [SESSION-2026-05-13.md](SESSION-2026-05-13.md) |
