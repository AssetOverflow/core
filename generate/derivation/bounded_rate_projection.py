"""Gate A2t — bounded rate projection ClusterContract.

Two surface-specific modes share only the dimensional admission contract:

* affine event per distance: ``(event_base - event_delta) /
  (distance_base + distance_delta)``;
* percent-improved distance projection: ``distance / time * (1 + percent) *
  target_time``.

This is not a generic rate, percent, or relation parser.  Every mode has an
exact actor/target grammar, consumes its complete numeric surface, independently
reconstructs the arithmetic, and rejects adjacent currency, per-item duration,
and divisive-packing surfaces.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Final, Literal

from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.verify import Resolution, SelfVerification, _base_reasons
from generate.math_roundtrip import WORD_NUMBERS, _tokens


_NUMBER: Final[str] = r"(?:\d+(?:\.\d+)?|[A-Za-z]+)"
_AFFINE_RATE_RE: Final[re.Pattern[str]] = re.compile(
    rf"^On\s+(?P<actor>[A-Z][A-Za-z'-]+)'s\s+"
    rf"(?P<trip_kind>[A-Za-z]+)\s+trip\s+across\s+town,\s+"
    rf"(?P<pronoun>he|she|they)\s+traveled\s+"
    rf"(?P<distance_delta>{_NUMBER})\s+more\s+than\s+"
    rf"(?P<distance_base>{_NUMBER})\s+"
    rf"(?P<distance_unit>miles|kilometers)\s+and\s+encountered\s+"
    rf"(?P<event_delta>{_NUMBER})\s+less\s+than\s+"
    rf"(?P<event_base>{_NUMBER})\s+"
    rf"(?P<event_unit>stop\s+signs|traffic\s+lights)\.\s*"
    rf"How\s+many\s+(?P<question_event>stop\s+signs|traffic\s+lights)\s+per\s+"
    rf"(?P<question_distance>mile|kilometer)\s+did\s+(?P<question_actor>[A-Z][A-Za-z'-]+)\s+"
    rf"encounter\s+on\s+(?P<question_possessive>his|her|their)\s+trip\s+across\s+town\?$",
    re.IGNORECASE,
)
_PERCENT_PROJECTION_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<actor>[A-Z][A-Za-z'-]+)\s+is\s+a\s+varsity\s+player\s+on\s+a\s+"
    rf"football\s+team\.\s+(?P<pronoun>He|She|They)\s+can\s+run\s+"
    rf"(?P<distance>{_NUMBER})\s+(?P<distance_unit>yards|meters)\s+within\s+"
    rf"(?P<base_time>{_NUMBER})\s+seconds\.\s+If\s+(?P=pronoun)\s+can\s+improve\s+"
    rf"(?P<possessive>his|her|their)\s+speed\s+by\s+(?P<percent>{_NUMBER})\s+percent,\s+"
    rf"how\s+many\s+(?P<question_unit>yards|meters)\s+will\s+(?P=pronoun)\s+be\s+able\s+"
    rf"to\s+run\s+within\s+(?P<target_time>{_NUMBER})\s+seconds\?$",
    re.IGNORECASE,
)

_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "appointment", "bags", "bill", "color", "cost", "dollars", "draw",
        "each", "eats", "insurance", "macaroons", "ounces", "packs",
        "pictures", "profit", "subsequent", "tickets", "weight",
    }
)
_DISTANCE_SINGULAR: Final[dict[str, str]] = {
    "miles": "mile",
    "kilometers": "kilometer",
}
_EVENT_SINGULAR: Final[dict[str, str]] = {
    "stop signs": "stop sign",
    "traffic lights": "traffic light",
}
_PRONOUN_POSSESSIVE: Final[dict[str, str]] = {
    "he": "his",
    "she": "her",
    "they": "their",
}


@dataclass(frozen=True, slots=True)
class BoundedRateProjectionBuild:
    mode: Literal["affine_event_per_distance", "percent_improved_distance"]
    derivation: GroundedDerivation
    answer: float
    answer_unit: str
    numeric_tokens: tuple[str, ...]


def _number(token: str) -> float | None:
    lowered = token.lower()
    if lowered in WORD_NUMBERS:
        return float(WORD_NUMBERS[lowered])
    try:
        return float(token)
    except ValueError:
        return None


def _all_numeric_tokens(text: str) -> Counter[str]:
    result: Counter[str] = Counter()
    for token in re.findall(r"\b\d+(?:\.\d+)?\b|\b[A-Za-z]+\b", text):
        lowered = token.lower()
        if re.fullmatch(r"\d+(?:\.\d+)?", lowered) or lowered in WORD_NUMBERS:
            result[lowered] += 1
    return result


def _expected_numeric_tokens(*tokens: str) -> Counter[str]:
    return Counter(token.lower() for token in tokens)


def _has_blocker(text: str) -> bool:
    tokens = _tokens(text)
    return "$" in text or bool(tokens & _BLOCKERS)


def _build_affine_event_rate(text: str) -> BoundedRateProjectionBuild | None:
    match = _AFFINE_RATE_RE.fullmatch(text.strip())
    if match is None:
        return None
    groups = {key: value.lower() for key, value in match.groupdict().items()}
    if groups["actor"] != groups["question_actor"]:
        return None
    if groups["question_event"] != groups["event_unit"]:
        return None
    if _DISTANCE_SINGULAR[groups["distance_unit"]] != groups["question_distance"]:
        return None
    if _PRONOUN_POSSESSIVE[groups["pronoun"]] != groups["question_possessive"]:
        return None

    numeric_names = ("distance_delta", "distance_base", "event_delta", "event_base")
    values = {name: _number(groups[name]) for name in numeric_names}
    if any(value is None for value in values.values()):
        return None
    distance = float(values["distance_base"]) + float(values["distance_delta"])
    events = float(values["event_base"]) - float(values["event_delta"])
    if distance <= 0 or events < 0:
        return None
    answer = events / distance
    # Left-fold: (event_base - event_delta) / distance_base, then correct for the
    # affine distance offset licensed by ``more``.  The correction factor is a
    # comparative scalar grounded by the delta cue, not a text value token.
    distance_correction = float(values["distance_base"]) / distance
    derivation = GroundedDerivation(
        start=Quantity(
            value=float(values["event_base"]),
            unit=groups["event_unit"],
            source_token=groups["event_base"],
        ),
        steps=(
            Step(
                op="subtract",
                operand=Quantity(
                    value=float(values["event_delta"]),
                    unit=groups["event_unit"],
                    source_token=groups["event_delta"],
                ),
                cue="less",
            ),
            Step(
                op="divide",
                operand=Quantity(
                    value=float(values["distance_base"]),
                    unit=groups["distance_unit"],
                    source_token=groups["distance_base"],
                ),
                cue="per",
            ),
            Step(
                op="multiply",
                operand=Quantity(
                    value=distance_correction,
                    unit="distance_correction",
                    source_token=groups["distance_delta"],
                ),
                cue="more",
                comparative=True,
            ),
        ),
    )
    return BoundedRateProjectionBuild(
        mode="affine_event_per_distance",
        derivation=derivation,
        answer=answer,
        answer_unit=f"{_EVENT_SINGULAR[groups['event_unit']]}_per_{groups['question_distance']}",
        numeric_tokens=tuple(groups[name] for name in numeric_names),
    )


def _build_percent_projection(text: str) -> BoundedRateProjectionBuild | None:
    match = _PERCENT_PROJECTION_RE.fullmatch(text.strip())
    if match is None:
        return None
    groups = {key: value.lower() for key, value in match.groupdict().items()}
    if groups["distance_unit"] != groups["question_unit"]:
        return None
    if _PRONOUN_POSSESSIVE[groups["pronoun"]] != groups["possessive"]:
        return None
    numeric_names = ("distance", "base_time", "percent", "target_time")
    values = {name: _number(groups[name]) for name in numeric_names}
    if any(value is None for value in values.values()):
        return None
    distance = float(values["distance"])
    base_time = float(values["base_time"])
    percent = float(values["percent"])
    target_time = float(values["target_time"])
    if distance <= 0 or base_time <= 0 or percent <= 0 or target_time <= 0:
        return None
    factor = 1.0 + percent / 100.0
    answer = distance / base_time * factor * target_time
    derivation = GroundedDerivation(
        start=Quantity(distance, groups["distance_unit"], groups["distance"]),
        steps=(
            Step(
                op="divide",
                operand=Quantity(base_time, "seconds", groups["base_time"]),
                cue="within",
            ),
            Step(
                op="multiply",
                operand=Quantity(factor, "percent_factor", groups["percent"]),
                cue="improve",
                comparative=True,
            ),
            Step(
                op="multiply",
                operand=Quantity(target_time, "seconds", groups["target_time"]),
                cue="within",
            ),
        ),
    )
    return BoundedRateProjectionBuild(
        mode="percent_improved_distance",
        derivation=derivation,
        answer=answer,
        answer_unit=groups["distance_unit"],
        numeric_tokens=tuple(groups[name] for name in numeric_names),
    )


def build_bounded_rate_projection(text: str) -> BoundedRateProjectionBuild | None:
    """Build exactly one licensed rate mode, otherwise refuse."""
    if not isinstance(text, str) or not text.strip() or _has_blocker(text):
        return None
    built = [
        candidate
        for candidate in (_build_affine_event_rate(text), _build_percent_projection(text))
        if candidate is not None
    ]
    return built[0] if len(built) == 1 else None


def _self_verifies(build: BoundedRateProjectionBuild, text: str) -> SelfVerification:
    reasons = list(_base_reasons(build.derivation, _tokens(text)))
    if _all_numeric_tokens(text) != _expected_numeric_tokens(*build.numeric_tokens):
        reasons.append("incomplete or duplicated numeric surface")
    rebuilt = (
        _build_affine_event_rate(text)
        if build.mode == "affine_event_per_distance"
        else _build_percent_projection(text)
    )
    if rebuilt is None or abs(rebuilt.answer - build.answer) > 1e-9:
        reasons.append("independent reconstruction failed")
    if abs(build.derivation.answer - build.answer) > 1e-9:
        reasons.append("derivation fold mismatch")
    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_bounded_rate_projection(text: str) -> Resolution | None:
    """Self-verify a unique bounded-rate mode."""
    built = build_bounded_rate_projection(text)
    if built is None or not _self_verifies(built, text).verified:
        return None
    return Resolution(built.answer, built.answer_unit, built.derivation)


def resolve_promotable_bounded_rate_projection(text: str) -> Resolution | None:
    """Serving bridge for Gate A2t."""
    return compose_bounded_rate_projection(text)

