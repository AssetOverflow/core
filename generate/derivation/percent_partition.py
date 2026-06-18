"""Gate A2l — equal half-split percent partition aggregate.

Experience Flywheel Sprint 8 / composition-validation **cv-0008** (train_sample
**0046**): total population, equal ``half`` girls / ``other half`` boys split,
two subgroup ``N% of the <group>`` clauses, question asks how many total own the
attribute.

    subgroup = total × half
    answer = subgroup × pct_girls + subgroup × pct_boys

Narrow organ — not a generic percent equation parser, not unequal partitions, not
multi-container DCS.  Promotion requires:

- question asks ``how many`` + aggregate ownership cue;
- total population quantity with unit;
- equal half / other-half split language;
- exactly two percent-of-subgroup clauses with distinct group referents;
- hazard refusal (fraction surfaces, money, profit, goal language).

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.comparatives import comparative_step, extract_comparative_scalars
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, SelfVerification
from generate.math_roundtrip import _tokens

_PERCENT_OF_GROUP_RE: Final[re.Pattern[str]] = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s+of\s+the\s+(\w+)",
    re.IGNORECASE,
)
_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+\s*/\s*\d+")
_GOAL_INTENT: Final[frozenset[str]] = frozenset(
    {"want", "wants", "wanted", "need", "needs", "hoping", "hopes", "plans", "aims", "goal"}
)
_OWNERSHIP_CUES: Final[frozenset[str]] = frozenset(
    {"own", "owns", "have", "has", "had"}
)


def _asks_partition_total(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "how" in tokens and "many" in tokens and bool(_OWNERSHIP_CUES & tokens)


def _has_equal_half_split(problem_text: str) -> bool:
    lowered = problem_text.lower()
    return "half" in lowered and "other half" in lowered


def _percent_clauses(problem_text: str) -> tuple[tuple[float, str, str], tuple[float, str, str]] | None:
    question_clause = _question_clause(problem_text)
    matches: list[tuple[float, str, str]] = []
    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        for match in _PERCENT_OF_GROUP_RE.finditer(clause):
            pct = float(match.group(1)) / 100.0
            group = match.group(2).lower()
            source = match.group(1)
            matches.append((pct, group, source))
    if len(matches) != 2:
        return None
    groups = {m[1] for m in matches}
    if len(groups) != 2:
        return None
    return matches[0], matches[1]


def _total_population(problem_text: str, question_clause: str) -> Quantity | None:
    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        lowered = clause.lower()
        if "half" in lowered or _PERCENT_OF_GROUP_RE.search(clause):
            continue
        if "group" in lowered:
            continue
        quantities = [q for q in extract_quantities(clause) if q.unit]
        if len(quantities) == 1:
            return quantities[0]
    return None


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    text_tokens = _tokens(problem_text)
    if _FRACTION_RE.search(problem_text):
        return True
    if text_tokens & _GOAL_INTENT:
        return True
    if "profit" in text_tokens or "money" in text_tokens or "$" in problem_text:
        return True
    if not _has_equal_half_split(problem_text):
        return True
    comparatives = extract_comparative_scalars(problem_text)
    if not any(cs.cue == "half" for cs in comparatives):
        return True
    return False


def build_percent_partition(problem_text: str) -> GroundedDerivation | None:
    """Construct equal half-split percent partition total, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_partition_total(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    total = _total_population(problem_text, question_clause)
    percent_pair = _percent_clauses(problem_text)
    if total is None or percent_pair is None:
        return None

    (pct_a, _, source_a), (pct_b, _, source_b) = percent_pair
    comparatives = extract_comparative_scalars(problem_text)
    half = next((cs for cs in comparatives if cs.cue == "half"), None)
    if half is None:
        return None

    subgroup = total.value * half.scalar
    contrib_a = subgroup * pct_a
    contrib_b = subgroup * pct_b

    return GroundedDerivation(
        start=total,
        steps=(
            comparative_step(half),
            Step(
                op="multiply",
                operand=Quantity(value=pct_a, unit="", source_token=source_a),
                cue="of",
            ),
            Step(
                op="add",
                operand=Quantity(value=contrib_b, unit=total.unit, source_token=source_b),
                cue="and",
            ),
        ),
    )


def _self_verifies_percent_partition(
    derivation: GroundedDerivation, problem_text: str
) -> SelfVerification:
    from generate.derivation.verify import _base_reasons

    tokens = _tokens(problem_text)
    reasons = list(_base_reasons(derivation, tokens))

    if _percent_clauses(problem_text) is None:
        reasons.append("expected two distinct percent-of-subgroup clauses")
    if _total_population(problem_text, _question_clause(problem_text)) is None:
        reasons.append("missing total population quantity")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_percent_partition(problem_text: str) -> Resolution | None:
    """Gate the typed percent-partition chain through self-verification."""
    derivation = build_percent_partition(problem_text)
    if derivation is None:
        return None
    if not _self_verifies_percent_partition(derivation, problem_text).verified:
        return None
    return Resolution(
        answer=derivation.answer,
        answer_unit=derivation.answer_unit,
        derivation=derivation,
    )


def resolve_promotable_percent_partition(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2l)."""
    return compose_percent_partition(problem_text)
