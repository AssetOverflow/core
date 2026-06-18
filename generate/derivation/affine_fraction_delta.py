"""Gate A2n — affine fraction-delta (fraction-of-reference plus offset).

Experience Flywheel Sprint 9 / microscope ``affine_equation_fraction_delta``
(train_sample **0010**): a prior clause establishes a reference entity's current
amount (including initial-loss mutation); a follow-on clause states
``N/M more than what <entity> currently has, plus K``; the question asks the
subject's total count.

GSM8K gold for this family computes:

    answer = reference × (N/M) + K

not ``reference × (1 + N/M)``.  Narrow organ — not ``decrease to N/M of``
(fraction_decrease), not comparative ``twice as many``, not a generic affine
equation parser.  Promotion requires:

- exactly one ``N/M more than what <entity> currently has`` clause;
- explicit ``plus K`` offset in the same clause;
- resolvable reference quantity from a single prior initial-mutation clause;
- question binds ``how many`` + possession cue for the affine subject;
- hazard refusal (decrease-to fraction, percent, goal language, multiple fractions).

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from typing import Final

from collections import Counter

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, SelfVerification
from generate.math_candidate_parser import _init_mutation_admitted
from generate.math_roundtrip import _token_in, _tokens, _value_grounds

_AFFINE_FRACTION_RE: Final[re.Pattern[str]] = re.compile(
    r"(\d+)\s*/\s*(\d+)\s+more\s+than\s+what\s+(\w+)\s+currently\s+has,\s+plus\s+(\d+)",
    re.IGNORECASE,
)
_DECREASE_TO_FRACTION_RE: Final[re.Pattern[str]] = re.compile(
    r"decrease\s+to\s+\d+\s*/\s*\d+\s+of",
    re.IGNORECASE,
)
_EXTRA_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+\s*/\s*\d+")
_GOAL_INTENT: Final[frozenset[str]] = frozenset(
    {"want", "wants", "wanted", "need", "needs", "hoping", "hopes", "plans", "aims", "goal"}
)
_POSSESSION_CUES: Final[frozenset[str]] = frozenset({"has", "have", "had"})


def _asks_subject_total(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "how" in tokens and "many" in tokens and bool(_POSSESSION_CUES & tokens)


def _affine_match(problem_text: str) -> re.Match[str] | None:
    matches = list(_AFFINE_FRACTION_RE.finditer(problem_text))
    if len(matches) != 1:
        return None
    return matches[0]


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _DECREASE_TO_FRACTION_RE.search(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "%" in problem_text or "percent" in text_tokens or "percentage" in text_tokens:
        return True
    if text_tokens & _GOAL_INTENT:
        return True
    if "twice" in text_tokens or "thrice" in text_tokens or "double" in text_tokens:
        return True
    match = _affine_match(problem_text)
    if match is None:
        return True
    fractions = _EXTRA_FRACTION_RE.findall(problem_text)
    token = f"{match.group(1)}/{match.group(2)}"
    extra = [f for f in fractions if f.replace(" ", "") != token.replace(" ", "")]
    return len(extra) > 0


def _reference_candidate(problem_text: str, entity: str):
    question_clause = _question_clause(problem_text)
    match = _affine_match(problem_text)
    if match is None:
        return None
    affine_clause = match.group(0)
    for clause in segment_clauses(problem_text):
        if clause == question_clause or affine_clause in clause:
            continue
        for candidate in _init_mutation_admitted(clause):
            if candidate.initial.entity.lower() != entity.lower():
                continue
            return candidate
    return None


def _reference_quantity(problem_text: str, entity: str) -> Quantity | None:
    candidate = _reference_candidate(problem_text, entity)
    if candidate is None:
        return None
    qty = candidate.initial.quantity
    return Quantity(
        value=qty.value,
        unit=qty.unit,
        source_token=candidate.matched_value_token,
    )


def build_affine_fraction_delta(problem_text: str) -> GroundedDerivation | None:
    """Construct ``reference × (N/M) + K``, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_subject_total(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    match = _affine_match(problem_text)
    if match is None:
        return None

    num_s, den_s, entity, offset_s = (
        match.group(1),
        match.group(2),
        match.group(3),
        match.group(4),
    )
    try:
        num = int(num_s)
        den = int(den_s)
        offset = float(offset_s)
    except ValueError:
        return None
    if num <= 0 or den <= 0:
        return None

    reference = _reference_quantity(problem_text, entity)
    if reference is None:
        return None

    factor = num / den
    fraction_token = f"{num_s}/{den_s}"

    return GroundedDerivation(
        start=reference,
        steps=(
            Step(
                op="multiply",
                operand=Quantity(value=factor, unit="", source_token=fraction_token),
                cue="more",
            ),
            Step(
                op="add",
                operand=Quantity(value=offset, unit=reference.unit, source_token=offset_s),
                cue="plus",
            ),
        ),
    )


def _self_verifies_affine_fraction_delta(
    derivation: GroundedDerivation, problem_text: str
) -> SelfVerification:
    reasons: list[str] = []
    tokens = _tokens(problem_text)
    question_clause = _question_clause(problem_text)

    operands = [derivation.start, *(s.operand for s in derivation.steps if not s.comparative)]
    for q in operands:
        if not _value_grounds(q.source_token, tokens):
            reasons.append(f"operand {q.source_token!r} not grounded in text")

    for step in derivation.steps:
        if not _token_in(step.cue, tokens):
            reasons.append(f"operation cue {step.cue!r} not grounded in text")

    primary_unit = derivation.start.unit
    for step in derivation.steps:
        if step.op in {"add", "subtract"} and step.operand.unit != primary_unit:
            reasons.append(
                f"unit mismatch: {step.op} of {step.operand.unit!r} into {primary_unit!r}"
            )

    match = _affine_match(problem_text)
    if match is None:
        reasons.append("missing affine fraction clause")
    else:
        reference = _reference_quantity(problem_text, match.group(3))
        if reference is None:
            reasons.append("missing reference initial-mutation quantity")

    body = problem_text.replace(question_clause, "").strip()
    body_quantities = Counter(q.source_token for q in extract_quantities(body))
    used = Counter(
        [derivation.start.source_token]
        + [step.operand.source_token for step in derivation.steps]
    )
    if match is not None:
        used[match.group(4)] += 1
        used[f"{match.group(1)}/{match.group(2)}"] += 1
        used[match.group(1)] += 1
        used[match.group(2)] += 1
        reference_candidate = _reference_candidate(problem_text, match.group(3))
        if reference_candidate is not None:
            for token in reference_candidate.consumed_value_tokens:
                used[token] += 1
    unused = body_quantities - used
    if unused:
        reasons.append(f"incomplete: unused body quantities {sorted(unused.elements())}")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_affine_fraction_delta(problem_text: str) -> Resolution | None:
    """Gate the typed affine fraction-delta chain through self-verification."""
    derivation = build_affine_fraction_delta(problem_text)
    if derivation is None:
        return None
    if not _self_verifies_affine_fraction_delta(derivation, problem_text).verified:
        return None
    return Resolution(
        answer=derivation.answer,
        answer_unit=derivation.answer_unit,
        derivation=derivation,
    )


def resolve_promotable_affine_fraction_delta(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2n)."""
    return compose_affine_fraction_delta(problem_text)