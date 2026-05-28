"""ADR-0175 §4a — pinned conservative reliability floor (one-sided Wilson lower bound).

A deterministic, replay-stable lower bound on a success proportion given integer
counts. No learned weights, no stochastic sampling — the only "statistics" here is
a fixed closed-form bound over counts.

Two independent dials (do not conflate):

- ``WILSON_Z`` — how skeptical the *estimator* is. Pinned, global. The single
  caution knob. The engine never touches it.
- per-class ``θ`` ceilings (see :mod:`core.reliability_gate.ceilings`) — how much
  reliability an *action* demands. Human-set, per class. Also untouchable by the
  engine (invariant #4).
"""

from __future__ import annotations

import math
from typing import Final

# Single global pessimism constant (~99% one-sided). ADR-0175 §4a.
WILSON_Z: Final[float] = 2.576
# Minimum committed trials before any reliability is claimed.
N_MIN: Final[int] = 10
# Replay rounding: half-to-even to this many decimals (determinism contract).
_ROUND_DECIMALS: Final[int] = 9
# Largest value strictly below 1.0 at the pinned precision — honours the [0,1)
# range invariant unconditionally (the Wilson lower bound is < 1 for all finite
# committed; this only ever binds at absurd counts, e.g. committed > ~6.6e9).
_MAX_BELOW_ONE: Final[float] = 1.0 - 10.0 ** (-_ROUND_DECIMALS)


def conservative_floor(successes: int, committed: int) -> float:
    """Lower bound on the success proportion of ``successes`` out of ``committed``.

    Pinned one-sided Wilson lower bound (ADR-0175 §4a). Returns a value in
    ``[0.0, 1.0)`` — never exactly ``1.0`` (no finite record proves perfection).
    Below :data:`N_MIN` committed trials returns ``0.0`` (insufficient evidence).

    Deterministic and replay-stable: IEEE-754 float64 with the result rounded
    half-to-even to ``1e-9`` so the downstream gate comparison is byte-stable
    across backends.

    For a perfect record (``successes == committed``) the bound reduces to
    ``committed / (committed + z²)`` — reliability is *earned by volume*, never
    granted by a lucky streak.
    """
    if not isinstance(successes, int) or not isinstance(committed, int):
        raise TypeError("successes and committed must be int counts")
    if committed < 0 or successes < 0:
        raise ValueError("counts must be non-negative")
    if successes > committed:
        raise ValueError(
            f"successes ({successes}) cannot exceed committed ({committed})"
        )
    if committed < N_MIN:
        return 0.0

    p = successes / committed
    z2 = WILSON_Z * WILSON_Z
    denom = 1.0 + z2 / committed
    center = (p + z2 / (2.0 * committed)) / denom
    margin = (WILSON_Z / denom) * math.sqrt(
        p * (1.0 - p) / committed + z2 / (4.0 * committed * committed)
    )
    lower = center - margin
    if lower < 0.0:
        lower = 0.0
    rounded = round(lower, _ROUND_DECIMALS)
    # Honour [0.0, 1.0) as a hard invariant regardless of rounding.
    return rounded if rounded < 1.0 else _MAX_BELOW_ONE
