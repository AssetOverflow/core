"""Gate A2k — fraction-decrease delta (decrease-to fraction of base).

Experience Flywheel Sprint 8 / composition-validation **cv-0007** (train_sample
**0005**): forecast clause states a quantity will ``decrease to N/M of`` its
current value; a follow-on clause states the current amount; the question asks
the **decrease by** delta (not the final value).

    decrease_by = base × (1 − N/M)

Narrow organ — not a generic affine equation parser, not ``N/M more than`` affine
surfaces (0010-class), not percent-decrease.  Promotion requires:

- exactly one ``decrease to N/M of`` forecast (no ``more than`` fraction affine);
- question binds ``decrease`` + ``by`` (delta target, not final-value question);
- exactly one explicit current/base quantity with a unit;
- hazard refusal (percent, goal language, multiple decrease-to fractions).

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, SelfVerification, select_self_verified
from generate.math_roundtrip import _tokens

_DECREASE_TO_FRACTION_RE: Final[re.Pattern[str]] = re.compile(
    r"decrease\s+to\s+(\d+)\s*/\s*(\d+)\s+of",
    re.IGNORECASE,
)
_EXTRA_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+/\d+")
_GOAL_INTENT: Final[frozenset[str]] = frozenset(
    {"want", "wants", "wanted", "need", "needs", "hoping", "hopes", "plans", "aims", "goal"}
)
_FINAL_VALUE_CUES: Final[frozenset[str]] = frozenset({"be", "will", "what"})


def _asks_decrease_delta(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "decrease" in tokens and "by" in tokens


def _asks_final_value(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    if "by" in tokens:
        return False
    if "decrease" not in tokens:
        return False
    return bool(_FINAL_VALUE_CUES & tokens) or "temperature" in tokens


def _target_fraction(problem_text: str) -> tuple[int, int, str] | None:
    matches = list(_DECREASE_TO_FRACTION_RE.finditer(problem_text))
    if len(matches) != 1:
        return None
    num_s, den_s = matches[0].group(1), matches[0].group(2)
    try:
        num = int(num_s)
        den = int(den_s)
    except ValueError:
        return None
    if num <= 0 or den <= 0 or num >= den:
        return None
    return num, den, f"{num_s}/{den_s}"


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "more" in text_tokens and "than" in text_tokens:
        return True
    if "%" in problem_text or "percent" in text_tokens or "percentage" in text_tokens:
        return True
    if text_tokens & _GOAL_INTENT:
        return True
    if _asks_final_value(question_clause):
        return True
    fractions = _EXTRA_FRACTION_RE.findall(problem_text)
    target = _target_fraction(problem_text)
    if target is None:
        return True
    _, _, token = target
    extra = [f for f in fractions if f.replace(" ", "") != token.replace(" ", "")]
    return len(extra) > 0


def _current_base_quantity(problem_text: str, question_clause: str) -> Quantity | None:
    for clause in segment_clauses(problem_text):
        tokens = _tokens(clause)
        if "current" not in tokens and "now" not in tokens:
            continue
        quantities = [q for q in extract_quantities(clause) if q.unit]
        if len(quantities) == 1:
            return quantities[0]
    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        quantities = [q for q in extract_quantities(clause) if q.unit]
        if len(quantities) == 1:
            return quantities[0]
    return None


def build_fraction_decrease(problem_text: str) -> GroundedDerivation | None:
    """Construct ``base × (1 − N/M)`` decrease delta, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_decrease_delta(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    fraction = _target_fraction(problem_text)
    base = _current_base_quantity(problem_text, question_clause)
    if fraction is None or base is None:
        return None

    num, den, source_token = fraction
    delta_factor = 1.0 - (num / den)
    if delta_factor <= 0:
        return None

    return GroundedDerivation(
        start=base,
        steps=(
            Step(
                op="multiply",
                operand=Quantity(
                    value=delta_factor,
                    unit="",
                    source_token=source_token,
                ),
                cue="decrease",
            ),
        ),
    )


def _self_verifies_fraction_decrease(
    derivation: GroundedDerivation, problem_text: str
) -> SelfVerification:
    from generate.derivation.verify import _base_reasons

    tokens = _tokens(problem_text)
    reasons = list(_base_reasons(derivation, tokens))

    fraction = _target_fraction(problem_text)
    if fraction is None:
        reasons.append("missing decrease-to fraction forecast")
    else:
        _, _, token = fraction
        if token not in problem_text.replace(" ", ""):
            reasons.append(f"fraction token {token!r} not grounded in text")

    base = _current_base_quantity(problem_text, _question_clause(problem_text))
    if base is None:
        reasons.append("missing explicit current/base quantity")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_fraction_decrease(problem_text: str) -> Resolution | None:
    """Gate the typed fraction-decrease chain through self-verification."""
    derivation = build_fraction_decrease(problem_text)
    if derivation is None:
        return None
    if not _self_verifies_fraction_decrease(derivation, problem_text).verified:
        return None
    return Resolution(
        answer=derivation.answer,
        answer_unit=derivation.answer_unit,
        derivation=derivation,
    )


def resolve_promotable_fraction_decrease(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2k)."""
    return compose_fraction_decrease(problem_text)