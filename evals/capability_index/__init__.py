"""Cross-domain capability index — the AGI-roadmap MEASURE step (Phase 1).

The yardstick that gates every later "more capable" claim. It composes the
independent-gold reasoning lanes into one report with honest, un-gameable axes:

- **accuracy** — of *committed* answers; wrong stays 0 in assert mode.
- **coverage** — attempted (not refused) fraction.
- **coverage_geomean** — the headline: the geometric mean of per-domain coverage,
  which only rises if EVERY domain rises. A narrow per-domain hack leaves it ~0.
- **capability_score** — `coverage_geomean × accuracy`, hard-gated to 0 if any
  domain committed a wrong answer (assert-mode invariant).

This makes "general, not narrow" a number, and makes self-deception (gaming one
lane) structurally visible. See
``docs/analysis/AGI-candidacy-autonomous-improvement-roadmap-2026-06-05.md``.
"""

from __future__ import annotations
