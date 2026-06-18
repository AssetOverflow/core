"""Gate A2o — affine comparative inversion total.

Sprint 10: train_sample **0009** — nested comparative
``N more <unitA> than M times <unitB>`` with a conditional given in the
question and an aggregate ``total <unitTotal>`` target.

Chain:

    implied_B = (given_A − N) / M
    total = given_A + implied_B

Narrow organ — not a generic conditional parser, not ``determine(answer=False)``,
not broad ``conditional_aggregate``.  Promotion requires:

- exactly one nested comparative clause in the body;
- question carries ``If <actor> has <given> <unitA>`` matching the body actor;
- question asks ``how many total <unitTotal>``;
- body unitA and unitB are distinct countable nouns;
- hazard refusal (fractions, percent, money, profit, goal language).

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from typing import Final

from collections import Counter

from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, SelfVerification
from generate.math_roundtrip import WORD_NUMBERS, _tokens, _value_grounds

_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+\s*/\s*\d+")
_NESTED_COMPARATIVE_RE: Final[re.Pattern[str]] = re.compile(
    r"\bhas\s+(\d+|\w+)\s+more\s+(\w+)\s+than\s+(\d+|\w+)\s+times\s+"
    r"(?:the\s+(?:number\s+of\s+)?)?(\w+)\b",
    re.IGNORECASE,
)
_CONDITIONAL_GIVEN_RE: Final[re.Pattern[str]] = re.compile(
    r"\bif\s+(\w+)\s+has\s+(\d+)\s+(\w+)\b",
    re.IGNORECASE,
)
_TOTAL_QUESTION_RE: Final[re.Pattern[str]] = re.compile(
    r"\bhow\s+many\s+total\s+(\w+)\b",
    re.IGNORECASE,
)
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "dollar",
        "dollars",
        "earn",
        "earned",
        "insurance",
        "percent",
        "percentage",
        "profit",
        "raise",
        "raised",
        "week",
        "weeks",
    }
)
_GOAL_INTENT: Final[frozenset[str]] = frozenset(
    {"want", "wants", "wanted", "need", "needs", "goal", "plans", "save", "saves"}
)


def _parse_numeric_token(token: str) -> float | None:
    if token.isdigit():
        return float(token)
    lower = token.lower()
    if lower in WORD_NUMBERS:
        return float(WORD_NUMBERS[lower])
    return None


def _nested_comparative(problem_text: str) -> re.Match[str] | None:
    matches = list(_NESTED_COMPARATIVE_RE.finditer(problem_text))
    if len(matches) != 1:
        return None
    return matches[0]


def _conditional_given(question_clause: str) -> re.Match[str] | None:
    return _CONDITIONAL_GIVEN_RE.search(question_clause)


def _asks_total_aggregate(question_clause: str) -> re.Match[str] | None:
    return _TOTAL_QUESTION_RE.search(question_clause)


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _FRACTION_RE.search(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "%" in problem_text or "percent" in text_tokens:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _GOAL_INTENT:
        return True
    if "$" in problem_text:
        return True
    return False


def build_affine_comparative_inversion_total(
    problem_text: str,
) -> GroundedDerivation | None:
    """Construct the ungated affine inversion chain, or ``None``."""
    question_clause = _question_clause(problem_text)
    if _has_hazard_surface(problem_text, question_clause):
        return None

    nested = _nested_comparative(problem_text)
    conditional = _conditional_given(question_clause)
    total_q = _asks_total_aggregate(question_clause)
    if nested is None or conditional is None or total_q is None:
        return None

    offset_token = nested.group(1)
    unit_a = nested.group(2).lower().rstrip("s")
    factor_token = nested.group(3)
    unit_b = nested.group(4).lower().rstrip("s")
    # Actor is the subject before "has" in the nested clause — recover from match context.
    actor_match = re.search(
        r"(\w+)\s+has\s+" + re.escape(offset_token) + r"\s+more",
        problem_text,
        re.IGNORECASE,
    )
    if actor_match is None:
        return None
    body_actor_name = actor_match.group(1).lower()

    offset = _parse_numeric_token(offset_token)
    factor = _parse_numeric_token(factor_token)
    given_value = float(conditional.group(2))
    given_unit = conditional.group(3).lower().rstrip("s")
    question_actor = conditional.group(1).lower()
    total_unit = total_q.group(1).lower().rstrip("s")

    if offset is None or factor is None or factor == 0:
        return None
    if body_actor_name != question_actor:
        return None
    if given_unit != unit_a:
        return None
    if unit_a == unit_b:
        return None
    # Question must ask an aggregate umbrella, not a single compared unit.
    if total_unit in {unit_a, unit_b}:
        return None

    given = Quantity(value=given_value, unit=total_unit, source_token=conditional.group(2))
    offset_q = Quantity(value=offset, unit=total_unit, source_token=offset_token)
    factor_q = Quantity(value=factor, unit=total_unit, source_token=factor_token)

    return GroundedDerivation(
        start=given,
        steps=(
            Step(op="subtract", operand=offset_q, cue="more"),
            Step(op="divide", operand=factor_q, cue="times"),
            Step(op="add", operand=given, cue="total"),
        ),
    )


def _self_verifies_affine_inversion(
    derivation: GroundedDerivation, problem_text: str
) -> SelfVerification:
    from generate.derivation.verify import _base_reasons

    tokens = _tokens(problem_text)
    reasons = list(_base_reasons(derivation, tokens))

    nested = _nested_comparative(problem_text)
    if nested is None:
        reasons.append("missing nested comparative clause")
    else:
        for token in (nested.group(1), nested.group(3)):
            if not _value_grounds(token, tokens):
                reasons.append(f"comparative token {token!r} not grounded in text")

    obligation = Counter(
        q.source_token
        for q in extract_quantities(problem_text)
        if q.unit not in {"times", ""}
    )
    used = Counter(
        [
            derivation.start.source_token,
            *(step.operand.source_token for step in derivation.steps),
        ]
    )
    unused = obligation - used
    if unused:
        reasons.append(f"incomplete: unused obligation quantities {sorted(unused.keys())}")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_affine_comparative_inversion_total(problem_text: str) -> Resolution | None:
    """Gate the typed affine inversion chain through self-verification."""
    derivation = build_affine_comparative_inversion_total(problem_text)
    if derivation is None:
        return None
    if not _self_verifies_affine_inversion(derivation, problem_text).verified:
        return None
    return Resolution(
        answer=derivation.answer,
        answer_unit=derivation.answer_unit,
        derivation=derivation,
    )


def resolve_promotable_affine_comparative_inversion_total(
    problem_text: str,
) -> Resolution | None:
    """Serving promotion bridge (Gate A2o)."""
    return compose_affine_comparative_inversion_total(problem_text)