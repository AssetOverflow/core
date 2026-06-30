# ADR-0225 — ADR Corpus Hygiene, Numbering Policy, and Cross-Reference Governance

**Status:** Accepted (2026-06-30)

**Context:** ADR-0201 is already occupied by `ADR-0201-proposition-canonicalizer.md`; therefore this governance decision uses the next available top-level ADR number after ADR-0224.

## Decision

CORE will treat the ADR corpus as a governed graph, not a loose directory of historical notes.

Every future ADR that touches runtime state, packs, teaching, memory, replay, or invariants must explicitly cite these standing anchors:

1. **Safety boundaries:** ADR-0027, ADR-0028, ADR-0029, and the safety-pack / identity-pack trust boundary.
2. **Versor closure:** `versor_condition(F) < 1e-6`, equivalently `||F * reverse(F) - 1||_F < 1e-6` for runtime field states.
3. **Reconstruction-over-storage:** store enough structured state to reconstruct the needed evidence; do not duplicate opaque state as a substitute for provenance.
4. **Replay-equivalence gates:** reviewed mutation and serving changes must name the deterministic replay or byte-equivalence gate that proves no hidden drift.

## Numbering Discipline

- Prefer sequential top-level numbering.
- Use sub-numbering only for clearly phased work inside one decision family, for example `ADR-0073a`–`ADR-0073d` or `ADR-0119.1`–`ADR-0119.8`.
- Gaps are permitted only when accompanied by explicit superseding, reservation, or reconciliation notes.
- Duplicate top-level numbers are forbidden except where already historical; future remediation must add reconciliation notes rather than silently renaming historical files.
- Governance ADRs must not occupy an already-used number. This ADR uses `ADR-0225` because `ADR-0201` is already live.

## Mandatory Cross-Reference Rule

Every new or amended ADR in the scoped areas must include a short `Governance citations` or equivalent section naming:

- safety / identity boundary impact;
- versor closure impact;
- reconstruction-over-storage impact;
- replay-equivalence / deterministic validation impact;
- mutation standing: no mutation, SPECULATIVE/proposal-only, reviewed durable mutation, or proof-carrying promotion.

If an item is not applicable, the ADR must say why. Absence is not acceptable.

## Index Maintenance

`docs/decisions/README.md` is the living reference matrix for ADR navigation. Every new ADR must update it in the same change set with:

- ADR number, title, and status;
- cluster / chain membership when applicable;
- supersedes / superseded-by note when applicable;
- governance anchors when the ADR falls under this policy.

## Consequences and Affected Corpus

This policy affects all future ADRs and all amendments to existing ADRs.

This remediation batch specifically updates or audits:

- ADRs: `ADR-0001`, `ADR-0027`, `ADR-0028`, `ADR-0029`, `ADR-0055`, `ADR-0056`, `ADR-0057`, `ADR-0200` through `ADR-0224`, and this `ADR-0225`.
- Index / map artifacts: `docs/decisions/README.md`, `docs/analysis/adr-corpus-cohesion-dependency-map-2026-06-30.md`.
- Safety / identity code surfaces: `packs/safety/loader.py`, `packs/safety/check.py`, `core/proposal_review/safety.py`, `chat/pack_resolver.py`.
- Foundational / versor code surfaces: `vocab/manifold.py`, `core_ingest/manifold.py`.
- Teaching / memory / epistemic code surfaces: `teaching/review.py`, `teaching/replay.py`, `teaching/proposals.py`, `teaching/promotion.py`, `teaching/supersede.py`, `teaching/contemplation.py`, `teaching/epistemic.py`, `teaching/discovery.py`.
- Additional learning / review surfaces: `core/proposal_review/`, `core/learning_arena/`.
- Test surfaces identified during mapping: `tests/test_safety_pack.py`, `tests/test_ethics_refusal_opt_in.py`, `tests/test_epistemic_phase3_state_tagging.py`, `tests/test_identity_continuity_proof.py`, `tests/test_vocab_manifold_invariants.py`, `tests/test_engine_loop_proof.py`, `tests/test_determinism_proofs.py`, `tests/test_learning_loop_demo.py`, `tests/test_teaching_loop_bench.py`, `tests/test_phase_d_replay_evidence.py`, `tests/test_discovery_candidates.py`, `tests/test_mutation_proposal_type.py`, `tests/test_proof_carrying_promotion_demo.py`, and `core-rs/tests/test_versor.rs`.

## Validation

- The Phase 1 dependency map is `docs/analysis/adr-corpus-cohesion-dependency-map-2026-06-30.md`.
- Baseline on current `main` is not green: `make test-fast` reports `54 failed, 10884 passed, 23 skipped, 912 deselected`.
- This ADR is documentation-governance only. It adds no field operator, no recall path, no pack mutation, and no runtime serving path.

## Governance Citations

- Safety boundaries: ADR-0027, ADR-0028, ADR-0029; no safety behavior is changed here.
- Versor closure: `versor_condition(F) < 1e-6`; no field state construction or propagation is changed here.
- Reconstruction-over-storage: this ADR requires index maintenance and traceable map artifacts instead of inferred claims.
- Replay-equivalence: future scoped ADRs must name their deterministic validation gate; this ADR records the current red baseline rather than claiming green.
- Mutation standing: documentation-only; no pack, teaching corpus, vault, or runtime mutation path is added.
