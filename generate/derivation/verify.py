"""ADR-0175 Phase 3a — the self-verification gate.

The wrong=0-critical gate. A derivation **self-verifies** only when all hold:

1. **operand grounding** — every operand's value token appears in the problem
   text (no invented numbers);
2. **operation-cue grounding** — every step's licensing cue lexeme appears in the
   text (the operation is licensed by present evidence, not assumed);
3. **unit consistency** — add/subtract require a shared unit; multiply/divide may
   compose across units onto the primary;
4. **no divide-by-zero**.

Grounding reuses the canonical primitives from :mod:`generate.math_roundtrip`
(single source of truth — the same checks the round-trip filter uses), so this
gate cannot drift from the round-trip contract.

``select_self_verified`` adds the cross-derivation **uniqueness** rule: among the
self-verifying derivations, a single distinct answer resolves; zero or several
refuse (the disagreement rule — preserves wrong=0).

Invariant #2: a derivation that fails any clause does not self-verify *even if its
value coincides with the gold answer* (the ``20/5 == 4`` class).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Canonical grounding primitives — reused so this gate stays identical to the
# round-trip filter's notion of "appears in the problem text".
from generate.math_roundtrip import _token_in, _tokens, _value_grounds
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation

_SAME_UNIT_REQUIRED: Final[frozenset[str]] = frozenset({"add", "subtract"})


@dataclass(frozen=True, slots=True)
class SelfVerification:
    verified: bool
    reasons: tuple[str, ...]  # empty iff verified; named failures otherwise


@dataclass(frozen=True, slots=True)
class Resolution:
    answer: float
    answer_unit: str
    derivation: GroundedDerivation


def self_verifies(derivation: GroundedDerivation, problem_text: str) -> SelfVerification:
    """Decide whether ``derivation`` self-verifies against ``problem_text``."""
    tokens = _tokens(problem_text)
    reasons: list[str] = []

    # 1. operand grounding — every value must be sourced from the text.
    operands = [derivation.start, *(s.operand for s in derivation.steps)]
    for q in operands:
        if not _value_grounds(q.source_token, tokens):
            reasons.append(f"operand {q.source_token!r} not grounded in text")

    # 2. operation-cue grounding — every op licensed by a present lexeme.
    for step in derivation.steps:
        if not _token_in(step.cue, tokens):
            reasons.append(f"operation cue {step.cue!r} not grounded in text")

    # 3. unit consistency.
    primary_unit = derivation.start.unit
    for step in derivation.steps:
        if step.op in _SAME_UNIT_REQUIRED and step.operand.unit != primary_unit:
            reasons.append(
                f"unit mismatch: {step.op} of {step.operand.unit!r} into {primary_unit!r}"
            )

    # 4. divide-by-zero.
    for step in derivation.steps:
        if step.op == "divide" and step.operand.value == 0:
            reasons.append("division by zero")

    # 5. completeness — a trustworthy derivation must account for every quantity
    #    the problem states. A derivation that ignores given numbers is an
    #    incomplete reading (typically a correct *first step* of a multi-step
    #    problem, mistaken for the whole answer). Refuse-preferring: unused
    #    quantities -> not self-verified. This is the clause the practice-lane
    #    microscope identified (ADR-0175 self-verification strengthening): it
    #    catches the multi-step-incomplete attempts the cue/grounding clauses
    #    cannot, because their operands ARE grounded.
    problem_quantities = {q.source_token for q in extract_quantities(problem_text)}
    used = {derivation.start.source_token}
    used.update(step.operand.source_token for step in derivation.steps)
    unused = problem_quantities - used
    if unused:
        reasons.append(f"incomplete: unused problem quantities {sorted(unused)}")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def select_self_verified(
    derivations: list[GroundedDerivation],
    problem_text: str,
) -> Resolution | None:
    """Among the self-verifying derivations, return the unique answer or refuse.

    Refuse-preferring: ``None`` when zero self-verify (no grounded derivation) or
    when the self-verifying ones disagree (the multi-branch disagreement rule).
    """
    verified = [d for d in derivations if self_verifies(d, problem_text).verified]
    if not verified:
        return None
    distinct = {round(d.answer, 9) for d in verified}
    if len(distinct) != 1:
        return None  # disagreement -> refuse (wrong=0)
    chosen = verified[0]
    return Resolution(
        answer=chosen.answer,
        answer_unit=chosen.answer_unit,
        derivation=chosen,
    )
