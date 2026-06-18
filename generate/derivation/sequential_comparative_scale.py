"""Gate A2p — sequential comparative scale (running quantity × scale factors).

Sprint 10: train_sample **0006** — an initial quantity plus an ordered chain of
``N times longer`` / ``times the previous length`` scale factors applied to a
running state.

Chain:

    answer = initial × scale₁ × scale₂ × … × scaleₙ

Narrow organ — not broad ``multiplicative_aggregate``, not age-timeline parsing,
not generic nearby-number multiplication.  Promotion requires:

- question asks ``how many pages``;
- body states an initial ``<N> pages`` anchor;
- at least two scale clauses with ``times longer`` or ``times the previous length``;
- hazard refusal (fractions, percent, money, goal language, ``doubled`` surfaces);
- age/year scaffolding excluded from completeness obligation.

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
from generate.math_roundtrip import _token_in, _tokens, _value_grounds

_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+\s*/\s*\d+")
_INITIAL_PAGES_RE: Final[re.Pattern[str]] = re.compile(
    r"(\d+)\s+pages\b",
    re.IGNORECASE,
)
_READER_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(\w+)\s+started\s+reading\b",
    re.IGNORECASE,
)
_QUESTION_READER_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bbooks\s+(\w+)\s+reads\b", re.IGNORECASE),
    re.compile(r"\b(\w+)'s\s+books\b", re.IGNORECASE),
    re.compile(r"\bdoes\s+(\w+)\s+read\b", re.IGNORECASE),
)
_PRONOUN_SUBJECTS: Final[frozenset[str]] = frozenset(
    {"he", "she", "they", "them", "him", "her", "it", "we", "you", "i"}
)
_SCALE_LONGER_RE: Final[re.Pattern[str]] = re.compile(
    r"(\d+)\s+times\s+longer\b",
    re.IGNORECASE,
)
_SCALE_PREVIOUS_RE: Final[re.Pattern[str]] = re.compile(
    r"(\d+)\s+times\s+the\s+previous\s+length\b",
    re.IGNORECASE,
)
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "doubled",
        "insurance",
        "percent",
        "percentage",
        "profit",
        "weight",
        "weighed",
        "pounds",
        "pound",
    }
)
_GOAL_INTENT: Final[frozenset[str]] = frozenset(
    {"want", "wants", "wanted", "need", "needs", "goal", "plans"}
)
_SCALE_OBLIGATION_UNITS: Final[frozenset[str]] = frozenset({"pages", "times"})


def _asks_page_count(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "how" in tokens and "many" in tokens and "pages" in tokens


def _reader(problem_text: str) -> str | None:
    match = _READER_RE.search(problem_text)
    if match is None:
        return None
    return match.group(1).lower()


def _explicit_page_question_reader(question_clause: str) -> str | None:
    for pattern in _QUESTION_READER_PATTERNS:
        match = pattern.search(question_clause)
        if match is None:
            continue
        subject = match.group(1).lower()
        if subject not in _PRONOUN_SUBJECTS:
            return subject
    return None


def _question_target_matches_reader(problem_text: str, question_clause: str) -> bool:
    explicit_reader = _explicit_page_question_reader(question_clause)
    if explicit_reader is None:
        return True
    body_reader = _reader(problem_text)
    return body_reader is not None and explicit_reader == body_reader


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _FRACTION_RE.search(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "%" in problem_text:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _GOAL_INTENT:
        return True
    if "$" in problem_text:
        return True
    return False


def _initial_pages(problem_text: str) -> Quantity | None:
    match = _INITIAL_PAGES_RE.search(problem_text)
    if match is None:
        return None
    value = float(match.group(1))
    return Quantity(value=value, unit="pages", source_token=match.group(1))


def _scale_factors_in_order(problem_text: str) -> list[tuple[float, str, str]]:
    """Return ``(value, source_token, cue)`` for each scale clause in narrative order."""
    factors: list[tuple[float, str, str]] = []
    for match in _SCALE_LONGER_RE.finditer(problem_text):
        factors.append((float(match.group(1)), match.group(1), "longer"))
    for match in _SCALE_PREVIOUS_RE.finditer(problem_text):
        factors.append((float(match.group(1)), match.group(1), "previous"))
    if not factors:
        return []
    # Re-sort by position in text to preserve narrative order when both patterns appear.
    ordered: list[tuple[float, str, str, int]] = []
    for match in _SCALE_LONGER_RE.finditer(problem_text):
        ordered.append((float(match.group(1)), match.group(1), "longer", match.start()))
    for match in _SCALE_PREVIOUS_RE.finditer(problem_text):
        ordered.append(
            (float(match.group(1)), match.group(1), "previous", match.start())
        )
    ordered.sort(key=lambda item: item[3])
    return [(v, token, cue) for v, token, cue, _ in ordered]


def build_sequential_comparative_scale(problem_text: str) -> GroundedDerivation | None:
    """Construct the ungated sequential scale chain, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_page_count(question_clause):
        return None
    if not _question_target_matches_reader(problem_text, question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    initial = _initial_pages(problem_text)
    factors = _scale_factors_in_order(problem_text)
    if initial is None or len(factors) < 2:
        return None

    steps = tuple(
        Step(
            op="multiply",
            operand=Quantity(value=value, unit="times", source_token=token),
            cue=cue,
        )
        for value, token, cue in factors
    )
    return GroundedDerivation(start=initial, steps=steps)


def _obligation_quantities(problem_text: str) -> Counter[str]:
    return Counter(
        q.source_token
        for q in extract_quantities(problem_text)
        if q.unit in _SCALE_OBLIGATION_UNITS
    )


def _self_verifies_sequential_scale(
    derivation: GroundedDerivation, problem_text: str
) -> SelfVerification:
    from generate.derivation.verify import _base_reasons

    tokens = _tokens(problem_text)
    reasons = list(_base_reasons(derivation, tokens))

    for step in derivation.steps:
        if not _token_in(step.cue, tokens):
            reasons.append(f"operation cue {step.cue!r} not grounded in text")

    obligation = _obligation_quantities(problem_text)
    used = Counter(
        [
            derivation.start.source_token,
            *(step.operand.source_token for step in derivation.steps),
        ]
    )
    unused = obligation - used
    if unused:
        reasons.append(f"incomplete: unused scale quantities {sorted(unused.keys())}")

    initial = _initial_pages(problem_text)
    if initial is None or not _value_grounds(initial.source_token, tokens):
        reasons.append("missing grounded initial pages anchor")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_sequential_comparative_scale(problem_text: str) -> Resolution | None:
    """Gate the typed sequential scale chain through self-verification."""
    derivation = build_sequential_comparative_scale(problem_text)
    if derivation is None:
        return None
    if not _self_verifies_sequential_scale(derivation, problem_text).verified:
        return None
    return Resolution(
        answer=derivation.answer,
        answer_unit=derivation.answer_unit,
        derivation=derivation,
    )


def resolve_promotable_sequential_comparative_scale(
    problem_text: str,
) -> Resolution | None:
    """Serving promotion bridge (Gate A2p)."""
    return compose_sequential_comparative_scale(problem_text)
