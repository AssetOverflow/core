"""Serving promotion gate for complete product derivations.

The pooled derivation reader can solve real GSM8K products (0003, 0021),
but it also has known wrong commits.  This module is the promotion boundary:
it admits only product readings whose question target is an aggregate product
target and whose surface lacks the known non-product hazards.

It is deliberately narrower than :func:`generate.derivation.pool.resolve_pooled`.
The pool may continue exploring; this bridge decides what is safe to expose to
the serving candidate-graph path.
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.model import GroundedDerivation
from generate.derivation.pool import resolve_pooled
from generate.derivation.verify import Resolution, classify_derivation
from generate.math_roundtrip import _tokens

_SENTENCE_SPLIT: Final[re.Pattern[str]] = re.compile(r"(?<=[.?!])\s+")
_COMMA_NUMBER_RE: Final[re.Pattern[str]] = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")

_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "back",
        "cover",
        "covered",
        "covers",
        "eat",
        "eats",
        "gave",
        "give",
        "given",
        "gives",
        "insurance",
        "kept",
        "left",
        "less",
        "long",
        "more",
        "profit",
        "remain",
        "remaining",
        "rest",
        "same",
        "spent",
        "spend",
        "subsequent",
    }
)

_QUESTION_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "after",
        "before",
        "left",
        "long",
        "per",
        "profit",
        "remaining",
    }
)

_MASS_UNITS: Final[frozenset[str]] = frozenset(
    {
        "gram",
        "grams",
        "kg",
        "kilogram",
        "kilograms",
        "ounce",
        "ounces",
        "pound",
        "pounds",
    }
)


def _question_clause(problem_text: str) -> str:
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(problem_text.strip()) if s.strip()]
    if not sentences:
        return problem_text
    questions = [s for s in sentences if s.rstrip().endswith("?")]
    return questions[-1] if questions else sentences[-1]


def _is_complete_pure_product(derivation: GroundedDerivation, problem_text: str) -> bool:
    """True only for the pool's complete all-multiply readings."""
    if not derivation.steps:
        return False
    if any(step.op != "multiply" or step.comparative for step in derivation.steps):
        return False
    return classify_derivation(derivation, problem_text) == "complete"


def _has_hazard_surface(problem_text: str, question_text: str) -> bool:
    """Reject surfaces known to ask for non-product reasoning.

    These are structural hazard cues, not case ids: percentage/equation targets,
    residual-state questions, comparative adjustments, prior-state questions,
    and comma-separated thousands that the derivation extractor does not yet read
    as one quantity.
    """
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_text)
    if _COMMA_NUMBER_RE.search(problem_text):
        return True
    if "%" in problem_text or "percent" in text_tokens or "percentage" in text_tokens:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    return False


def _has_product_target(question_text: str, derivation: GroundedDerivation) -> bool:
    """Whether the question asks for a product aggregate this bridge can expose."""
    q_tokens = _tokens(question_text)
    units = {derivation.start.unit, *(step.operand.unit for step in derivation.steps)}

    # Revenue/product value target: unit price times count(s).
    if "money" in q_tokens and ("make" in q_tokens or "earn" in q_tokens):
        return True

    # Physical work/weight target: weight per repetition times repetitions/sets.
    if "weight" in q_tokens and ("total" in q_tokens or "move" in q_tokens):
        return bool(units & _MASS_UNITS)

    return False


def resolve_promotable_product(problem_text: str) -> Resolution | None:
    """Return a serving-safe product resolution, or ``None``.

    This function is intentionally a correction pass over the pooled reader:
    ``resolve_pooled`` supplies the candidate and disagreement rule; this gate
    supplies the promotion invariant that the reader itself lacks.
    """
    question_text = _question_clause(problem_text)
    if _has_hazard_surface(problem_text, question_text):
        return None

    resolution = resolve_pooled(problem_text)
    if resolution is None:
        return None

    derivation = resolution.derivation
    if not _is_complete_pure_product(derivation, problem_text):
        return None
    if not _has_product_target(question_text, derivation):
        return None
    return resolution
