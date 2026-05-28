"""ADR-0175 §4 — the per-class calibration ledger.

A replayable tally of *counted* outcomes per class (= capability axis: G1..G5,
S1, ...). Nothing learned, nothing stochastic — every figure is an integer count.

Reliability is **commitment precision** (``correct / (correct + wrong)`` via the
pinned :func:`conservative_floor`): refusals are excluded from the denominator on
purpose. Refusing is always safe, so a high refusal rate is a *coverage* fact
(``coverage``), never a *reliability* penalty.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.reliability_gate.floor import conservative_floor


@dataclass(frozen=True, slots=True)
class ClassTally:
    """Immutable per-class outcome counts.

    ``class_name`` is a capability-axis id. All mutation is via :meth:`record`,
    which returns a new tally (immutability rule).
    """

    class_name: str
    correct: int = 0
    wrong: int = 0
    refused: int = 0
    t2_verified: int = 0
    t2_agrees_gold: int = 0

    def __post_init__(self) -> None:
        for value in (
            self.correct,
            self.wrong,
            self.refused,
            self.t2_verified,
            self.t2_agrees_gold,
        ):
            if not isinstance(value, int) or value < 0:
                raise ValueError("tally counts must be non-negative ints")
        if self.t2_agrees_gold > self.t2_verified:
            raise ValueError(
                f"t2_agrees_gold ({self.t2_agrees_gold}) cannot exceed "
                f"t2_verified ({self.t2_verified})"
            )

    @property
    def committed(self) -> int:
        """Attempts where the engine committed to an answer (excludes refusals)."""
        return self.correct + self.wrong

    @property
    def attempted(self) -> int:
        return self.correct + self.wrong + self.refused

    @property
    def reliability(self) -> float:
        """Conservative lower bound on commitment precision (ADR-0175 §4/§4a)."""
        return conservative_floor(self.correct, self.committed)

    @property
    def t2_precision(self) -> float:
        """How trustworthy Tier-2 self-verification is on this class (vs gold)."""
        return conservative_floor(self.t2_agrees_gold, self.t2_verified)

    @property
    def coverage(self) -> float:
        """Commit rate = committed / attempted. A coverage fact, not reliability."""
        return round(self.committed / self.attempted, 9) if self.attempted else 0.0

    def record(
        self,
        *,
        correct: int = 0,
        wrong: int = 0,
        refused: int = 0,
        t2_verified: int = 0,
        t2_agrees_gold: int = 0,
    ) -> "ClassTally":
        """Return a new tally with the given outcomes added (immutable update)."""
        return ClassTally(
            class_name=self.class_name,
            correct=self.correct + correct,
            wrong=self.wrong + wrong,
            refused=self.refused + refused,
            t2_verified=self.t2_verified + t2_verified,
            t2_agrees_gold=self.t2_agrees_gold + t2_agrees_gold,
        )
