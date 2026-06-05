"""L10 continuity spike — a falsifiable long-horizon soak of the real turn loop.

This lane is the empirical gate between the two L10 targets (see
``docs/analysis/L10-continuity-spike-design-2026-06-05.md``):

- **T-resume** (provable same-life *resume*): determinism + recovery (P1, P2, P3, P4).
- **T-experience** (a continuous *experiencing* field-life): the field's *content*
  stays meaningful over indefinite uptime (P5).

It is NOT a proof of correctness of any single turn (that is the cognition lane),
nor a wall-clock endurance certificate. It is a falsifiable soak: every predicate
must be able to fail loudly, and each predicate is mutation-verified to *bite*
before any PASS is trusted (CLAUDE.md schema-as-proof discipline).

The lane drives the full runtime, but it never *directly* imports the GSM8K
serving path (``generate.derivation`` / ``core.reliability_gate``) and it is
read-only over the runtime — it records evidence and never mutates serving code
or any gold lane — so it cannot regress the serving metric.
"""

from __future__ import annotations
