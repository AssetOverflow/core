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
from collections import Counter
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


def _base_reasons(derivation: GroundedDerivation, tokens: frozenset[str]) -> list[str]:
    """The grounding ∧ cue ∧ unit ∧ divide-by-zero clauses (everything *but*
    completeness). Shared by :func:`self_verifies` and :func:`classify_derivation`
    so the two cannot drift."""
    reasons: list[str] = []

    # 1. operand grounding — every TEXT operand value must be sourced from the
    #    text. Comparative operands (ADR-0176 MS-2: twice -> x2, 'N times' -> xN)
    #    are grounded by their cue (clause 2), not by a text value token, so they
    #    are exempt here — their pack-supplied scalar is not a number in the text.
    operands = [derivation.start, *(s.operand for s in derivation.steps if not s.comparative)]
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

    return reasons


def _unused_quantities(derivation: GroundedDerivation, problem_text: str) -> Counter[str]:
    """Problem quantities (by source token) the derivation does not consume."""
    problem_quantities = Counter(q.source_token for q in extract_quantities(problem_text))
    used = Counter(
        [derivation.start.source_token]
        + [step.operand.source_token for step in derivation.steps]
    )
    return problem_quantities - used


def self_verifies(derivation: GroundedDerivation, problem_text: str) -> SelfVerification:
    """Decide whether ``derivation`` self-verifies against ``problem_text``."""
    tokens = _tokens(problem_text)
    reasons = _base_reasons(derivation, tokens)

    # 5. completeness — a trustworthy derivation must account for every quantity
    #    the problem states. A derivation that ignores given numbers is an
    #    incomplete reading (typically a correct *first step* of a multi-step
    #    problem, mistaken for the whole answer). Refuse-preferring: unused
    #    quantities -> not self-verified. This is the clause the practice-lane
    #    microscope identified (ADR-0175 self-verification strengthening): it
    #    catches the multi-step-incomplete attempts the cue/grounding clauses
    #    cannot, because their operands ARE grounded.
    unused = _unused_quantities(derivation, problem_text)
    if unused:
        reasons.append(f"incomplete: unused problem quantities {sorted(unused.keys())}")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def _is_repeated_unit_product(derivation: GroundedDerivation) -> bool:
    """ADR-0184 — a *pure* multiplicative product that revisits a non-empty
    dimension (``apples × apples``, ``cards × cards``), forming ``unit²``.

    A genuine rate-chain composes **distinct** dimensions (``boxes × erasers/box ×
    $/eraser``); a product that repeats a dimension is multiplying independent groups
    (``4 bags×20 + 6 bags×25`` mis-read as ``4×20×6×25``) — never a real quantity.
    Empty units are exempt (an unknown dimension cannot be shown to collide, and a
    correct rate-chain may carry a blank-unit scalar like ``$0.75``). Divide is
    exempt — same-unit division (``feet / feet``) is a legitimate dimensionless count.
    Dimensional, not lexical (ADR-0165-safe)."""
    if not derivation.steps or not all(step.op == "multiply" for step in derivation.steps):
        return False
    units = [derivation.start.unit, *(step.operand.unit for step in derivation.steps)]
    non_empty = [unit for unit in units if unit]
    return len(non_empty) != len(set(non_empty))


def classify_derivation(derivation: GroundedDerivation, problem_text: str) -> str | None:
    """ADR-0182 — the commit-eligibility class of a derivation, for pooling.

    Returns:

    * ``"complete"`` — passes every clause *including* full completeness;
      **commit-eligible** (may resolve as an answer).
    * ``"exempt"``  — **commit-INELIGIBLE**: it may enter the pool and force a
      disagreement → refusal, but never resolve as the answer alone. Two ways to
      earn it: (ADR-0182) the only unused quantities are **isolated-foreign**
      (a candidate distractor standing alone in a dimension the reading never
      touches); or (ADR-0184) the derivation is a **repeated-unit product**
      (``unit²`` — dimensionally impossible as the answer, but still a real reading
      that should *disagree* with an additive rival, e.g. ``coins × coins`` vs
      ``coins + coins`` on a disguised-polarity confuser). Keeping it commit-
      ineligible — rather than dropping it — preserves the disagreement refusals
      ADR-0182 relies on; dropping it would unmask the additive reading as a unique
      (wrong) commit.
    * ``None``      — fails a base clause, or an unused quantity is not
      isolated-foreign (empty unit, or a unit shared with a used operand → real
      signal the reading dropped).
    """
    tokens = _tokens(problem_text)
    if _base_reasons(derivation, tokens):
        return None
    repeated_unit_product = _is_repeated_unit_product(derivation)
    unused = _unused_quantities(derivation, problem_text)
    if not unused:
        # ADR-0184: a dimensionally-impossible product is commit-ineligible (exempt),
        # not commit-eligible — but it stays in the pool to force disagreement.
        return "exempt" if repeated_unit_product else "complete"

    used_units = {derivation.start.unit, *(step.operand.unit for step in derivation.steps)}
    units_by_token: dict[str, set[str]] = {}
    for q in extract_quantities(problem_text):
        units_by_token.setdefault(q.source_token, set()).add(q.unit)

    for token in unused:
        token_units = units_by_token.get(token, {""})
        # isolated-foreign iff *every* occurrence has a non-empty unit not shared
        # with any used operand. An empty unit, or a unit a used operand carries,
        # disqualifies the exemption — that quantity is real signal, not a distractor.
        if any((not unit) or (unit in used_units) for unit in token_units):
            return None
    return "exempt"


def select_self_verified(
    derivations: list[GroundedDerivation],
    problem_text: str,
    *,
    target_units: tuple[str, ...] = (),
) -> Resolution | None:
    """Among the self-verifying derivations, return the unique answer or refuse.

    Refuse-preferring: ``None`` when zero self-verify (no grounded derivation) or
    when the self-verifying ones disagree (the multi-branch disagreement rule).

    ADR-0176 MS-2 question-targeting: when ``target_units`` is non-empty (the unit
    the question asks for), derivations whose ``answer_unit`` is not among them are
    dropped — a chain that computes the wrong kind of quantity answered a different
    question. Empty ``target_units`` imposes no constraint (the unit signal may be
    unavailable, e.g. a superordinate the units pack doesn't yet cover).
    """
    verified = [d for d in derivations if self_verifies(d, problem_text).verified]
    if target_units:
        verified = [d for d in verified if d.answer_unit in target_units]
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
