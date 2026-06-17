# CLOSE Derived Climb Yardstick (PR-3, hardened for Claim B)

This lane measures the monotone growth in directly-answerable set enabled by:

- PR #788: relational transitive CLOSE (less/greater/before/after now consolidate like is-a)
- PR #789: derived facts emit review proposals when flag enabled

## Metrics (Claim A + Claim B)
- direct_answerable_before / after_tick_1 / after_fixed_point (vault growth)
- wrong_total (must 0; negatives and excluded preds refused)
- proposals_only_with_flag (measured via *real* ChatRuntime.idle_tick() + IdleTickResult.derived_close_proposals_emitted; >0 only when review_derived_close_proposals=True)
- semantic_positives_determined_direct (explicit determine() calls on positives post-fixed-point assert Determined(True) with rule='direct')
- replay_checksum (aggregates for compatibility)
- content_replay_checksum (canonical closure sets with structure_key + Derivation/premise_structure_keys + proposal bodies for exact-trajectory fidelity)
- proposal_review_posture (additive Claim-B visibility on the review/ratification side of the CLOSE flywheel: emitted proposals carry explicit proposal_only / speculative / requires_review posture; review_eligible count; structural guarantee that the yardstick itself performs no acceptance/rejection/promotion — ratification remains operator/HITL gated. Computed from the same proposal bodies covered by content_replay_checksum.)

## Scenarios
- is-a (member/subset) climb
- less_than relational climb
- before_event temporal climb
- parent/sibling negatives refused (wrong=0)
- proposal emission gated by flag (lived idle_tick path)

## No side effects
- No change to serving, determine, or ratification.
- Uses real idle_tick path with flags for consolidation and proposal emission.
- All realization remains SPECULATIVE; proposals are proposal_only + requires_review.

Run: uv run python -m evals.close_derived_climb
Replays the exact trajectories (aggregates + full content) for audit. Now qualifies as full lived-runtime Claim B yardstick per post-merge hardening audit.

**Dedicated surface:** `make test-close-flywheel` (or the equivalent python -m + pytest commands). This is the clearly named, intentional Claim-B regression surface for heavier determinism regressions and teaching/anti-regression verification flows. See the full definition, capabilities, runtime characteristics, hermeticity guarantees, and Engineering Pillars alignment in `docs/testing-lanes.md` "Dedicated CLOSE Flywheel Regression Surface (Claim-B Level)".

Integrated into the project's standard determinism regression and teaching/anti-regression surfaces via the anti-regression demo embedding (see docs/evals/anti_regression_demo.md and `tests/test_anti_regression_demo.py`). See ratification docs/analysis/close-flywheel-dedicated-regression-surface-ratification-2026-06-16.md (this task), docs/analysis/integrate-hardened-close-yardstick-determinism-teaching-regression-ratification-2026-06-16.md (#792), and docs/analysis/close-derived-climb-yardstick-claim-b-ratification-2026-06-16.md (#791). Cross-references runtime determination surface in docs/runtime_contracts.md.

This PR strengthens the *review/ratification* visibility half (proposal_review_posture + aggregates surfaced through the same dedicated surface and anti-regression demo). See docs/analysis/close-flywheel-proposal-review-visibility-ratification-2026-06-16.md for the full justification, scope lock, pillar alignment (Mechanical Sympathy, Semantic Rigor, Third Door), and invariant preservation.
