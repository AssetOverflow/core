"""ADR-0177 CP-1 — the per-cue-pattern reliability ledger + credit assignment.

A replayable tally of *counted* gold-labels per **cue-pattern**, mirroring the
ADR-0175 per-class ledger (:mod:`core.reliability_gate.ledger`) but keyed on a
``(cue, op, unit_shape)`` pattern string instead of a capability axis. Nothing
learned, nothing stochastic — every figure is an integer count, and reliability
is the same pinned :func:`conservative_floor` (commitment precision, earned by
volume, never by a lucky streak).

This is **inert substrate** (ADR-0177 §"Recommended sequencing" CP-1): the
mechanism + credit assignment only. It is **not** wired into the gate, any
scorer, or the search (that is CP-2/CP-3). It is imported by nothing outside its
own tests, exactly as ``core/reliability_gate/`` shipped before its consumer.

Credit assignment (ADR-0177 §"Credit assignment"): for a practice case the search
emits candidate chains; each chain is labelled by gold (``answer == gold``); for
**every step's pattern** in a chain we record ``+correct`` if the chain matched
gold else ``+wrong``. Learning does **not** depend on the search *resolving* — it
labels candidates, separate from the resolve/refuse decision (ADR-0177 §"The
mechanism"). A case-level *refusal* is therefore never counted as a commitment:
the ledger only ever sees gold-labelled candidate chains, and a pattern tally has
no "refused" axis at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Iterable

from core.reliability_gate.floor import conservative_floor
from generate.derivation.model import VALID_OPS, GroundedDerivation, Step

# A step either stays within the running unit dimension or crosses into another.
CROSS_UNIT: Final[str] = "cross_unit"
SAME_UNIT: Final[str] = "same_unit"
UNIT_SHAPES: Final[frozenset[str]] = frozenset({CROSS_UNIT, SAME_UNIT})

# Replay rounding for gold comparison — identical to the verify gate's notion of
# "same answer" (generate/derivation/verify.py uses round(answer, 9)).
_GOLD_DECIMALS: Final[int] = 9


@dataclass(frozen=True, slots=True)
class CuePattern:
    """A ``(cue, op, unit_shape)`` reading the search asserts the text licenses.

    ``cue`` is the surface lexeme licensing ``op`` (e.g. ``"per"``); ``op`` is a
    :data:`generate.derivation.model.VALID_OPS` member; ``unit_shape`` records
    whether the operation crosses units (ADR-0177 §"Pattern key" — cross-unit
    multiplication is the aggregate signal).
    """

    cue: str
    op: str
    unit_shape: str

    def __post_init__(self) -> None:
        if not isinstance(self.cue, str) or not self.cue:
            raise ValueError("cue must be a non-empty str")
        if self.op not in VALID_OPS:
            raise ValueError(f"op must be one of {sorted(VALID_OPS)}, got {self.op!r}")
        if self.unit_shape not in UNIT_SHAPES:
            raise ValueError(
                f"unit_shape must be one of {sorted(UNIT_SHAPES)}, got {self.unit_shape!r}"
            )


def _unit_shape(running_unit: str, operand_unit: str) -> str:
    """Classify a step's unit shape against the running (primary) unit.

    The value model keeps the primary (``start``) unit through the whole fold
    (``GroundedDerivation.answer_unit == start.unit``), so the running unit is the
    start unit at every step. A dimensionless operand (a comparative scalar carries
    ``unit == ""``) *scales within* the current dimension — ``twice as many apples``
    stays apples — so it reads :data:`SAME_UNIT`, not a cross-unit aggregate. The
    gate already forces add/subtract operands to share the primary unit, so only
    multiply/divide can ever be :data:`CROSS_UNIT`.
    """
    if operand_unit == "" or operand_unit == running_unit:
        return SAME_UNIT
    return CROSS_UNIT


def pattern_for_step(derivation: GroundedDerivation, step: Step) -> CuePattern:
    """The :class:`CuePattern` a single step contributes within ``derivation``."""
    return CuePattern(
        cue=step.cue,
        op=step.op,
        unit_shape=_unit_shape(derivation.start.unit, step.operand.unit),
    )


def patterns_in_chain(derivation: GroundedDerivation) -> tuple[CuePattern, ...]:
    """Every step's pattern, in step order. Each *occurrence* counts (ADR-0177
    credit assignment is per-step, so a 3-step product-of-all credits its pattern
    three times — reliability is earned by clean appearances)."""
    return tuple(pattern_for_step(derivation, step) for step in derivation.steps)


@dataclass(frozen=True, slots=True)
class PatternTally:
    """Immutable per-pattern outcome counts.

    Mirrors :class:`core.reliability_gate.ledger.ClassTally`: counts-only,
    reliability is commitment precision via the pinned conservative floor. There
    is **no** refused axis — a candidate chain is always a gold-labelled
    commitment; case-level refusals are never recorded here (ADR-0177).
    """

    pattern: CuePattern
    correct: int = 0
    wrong: int = 0

    def __post_init__(self) -> None:
        for value in (self.correct, self.wrong):
            if not isinstance(value, int) or value < 0:
                raise ValueError("tally counts must be non-negative ints")

    @property
    def committed(self) -> int:
        """Gold-labelled candidate-chain appearances of this pattern."""
        return self.correct + self.wrong

    @property
    def reliability(self) -> float:
        """Conservative lower bound on commitment precision (ADR-0175 §4a floor).

        ``0.0`` for a cold/low pattern (below ``N_MIN`` committed): a cold ledger
        trusts nothing, which is the wrong=0 safety property CP-2 will rely on.
        """
        return conservative_floor(self.correct, self.committed)

    def record(self, *, correct: int = 0, wrong: int = 0) -> "PatternTally":
        """Return a new tally with the given outcomes added (immutable update)."""
        return PatternTally(
            pattern=self.pattern,
            correct=self.correct + correct,
            wrong=self.wrong + wrong,
        )


def _sort_key(pattern: CuePattern) -> tuple[str, str, str]:
    return (pattern.cue, pattern.op, pattern.unit_shape)


@dataclass(frozen=True, slots=True)
class CuePrecisionLedger:
    """Immutable map of :class:`CuePattern` -> :class:`PatternTally`.

    Canonical storage is a tuple sorted by pattern (deterministic, byte-stable
    across runs). Every ``record_*`` returns a new ledger (immutability rule);
    an absent pattern reads as an empty tally, so a cold ledger reports ``0.0``
    reliability for every pattern.
    """

    tallies: tuple[PatternTally, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        seen: set[CuePattern] = set()
        for tally in self.tallies:
            if tally.pattern in seen:
                raise ValueError(f"duplicate pattern in ledger: {tally.pattern!r}")
            seen.add(tally.pattern)

    def tally_for(self, pattern: CuePattern) -> PatternTally:
        """The tally for ``pattern``, or an empty one if unseen (cold ⇒ 0)."""
        for tally in self.tallies:
            if tally.pattern == pattern:
                return tally
        return PatternTally(pattern=pattern)

    def reliability(self, pattern: CuePattern) -> float:
        """Conservative reliability of ``pattern`` (``0.0`` when cold/low)."""
        return self.tally_for(pattern).reliability

    def _record_pattern(
        self, pattern: CuePattern, *, correct: int = 0, wrong: int = 0
    ) -> "CuePrecisionLedger":
        index = {tally.pattern: tally for tally in self.tallies}
        base = index.get(pattern, PatternTally(pattern=pattern))
        index[pattern] = base.record(correct=correct, wrong=wrong)
        ordered = tuple(sorted(index.values(), key=lambda t: _sort_key(t.pattern)))
        return CuePrecisionLedger(tallies=ordered)

    def record_chain(
        self, derivation: GroundedDerivation, *, matched_gold: bool
    ) -> "CuePrecisionLedger":
        """Credit every step's pattern in ``derivation`` by its gold label.

        ``+correct`` per step occurrence when the chain matched gold, else
        ``+wrong``. A chain whose value cannot be computed (a divide-by-zero the
        gate would reject) is not a labelable reading and contributes nothing —
        a deliberate, documented skip, not a swallowed error.
        """
        ledger = self
        for pattern in patterns_in_chain(derivation):
            if matched_gold:
                ledger = ledger._record_pattern(pattern, correct=1)
            else:
                ledger = ledger._record_pattern(pattern, wrong=1)
        return ledger

    def record_case(
        self,
        candidate_chains: Iterable[GroundedDerivation],
        gold_answer: float,
    ) -> "CuePrecisionLedger":
        """Label each candidate chain by gold and credit its patterns.

        Independent of whether the search *resolved* the case (ADR-0177): the
        ledger learns from labelling candidates, so a refused case still records
        only its candidates' gold labels — never a separate refusal penalty.
        """
        ledger = self
        for derivation in candidate_chains:
            try:
                value = derivation.answer
            except ZeroDivisionError:
                # Non-computable chain: not a labelable reading (the verify gate
                # rejects divide-by-zero before .answer is relied upon). Skip it.
                continue
            matched = round(value, _GOLD_DECIMALS) == round(gold_answer, _GOLD_DECIMALS)
            ledger = ledger.record_chain(derivation, matched_gold=matched)
        return ledger
