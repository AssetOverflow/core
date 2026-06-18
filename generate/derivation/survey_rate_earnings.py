"""Gate A2h — survey rate earnings (survey-count sum × questions/survey × $/question).

Experience Flywheel Sprint 6: ``multiplicative_aggregate`` cluster had recognizer
hits but no sealed-correct lift signal; case **0045** decomposes cleanly as
``(surveys_mon + surveys_tue) × questions_per_survey × rate_per_question`` with
explicit question money binding.

Narrow organ — not broad product_bridge, not generic multiplication over
co-occurring numbers.  Promotion requires:

- question asks ``money`` + ``earn``/``make``/``receive``;
- body states rate per question (``$`` + ``every``/``per`` + ``question``);
- body states ``each/every survey has N questions``;
- exactly two day-indexed survey counts that sum;
- hazard refusal (fractions, percent, profit, comparative distractors).

Question-clause temporal scaffolding (e.g. ``two days``) is excluded from the
completeness obligation — Mon/Tue survey counts already decompose the window.

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
from generate.math_roundtrip import _token_in, _tokens, _value_grounds

_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+/\d+")
_EARN_VERBS: Final[frozenset[str]] = frozenset(
    {"earn", "earned", "make", "made", "receive", "received", "get", "got"}
)
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "half",
        "insurance",
        "percent",
        "percentage",
        "profit",
        "twice",
        "thrice",
    }
)
_QUESTION_BLOCKERS: Final[frozenset[str]] = frozenset(
    {"left", "remaining", "profit"}
)


def _asks_money_earned(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "money" in tokens and bool(_EARN_VERBS & tokens)


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _FRACTION_RE.search(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "%" in problem_text or "percent" in text_tokens:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    return False


def _body_text(problem_text: str) -> str:
    question_clause = _question_clause(problem_text)
    return problem_text.replace(question_clause, "").strip()


def _clause_mentions_survey(clause: str) -> bool:
    tokens = _tokens(clause)
    return "survey" in tokens or "surveys" in tokens


def _survey_counts(problem_text: str) -> tuple[Quantity, Quantity] | None:
    counts: list[Quantity] = []
    question_clause = _question_clause(problem_text)
    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        if not _clause_mentions_survey(clause):
            continue
        for q in extract_quantities(clause):
            if q.unit == "surveys" or q.unit.rstrip("s") == "survey":
                counts.append(
                    Quantity(value=q.value, unit="surveys", source_token=q.source_token)
                )
    if len(counts) != 2:
        return None
    return counts[0], counts[1]


def _questions_per_survey(problem_text: str) -> Quantity | None:
    question_clause = _question_clause(problem_text)
    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        lowered = clause.lower()
        if not _clause_mentions_survey(clause):
            continue
        if not ("each" in _tokens(clause) or "every" in _tokens(clause)):
            continue
        if "questions" not in _tokens(clause) and "question" not in _tokens(clause):
            continue
        quantities = extract_quantities(clause)
        if len(quantities) != 1:
            continue
        q = quantities[0]
        if q.unit not in {"questions", "question"} and q.unit.rstrip("s") != "question":
            continue
        return Quantity(value=q.value, unit="questions", source_token=q.source_token)
    return None


def _rate_per_question(problem_text: str) -> tuple[Quantity, str] | None:
    question_clause = _question_clause(problem_text)
    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        if "$" not in clause and "dollar" not in _tokens(clause):
            continue
        if "question" not in _tokens(clause):
            continue
        rate_cue = next(
            (c for c in ("every", "per", "each") if c in _tokens(clause)),
            None,
        )
        if rate_cue is None:
            continue
        quantities = extract_quantities(clause)
        if len(quantities) != 1:
            continue
        q = quantities[0]
        return Quantity(value=q.value, unit="dollars", source_token=q.source_token), rate_cue
    return None


def build_survey_rate_earnings(problem_text: str) -> GroundedDerivation | None:
    """Construct the ungated survey earnings chain, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_money_earned(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    survey_pair = _survey_counts(problem_text)
    per_survey = _questions_per_survey(problem_text)
    rate_info = _rate_per_question(problem_text)
    if survey_pair is None or per_survey is None or rate_info is None:
        return None

    count_a, count_b = survey_pair
    rate, rate_cue = rate_info
    sum_cue = "and" if "and" in _tokens(problem_text) else None
    if sum_cue is None:
        return None
    has_cue = next((c for c in ("has", "have", "contains") if c in _tokens(problem_text)), None)
    if has_cue is None:
        return None

    return GroundedDerivation(
        start=count_a,
        steps=(
            Step(op="add", operand=count_b, cue=sum_cue),
            Step(op="multiply", operand=per_survey, cue=has_cue),
            Step(op="multiply", operand=rate, cue=rate_cue),
        ),
    )


def _self_verifies_survey_earnings(
    derivation: GroundedDerivation, problem_text: str
) -> SelfVerification:
    """Self-verify with body-scoped completeness (question ``days`` scaffolding)."""
    from generate.derivation.verify import _base_reasons

    tokens = _tokens(problem_text)
    reasons = list(_base_reasons(derivation, tokens))

    body = _body_text(problem_text)
    body_quantities = {q.source_token for q in extract_quantities(body)}
    used = {
        derivation.start.source_token,
        *(step.operand.source_token for step in derivation.steps),
    }
    unused = body_quantities - used
    if unused:
        reasons.append(f"incomplete: unused body quantities {sorted(unused)}")

    for step in derivation.steps:
        if not _token_in(step.cue, tokens):
            reasons.append(f"operation cue {step.cue!r} not grounded in text")
    if not _value_grounds(derivation.start.source_token, tokens):
        reasons.append(
            f"operand {derivation.start.source_token!r} not grounded in text"
        )

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_survey_rate_earnings(problem_text: str) -> Resolution | None:
    """Gate the typed survey earnings chain through self-verification."""
    derivation = build_survey_rate_earnings(problem_text)
    if derivation is None:
        return None
    if not _self_verifies_survey_earnings(derivation, problem_text).verified:
        return None
    return Resolution(
        answer=derivation.answer,
        answer_unit=derivation.answer_unit,
        derivation=derivation,
    )


def resolve_promotable_survey_rate_earnings(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2h)."""
    return compose_survey_rate_earnings(problem_text)