"""Gate A2f — question-bound product aggregate (typed cross-clause / in-clause chain).

Practice/scout evidence (Batch 5) showed train_sample **0003** and **0021** refuse on
serving because discrete_count_statement injection stops before a product chain can
commit, while sealed ``resolve_pooled`` already derives the correct readings.  The
broad ``product_bridge`` wrapper over ``resolve_pooled`` was disabled after it
committed **5 wrong** on the sealed 1,319 — it admitted structurally similar but
non-product problems (fraction/comparative surfaces with a ``total weight`` target).

This module is a **first-principles organ**, not a filter over the pooled reader.
It constructs only two explicit shapes:

1. **Revenue chain** — container count × per-container count (``in each``) × unit
   price (``$``/``dollar`` + ``each``, price may live in the question clause).
2. **Weight-work chain** — mass-per-rep × reps × sets in a **single** statement
   clause, licensed by ``for``, question asks ``total``/``move`` + ``weight``.

Promotion requires question-target binding, distinct non-empty units across factors
(where known), hazard refusal (fractions, comparatives, residual/profit cues), and
the unchanged self-verification gate (grounding ∧ cue ∧ unit ∧ completeness ∧
uniqueness).  Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.multistep import search_chain
from generate.derivation.state.bind import leading_subject_token
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, select_self_verified
from generate.math_roundtrip import _tokens

_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+/\d+")
_COMPARATIVE_CUES: Final[frozenset[str]] = frozenset(
    {"twice", "thrice", "double", "doubled", "half", "triple", "tripled"}
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
_REVENUE_QUESTION_VERBS: Final[frozenset[str]] = frozenset(
    {"make", "earn", "raise", "collect"}
)
_WEIGHT_QUESTION_VERBS: Final[frozenset[str]] = frozenset(
    {"total", "move", "lift", "press"}
)
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


def _asks_revenue_total(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "money" in tokens and bool(_REVENUE_QUESTION_VERBS & tokens)


def _asks_weight_total(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "weight" in tokens and bool(_WEIGHT_QUESTION_VERBS & tokens)


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _FRACTION_RE.search(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if _COMPARATIVE_CUES & text_tokens:
        return True
    if "%" in problem_text or "percent" in text_tokens or "percentage" in text_tokens:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    return False


def _distinct_known_units(derivation: GroundedDerivation) -> bool:
    units = [derivation.start.unit, *(step.operand.unit for step in derivation.steps)]
    non_empty = [unit for unit in units if unit]
    return len(non_empty) == len(set(non_empty))


_IMPERSONAL_SUBJECTS: Final[frozenset[str]] = frozenset(
    {
        "a",
        "an",
        "each",
        "every",
        "if",
        "it",
        "the",
        "there",
        "this",
        "that",
        "when",
        "while",
    }
)


def _named_actor_subjects(problem_text: str) -> set[str]:
    """Collect likely named-actor subjects from quantity-bearing clauses."""
    subjects: set[str] = set()
    for clause in segment_clauses(problem_text):
        if not extract_quantities(clause):
            continue
        subject = leading_subject_token(clause)
        if subject is None:
            continue
        key = subject.lower()
        if key in _IMPERSONAL_SUBJECTS:
            continue
        subjects.add(key)
    return subjects


_SELL_VERBS: Final[frozenset[str]] = frozenset({"sell", "sells", "sold", "selling"})


def _question_named_seller(question_clause: str) -> str | None:
    """Named seller in a conditional question clause, if present."""
    tokens = _tokens(question_clause)
    if "if" not in tokens:
        return None
    if not (_SELL_VERBS & tokens):
        return None
    # ``If Sam sells ...`` — the token immediately after ``if``.
    token_list = question_clause.split()
    for index, word in enumerate(token_list):
        if word.lower() == "if" and index + 1 < len(token_list):
            candidate = token_list[index + 1].strip("',.")
            key = candidate.lower()
            if key not in _IMPERSONAL_SUBJECTS:
                return key
    return None


def _has_conflicting_actor_subjects(problem_text: str) -> bool:
    """Refuse when named suppliers and sellers disagree across clauses."""
    question_clause = _question_clause(problem_text)
    statement_actors = set()
    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        statement_actors |= _named_actor_subjects(clause)
    seller = _question_named_seller(question_clause)
    if seller is not None and statement_actors and seller not in statement_actors:
        return True
    all_actors = _named_actor_subjects(problem_text)
    return len(all_actors) > 1


def _build_revenue_product_chain(problem_text: str) -> GroundedDerivation | None:
    """Container × per-container (``in each``) × unit price — revenue target only."""
    question_clause = _question_clause(problem_text)
    if not _asks_revenue_total(question_clause):
        return None

    factors: list[Quantity] = []
    in_each_seen = False
    price_seen = False

    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        quantities = extract_quantities(clause)
        if len(quantities) != 1:
            continue
        factors.append(quantities[0])
        if "in each" in clause.lower():
            in_each_seen = True

    question_quantities = extract_quantities(question_clause)
    if (
        len(question_quantities) == 1
        and ("$" in question_clause or "dollar" in _tokens(question_clause))
        and "each" in _tokens(question_clause)
    ):
        factors.append(question_quantities[0])
        price_seen = True

    if len(factors) != 3 or not in_each_seen or not price_seen:
        return None

    start, *rest = factors
    return GroundedDerivation(
        start=start,
        steps=tuple(Step(op="multiply", operand=q, cue="each") for q in rest),
    )


def _build_weight_product_chain(problem_text: str) -> GroundedDerivation | None:
    """Mass-per-rep × reps × sets in one clause — total-weight target only."""
    question_clause = _question_clause(problem_text)
    if not _asks_weight_total(question_clause):
        return None

    statement_clauses = [
        clause
        for clause in segment_clauses(problem_text)
        if clause != question_clause and not clause.rstrip().endswith("?")
    ]
    quantity_clauses = [
        clause for clause in statement_clauses if len(extract_quantities(clause)) >= 2
    ]
    if len(quantity_clauses) != 1:
        return None

    clause = quantity_clauses[0]
    quantities = extract_quantities(clause)
    if len(quantities) != 3:
        return None
    if not (_MASS_UNITS & {quantities[0].unit}):
        return None
    if "for" not in _tokens(clause):
        return None

    resolution = search_chain(clause)
    if resolution is None:
        return None

    derivation = resolution.derivation
    if not all(step.op == "multiply" and step.cue == "for" for step in derivation.steps):
        return None
    if not _distinct_known_units(derivation):
        return None
    return derivation


def build_question_bound_product(problem_text: str) -> GroundedDerivation | None:
    """Construct the ungated question-bound product chain, or ``None``."""
    question_clause = _question_clause(problem_text)
    if _has_hazard_surface(problem_text, question_clause):
        return None
    if _has_conflicting_actor_subjects(problem_text):
        return None
    return _build_revenue_product_chain(problem_text) or _build_weight_product_chain(
        problem_text
    )


def compose_question_bound_product(problem_text: str) -> Resolution | None:
    """Gate the typed product chain through self-verification."""
    derivation = build_question_bound_product(problem_text)
    if derivation is None:
        return None
    return select_self_verified([derivation], problem_text, target_units=())


def resolve_promotable_question_bound_product(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2f).

    Narrower than :func:`generate.derivation.product_bridge.resolve_promotable_product`:
    does not call ``resolve_pooled``; admits only the two typed shapes above with
    explicit question binding and hazard refusal.  Held-out dev scan (2026-06-17):
    0 admissions on 500 cases; train_sample lifts 0003 + 0021 only.
    """
    return compose_question_bound_product(problem_text)