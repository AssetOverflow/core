"""ADR-0177 CP-1/CP-2a — cue-precision reliability ledger + training.

Standalone, deterministic, replay-stable. **Inert w.r.t. the runtime path**: NOT
wired into the gate, any scorer, or the search (trust/guidance is CP-2b/CP-3). The
CP-2a trainer is consumed only by the sealed eval measurement, never by serving.

Public surface:
- :class:`CuePattern` — the ``(cue, op, unit_shape)`` reading key.
- :data:`UNIT_SHAPES`, :data:`CROSS_UNIT`, :data:`SAME_UNIT` — the unit-shape set.
- :func:`pattern_for_step`, :func:`patterns_in_chain` — extract patterns from a
  grounded derivation.
- :class:`PatternTally` — per-pattern counted ledger; reliability = commitment
  precision via the pinned ADR-0175 conservative floor.
- :class:`CuePrecisionLedger` — immutable pattern->tally map + credit assignment
  (``record_chain`` / ``record_case``).
- :func:`train_from_cases`, :func:`candidates_for` (CP-2a) — fold gold-labelled
  candidate readings (from injected enumerators) into a trained ledger.
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
from generate.cue_precision.trainer import (
    CandidateEnumerator,
    TrainingCase,
    candidates_for,
    train_from_cases,
)

__all__ = [
    "CROSS_UNIT",
    "CandidateEnumerator",
    "CuePattern",
    "CuePrecisionLedger",
    "PatternTally",
    "SAME_UNIT",
    "TrainingCase",
    "UNIT_SHAPES",
    "candidates_for",
    "pattern_for_step",
    "patterns_in_chain",
    "train_from_cases",
]
