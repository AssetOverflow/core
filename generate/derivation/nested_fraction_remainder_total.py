"""Gate A2r — nested fraction complement remainder total (ClusterContract organ).

Sprint 12: train_sample **0004** — outer ``Half of`` partition, inner ``1/4 of``
subgroup split (morning vs afternoon), known afternoon complement count, question
asks root population ``altogether``.

Chain (0004-class):

    subgroup = afternoon / (1 − inner_fraction)
    total = subgroup / outer_half_scalar = subgroup × 2

Narrow organ — not generic fraction parser, not sealed_elimination, not currency.
Promotion requires ClusterContract positive anchors, explicit target binding, and
0026-class hazard refusal.

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Final

from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, SelfVerification
from generate.math_roundtrip import _token_in, _tokens, _value_grounds

_OUTER_HALF_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)\bhalf\s+of\s+the\s+(\w+)\s+are\s+going\s+to\s+(\w+)\s+camp\b"
)
_INNER_QUARTER_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)\b1/4\s+of\s+the\s+(\w+)\s+going\s+to\s+(\w+)\s+camp\s+are\s+going\s+to\s+\w+\s+camp\b"
)
_MORNING_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)\bgoing\s+to\s+(\w+)\s+camp\s+in\s+the\s+morning\b"
)
_AFTERNOON_COUNT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(\d+)\s+(\w+)\s+are\s+going\s+to\s+(\w+)\s+camp\s+in\s+the\s+afternoon"
)
_EXTRA_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+\s*/\s*\d+")
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "bill",
        "dinner",
        "dollars",
        "each",
        "ice",
        "money",
        "profit",
        "saved",
        "scoops",
    }
)
_QUESTION_BLOCKERS: Final[frozenset[str]] = frozenset(
    {"afternoon", "morning", "scoops"}
)


@dataclass(frozen=True, slots=True)
class _CampBinding:
    population: str
    camp: str
    afternoon_count: float
    afternoon_token: str


def _asks_root_altogether(question_clause: str, population: str) -> bool:
    tokens = _tokens(question_clause)
    return (
        "how" in tokens
        and "many" in tokens
        and population in tokens
        and ("altogether" in tokens or "there" in tokens)
    )


def _asks_subgroup_only(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "camp" in tokens and "altogether" not in tokens


def _parse_camp_binding(problem_text: str) -> _CampBinding | None:
    outer = _OUTER_HALF_RE.search(problem_text)
    inner = _INNER_QUARTER_RE.search(problem_text)
    morning = _MORNING_RE.search(problem_text)
    afternoon = _AFTERNOON_COUNT_RE.search(problem_text)
    if outer is None or inner is None or morning is None or afternoon is None:
        return None

    population = outer.group(1).lower()
    outer_camp = outer.group(2).lower()
    inner_pop = inner.group(1).lower()
    inner_camp = inner.group(2).lower()
    morning_camp = morning.group(1).lower()
    afternoon_count = float(afternoon.group(1))
    afternoon_pop = afternoon.group(2).lower()
    afternoon_camp = afternoon.group(3).lower()

    if not {population, inner_pop, afternoon_pop} == {population}:
        return None
    if not {outer_camp, inner_camp, morning_camp, afternoon_camp} == {outer_camp}:
        return None
    return _CampBinding(
        population=population,
        camp=outer_camp,
        afternoon_count=afternoon_count,
        afternoon_token=afternoon.group(1),
    )


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if "$" in problem_text:
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    if _asks_subgroup_only(question_clause):
        return True
    if "3/4" in problem_text.replace(" ", ""):
        return True
    if "saved" in text_tokens and "each" in text_tokens:
        return True
    fractions = _EXTRA_FRACTION_RE.findall(problem_text)
    if len(fractions) != 1 or fractions[0].replace(" ", "") != "1/4":
        return True
    return False


def _inner_complement_scalar() -> float:
    return 1.0 - (1.0 / 4.0)


def _outer_inverse_half_scalar() -> float:
    return 2.0


def _recompute_total(afternoon_count: float) -> float:
    subgroup = afternoon_count / _inner_complement_scalar()
    return subgroup * _outer_inverse_half_scalar()


def build_nested_fraction_remainder_total(
    problem_text: str,
) -> tuple[GroundedDerivation, float, _CampBinding] | None:
    """Construct the ungated nested-fraction chain, or ``None``."""
    binding = _parse_camp_binding(problem_text)
    if binding is None:
        return None

    question_clause = _question_clause(problem_text)
    if not _asks_root_altogether(question_clause, binding.population):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    afternoon = Quantity(
        value=binding.afternoon_count,
        unit=binding.population,
        source_token=binding.afternoon_token,
    )
    total = _recompute_total(binding.afternoon_count)
    derivation = GroundedDerivation(
        start=afternoon,
        steps=(
            Step(
                op="divide",
                operand=Quantity(
                    value=_inner_complement_scalar(),
                    unit="",
                    source_token="1/4",
                ),
                cue="4",
                comparative=True,
            ),
            Step(
                op="multiply",
                operand=Quantity(
                    value=_outer_inverse_half_scalar(),
                    unit="",
                    source_token="half",
                ),
                cue="half",
                comparative=True,
            ),
        ),
    )
    return derivation, total, binding


def _self_verifies_nested_fraction(
    derivation: GroundedDerivation,
    problem_text: str,
    expected_total: float,
    binding: _CampBinding,
) -> SelfVerification:
    tokens = _tokens(problem_text)
    reasons: list[str] = []

    if not _operand_grounds(derivation.start, tokens):
        reasons.append(f"operand {derivation.start.source_token!r} not grounded in text")

    for step in derivation.steps:
        if not step.comparative and not _operand_grounds(step.operand, tokens):
            reasons.append(f"operand {step.operand.source_token!r} not grounded in text")
        if not _token_in(step.cue, tokens):
            reasons.append(f"operation cue {step.cue!r} not grounded in text")

    if _parse_camp_binding(problem_text) is None:
        reasons.append("missing camp partition binding")
    elif abs(_recompute_total(binding.afternoon_count) - expected_total) > 1e-9:
        reasons.append("arithmetic mismatch on nested fraction total")

    if abs(derivation.answer - expected_total) > 1e-9:
        reasons.append("derivation fold mismatch")

    obligation = Counter(
        q.source_token
        for q in extract_quantities(problem_text)
        if q.unit == binding.population and q.source_token.isdigit()
    )
    used = Counter([derivation.start.source_token])
    unused = obligation - used
    if unused:
        reasons.append(
            f"incomplete: unused {binding.population} quantities {sorted(unused.keys())}"
        )

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def _operand_grounds(q: Quantity, tokens: frozenset[str]) -> bool:
    return _value_grounds(q.source_token, tokens)


def compose_nested_fraction_remainder_total(problem_text: str) -> Resolution | None:
    """Gate the typed nested-fraction chain through self-verification."""
    built = build_nested_fraction_remainder_total(problem_text)
    if built is None:
        return None
    derivation, total, binding = built
    if not _self_verifies_nested_fraction(derivation, problem_text, total, binding).verified:
        return None
    return Resolution(
        answer=total,
        answer_unit=binding.population,
        derivation=derivation,
    )


def resolve_promotable_nested_fraction_remainder_total(
    problem_text: str,
) -> Resolution | None:
    """Serving promotion bridge (Gate A2r, ClusterContract nested_fraction)."""
    return compose_nested_fraction_remainder_total(problem_text)
