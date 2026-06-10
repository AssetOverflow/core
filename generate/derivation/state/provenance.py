"""ADR-0184 S4b — replay-faithfulness checker (the provenance half of the boundary).

A semantic world may only enter the candidate pool through
:func:`generate.derivation.state.replay.replay_accumulation_ledger`.  This module
states that bridge's law as a *checkable structural property*: given a ledger and a
``GroundedDerivation`` claimed to be its replay, every transition must correspond
1:1 to the arithmetic proof object — no step invented, dropped, reordered, or
re-cued.  A candidate that cannot be tied to its ledger this way is fabricated
semantics and must never be trusted.

This is a checker, not a second replay path: it asserts correspondence, it does not
produce candidates.  Like the rest of ``generate/derivation/state/``, it holds no
commit authority and imports neither the verifier nor the pool (pinned by the
structural scan in ``tests/test_adr_0184_s4_semantic_candidate_source.py``).
"""

from __future__ import annotations

from generate.derivation.model import GroundedDerivation
from generate.derivation.state.model import SemanticLedger

_OP_FOR_TRANSITION: dict[str, str] = {"gain": "add", "loss": "subtract"}


def faithfulness_violations(
    ledger: SemanticLedger, derivation: GroundedDerivation
) -> tuple[str, ...]:
    """Every way ``derivation`` fails to be the faithful replay of ``ledger``.

    Empty iff faithful.  The clauses mirror ``replay_accumulation_ledger`` exactly:

    * the ledger is the narrow accumulation shape (>=2 transitions, SET start,
      one key, GAIN/LOSS tail);
    * ``start`` is the SET quantity verbatim (value, unit, source token);
    * steps correspond 1:1 and in order to the GAIN/LOSS transitions
      (gain->add, loss->subtract; cue and value/source token verbatim);
    * step operands carry the ledger key's unit (the anchor-inheritance law);
    * no step is comparative (a comparative scalar has no ledger transition).
    """
    violations: list[str] = []
    transitions = ledger.transitions

    if len(transitions) < 2:
        violations.append(f"ledger has {len(transitions)} transitions; replay needs >= 2")
        return tuple(violations)
    start_transition = transitions[0]
    if start_transition.op != "set":
        violations.append(f"ledger starts with {start_transition.op!r}, not 'set'")
        return tuple(violations)
    key = start_transition.key

    start_quantity = start_transition.quantity
    if derivation.start.value != start_quantity.value:
        violations.append(
            f"start value {derivation.start.value!r} != SET value {start_quantity.value!r}"
        )
    if derivation.start.unit != start_quantity.unit:
        violations.append(
            f"start unit {derivation.start.unit!r} != SET unit {start_quantity.unit!r}"
        )
    if derivation.start.source_token != start_quantity.source_token:
        violations.append(
            f"start source token {derivation.start.source_token!r} != "
            f"SET source token {start_quantity.source_token!r}"
        )

    changes = transitions[1:]
    if len(derivation.steps) != len(changes):
        violations.append(
            f"{len(derivation.steps)} steps != {len(changes)} change transitions"
        )
        return tuple(violations)

    for idx, (step, transition) in enumerate(zip(derivation.steps, changes)):
        if transition.key != key:
            violations.append(f"transition {idx + 1} mutates a different key")
        expected_op = _OP_FOR_TRANSITION.get(transition.op)
        if expected_op is None:
            violations.append(f"transition {idx + 1} op {transition.op!r} is not gain/loss")
            continue
        if step.op != expected_op:
            violations.append(
                f"step {idx} op {step.op!r} != {expected_op!r} for {transition.op!r}"
            )
        if step.cue != transition.cue:
            violations.append(f"step {idx} cue {step.cue!r} != ledger cue {transition.cue!r}")
        if step.operand.value != transition.quantity.value:
            violations.append(
                f"step {idx} operand {step.operand.value!r} != "
                f"transition value {transition.quantity.value!r}"
            )
        if step.operand.source_token != transition.quantity.source_token:
            violations.append(
                f"step {idx} source token {step.operand.source_token!r} != "
                f"transition source token {transition.quantity.source_token!r}"
            )
        if step.operand.unit != key.unit:
            violations.append(
                f"step {idx} operand unit {step.operand.unit!r} != key unit {key.unit!r} "
                "(anchor-inheritance law)"
            )
        if step.comparative:
            violations.append(f"step {idx} is comparative; no ledger transition licenses it")

    return tuple(violations)


def replay_is_faithful(ledger: SemanticLedger, derivation: GroundedDerivation) -> bool:
    """True iff ``derivation`` is the faithful replay of ``ledger``."""
    return not faithfulness_violations(ledger, derivation)
