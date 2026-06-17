"""Yardstick lane for the CLOSE derived climb (PR-3).

Proves — deterministically — the monotone capability climb now enabled by
PR #788 (relational transitive CLOSE substrate) + PR #789 (derived CLOSE
proposal bridge):

- Direct answerable set grows across idle ticks to fixed point (is-a + relational).
- wrong_total == 0 (negatives and excluded predicates remain refused; member∨member canary never derived).
- Proposal candidates emitted only when review_derived_close_proposals flag is enabled.
- Review/ratification posture of emitted proposals is explicitly visible (all proposal_only + SPECULATIVE + requires_review; none accepted/promoted inside the yardstick).
- Replay stable (sizes, closures, proposal counts deterministic).

Composes the lived loop: realize → determine → CLOSE consolidate → proposal emission (flag-gated).

No serving changes. No ratification.
"""

from evals.close_derived_climb.runner import run

__all__ = ["run"]