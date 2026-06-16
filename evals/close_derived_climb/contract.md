# CLOSE Derived Climb Yardstick (PR-3)

This lane measures the monotone growth in directly-answerable set enabled by:

- PR #788: relational transitive CLOSE (less/greater/before/after now consolidate like is-a)
- PR #789: derived facts emit review proposals when flag enabled

## Metrics
- direct_answerable_before / after_tick_1 / after_fixed_point
- wrong_total (must 0; negatives and excluded preds refused)
- proposals_only_with_flag (emitted >0 only when review_derived_close_proposals=True)
- replay_checksum stable

## Scenarios
- is-a (member/subset) climb
- less_than relational climb
- before_event temporal climb
- parent/sibling negatives refused (wrong=0)
- proposal emission gated by flag

## No side effects
- No change to serving, determine, or ratification.
- Uses real idle_tick path with flags.

Run: python -m evals.close_derived_climb
Replays the exact trajectories for audit.
