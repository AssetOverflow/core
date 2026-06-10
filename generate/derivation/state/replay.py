"""ADR-0184 S2 — replay semantic ledgers into arithmetic proof objects.

Replay is the only bridge from scoped semantic state to arithmetic candidates.
It emits ``GroundedDerivation`` so the existing verifier/classifier/pool remain the
authoritative commit path.
"""

from __future__ import annotations

from generate.derivation.model import GroundedDerivation, Step
from generate.derivation.state.model import SemanticLedger, StateTransition


def replay_accumulation_ledger(ledger: SemanticLedger) -> GroundedDerivation | None:
    """Replay a SET_STATE + GAIN/LOSS ledger to ``GroundedDerivation``.

    Returns ``None`` when the ledger is not the narrow accumulation shape S2 owns.
    This keeps future transition kinds from accidentally being interpreted as a
    linear arithmetic chain before they receive their own proof model.
    """

    transitions = ledger.transitions
    if len(transitions) < 2:
        return None
    start_transition = transitions[0]
    if start_transition.op != "set":
        return None
    key = start_transition.key
    start = start_transition.quantity.to_quantity()
    steps: list[Step] = []

    for transition in transitions[1:]:
        if not _same_key(transition, start_transition):
            return None
        if transition.op not in {"gain", "loss"}:
            return None
        op = "add" if transition.op == "gain" else "subtract"
        operand = transition.quantity.to_quantity(unit_override=key.unit)
        steps.append(Step(op=op, operand=operand, cue=transition.cue))

    if not steps:
        return None
    return GroundedDerivation(start=start, steps=tuple(steps))


def _same_key(a: StateTransition, b: StateTransition) -> bool:
    """True iff two transitions mutate the same scoped state key."""

    return a.key == b.key
