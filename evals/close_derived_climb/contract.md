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

Run: python -m evals.close_derived_climb
Replays the exact trajectories (aggregates + full content) for audit. Now qualifies as full lived-runtime Claim B yardstick per post-merge hardening audit.
