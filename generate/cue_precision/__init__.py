"""ADR-0177 CP-1 — cue-precision reliability ledger substrate.

Standalone, deterministic, replay-stable. **Inert**: NOT wired into the gate, any
scorer, or the search (that is CP-2/CP-3). Imported by nothing outside its own
tests — like ``core/reliability_gate/`` before its consumer existed.

Public surface:
- :class:`CuePattern` — the ``(cue, op, unit_shape)`` reading key.
- :data:`UNIT_SHAPES`, :data:`CROSS_UNIT`, :data:`SAME_UNIT` — the unit-shape set.
- :func:`pattern_for_step`, :func:`patterns_in_chain` — extract patterns from a
  grounded derivation.
- :class:`PatternTally` — per-pattern counted ledger; reliability = commitment
  precision via the pinned ADR-0175 conservative floor.
- :class:`CuePrecisionLedger` — immutable pattern->tally map + credit assignment
  (``record_chain`` / ``record_case``).
"""

from __future__ import annotations

from generate.cue_precision.ledger import (
    CROSS_UNIT,
    SAME_UNIT,
    UNIT_SHAPES,
    CuePattern,
    CuePrecisionLedger,
    PatternTally,
    pattern_for_step,
    patterns_in_chain,
)

__all__ = [
    "CROSS_UNIT",
    "CuePattern",
    "CuePrecisionLedger",
    "PatternTally",
    "SAME_UNIT",
    "UNIT_SHAPES",
    "pattern_for_step",
    "patterns_in_chain",
]
