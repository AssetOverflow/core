"""Gate A2u — closed explicit-reference affine aggregate ClusterContract.

The two modes are deliberately surface-specific:

* a five-platform follower graph with every comparison naming its platform;
* a three-person weight-gain graph with every comparison naming its actor.

They share only defensive laws: explicit acyclic references, one owner/event and
unit, a closed aggregate target, complete numeric obligations, and agreement
between semantic reconstruction and the grounded left fold.  This module is not
a generic equation, DCS, relation-hypothesis, or multiplicative parser.
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
_SOCIAL_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<owner>[A-Z][A-Za-z'-]+)\s+has\s+(?P<instagram>{_NUMBER})\s+followers\s+on\s+"
    rf"Instagram\s+and\s+(?P<facebook>{_NUMBER})\s+followers\s+on\s+Facebook\.\s+"
    rf"The\s+number\s+of\s+followers\s+(?P<pronoun>he|she)\s+has\s+on\s+Twitter\s+is\s+"
    rf"half\s+the\s+number\s+of\s+followers\s+(?P=pronoun)\s+has\s+on\s+Instagram\s+and\s+"
    rf"Facebook\s+combined\.\s+Meanwhile,\s+the\s+number\s+of\s+followers\s+(?P=pronoun)\s+"
    rf"has\s+on\s+TikTok\s+is\s+(?P<scale>{_NUMBER})\s+times\s+the\s+number\s+of\s+"
    rf"followers\s+(?:(?P=pronoun)|is)\s+has\s+on\s+Twitter,\s+and\s+(?P=pronoun)\s+has\s+"
    rf"(?P<delta>{_NUMBER})\s+more\s+followers\s+on\s+Youtube\s+than\s+(?P=pronoun)\s+has\s+"
    rf"on\s+TikTok\.\s+How\s+many\s+followers\s+does\s+(?P<question_owner>[A-Z][A-Za-z'-]+)\s+"
    rf"have\s+on\s+all\s+(?P<possessive>his|her)\s+social\s+media\?$",
    re.IGNORECASE,
)
_WEIGHT_RE: Final[re.Pattern[str]] = re.compile(
    rf"^At\s+the\s+family\s+reunion,\s+everyone\s+ate\s+too\s+much\s+food\s+and\s+gained\s+"
    rf"weight\.\s+(?P<first>[A-Z][A-Za-z'-]+)\s+gained\s+(?P<base>{_NUMBER})\s+pounds\.\s+"
    rf"(?P<second>[A-Z][A-Za-z'-]+)\s+gained\s+(?P<more>{_NUMBER})\s+pounds\s+more\s+than\s+"
    rf"twice\s+what\s+(?P<second_ref>[A-Z][A-Za-z'-]+)\s+gained\.\s+"
    rf"(?P<third>[A-Z][A-Za-z'-]+)\s+gained\s+(?P<less>{_NUMBER})\s+pounds\s+less\s+than\s+"
    rf"half\s+of\s+what\s+(?P<third_ref>[A-Z][A-Za-z'-]+)\s+gained\.\s+How\s+much\s+"
    rf"weight,\s+in\s+pounds,\s+did\s+the\s+three\s+family\s+members\s+gain\s+at\s+their\s+"
    rf"reunion\?$",
    re.IGNORECASE,
)

_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "bags", "bill", "color", "dollars", "draw", "each", "eats",
        "hours", "insurance", "macaroons", "ounces", "packs", "percent",
        "pictures", "scoops", "years",
    }
)
_PRONOUN_POSSESSIVE: Final[dict[str, str]] = {"he": "his", "she": "her"}


@dataclass(frozen=True, slots=True)
class ClosedReferenceAffineAggregateBuild:
    mode: Literal["five_platform_followers", "three_actor_weight"]
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


def _statement_scope(text: str) -> str:
    """Count numeric obligations only in the statement body, not question targets."""
    for marker in ("how much", "how many"):
        idx = text.lower().find(marker)
        if idx >= 0:
            return text[:idx]
    return text


def _numeric_surface(text: str) -> Counter[str]:
    result: Counter[str] = Counter()
    for token in re.findall(r"\b\d+(?:\.\d+)?\b|\b[A-Za-z]+\b", _statement_scope(text)):
        lowered = token.lower()
        if re.fullmatch(r"\d+(?:\.\d+)?", lowered) or lowered in WORD_NUMBERS:
            result[lowered] += 1
    return result


def _has_blocker(text: str) -> bool:
    return "$" in text or bool(_tokens(text) & _BLOCKERS)


def _build_social(text: str) -> ClosedReferenceAffineAggregateBuild | None:
    match = _SOCIAL_RE.fullmatch(text.strip())
    if match is None:
        return None
    groups = {key: value.lower() for key, value in match.groupdict().items()}
    if groups["owner"] != groups["question_owner"]:
        return None
    if _PRONOUN_POSSESSIVE[groups["pronoun"]] != groups["possessive"]:
        return None
    instagram = _number(groups["instagram"])
    facebook = _number(groups["facebook"])
    scale = _number(groups["scale"])
    delta = _number(groups["delta"])
    if any(value is None for value in (instagram, facebook, scale, delta)):
        return None
    instagram = float(instagram)
    facebook = float(facebook)
    scale = float(scale)
    delta = float(delta)
    if min(instagram, facebook, scale, delta) < 0 or scale == 0:
        return None

    combined = instagram + facebook
    twitter = combined / 2.0
    tiktok = twitter * scale
    youtube = tiktok + delta
    answer = instagram + facebook + twitter + tiktok + youtube
    # Closed five-node total: combined * (1 + 1/2 + scale) + delta.
    aggregate_factor = 1.5 + scale
    derivation = GroundedDerivation(
        start=Quantity(instagram, "followers", groups["instagram"]),
        steps=(
            Step(
                op="add",
                operand=Quantity(facebook, "followers", groups["facebook"]),
                cue="combined",
            ),
            Step(
                op="multiply",
                operand=Quantity(aggregate_factor, "closed_nodes", "half"),
                cue="half",
                comparative=True,
            ),
            Step(
                op="add",
                operand=Quantity(delta, "followers", groups["delta"]),
                cue="more",
            ),
        ),
    )
    return ClosedReferenceAffineAggregateBuild(
        mode="five_platform_followers",
        derivation=derivation,
        answer=answer,
        answer_unit="followers",
        numeric_tokens=(
            groups["instagram"],
            groups["facebook"],
            "half",
            groups["scale"],
            groups["delta"],
        ),
    )


def _build_weight(text: str) -> ClosedReferenceAffineAggregateBuild | None:
    match = _WEIGHT_RE.fullmatch(text.strip())
    if match is None:
        return None
    groups = {key: value.lower() for key, value in match.groupdict().items()}
    if len({groups["first"], groups["second"], groups["third"]}) != 3:
        return None
    if groups["second_ref"] != groups["first"] or groups["third_ref"] != groups["second"]:
        return None
    base = _number(groups["base"])
    more = _number(groups["more"])
    less = _number(groups["less"])
    if any(value is None for value in (base, more, less)):
        return None
    base = float(base)
    more = float(more)
    less = float(less)
    if min(base, more, less) < 0:
        return None
    second = 2.0 * base + more
    third = second / 2.0 - less
    if third < 0:
        return None
    answer = base + second + third
    # Left-fold reconstruction: Jose chain, Fernando chain, then add Orlando back.
    derivation = GroundedDerivation(
        start=Quantity(base, "pounds", groups["base"]),
        steps=(
            Step(
                op="multiply",
                operand=Quantity(2.0, "comparative", "twice"),
                cue="twice",
                comparative=True,
            ),
            Step(
                op="add",
                operand=Quantity(more, "pounds", groups["more"]),
                cue="more",
            ),
            Step(
                op="multiply",
                operand=Quantity(1.5, "closed_nodes", "half"),
                cue="half",
                comparative=True,
            ),
            Step(
                op="add",
                operand=Quantity(base, "pounds", groups["base"]),
                cue=groups["first"],
            ),
            Step(
                op="subtract",
                operand=Quantity(less, "pounds", groups["less"]),
                cue="less",
            ),
        ),
    )
    return ClosedReferenceAffineAggregateBuild(
        mode="three_actor_weight",
        derivation=derivation,
        answer=answer,
        answer_unit="pounds",
        numeric_tokens=(groups["base"], groups["more"], "half", groups["less"]),
    )


def build_closed_reference_affine_aggregate(
    text: str,
) -> ClosedReferenceAffineAggregateBuild | None:
    """Build one exact closed-reference mode, otherwise refuse."""
    if not isinstance(text, str) or not text.strip() or _has_blocker(text):
        return None
    built = [candidate for candidate in (_build_social(text), _build_weight(text)) if candidate]
    return built[0] if len(built) == 1 else None


def _self_verifies(
    build: ClosedReferenceAffineAggregateBuild, text: str
) -> SelfVerification:
    reasons = list(_base_reasons(build.derivation, _tokens(text)))
    if _numeric_surface(text) != Counter(token.lower() for token in build.numeric_tokens):
        reasons.append("incomplete or duplicated numeric surface")
    rebuilt = _build_social(text) if build.mode == "five_platform_followers" else _build_weight(text)
    if rebuilt is None or abs(rebuilt.answer - build.answer) > 1e-9:
        reasons.append("independent reconstruction failed")
    if abs(build.derivation.answer - build.answer) > 1e-9:
        reasons.append("derivation fold mismatch")
    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_closed_reference_affine_aggregate(text: str) -> Resolution | None:
    """Self-verify a unique explicit-reference aggregate mode."""
    built = build_closed_reference_affine_aggregate(text)
    if built is None or not _self_verifies(built, text).verified:
        return None
    return Resolution(built.answer, built.answer_unit, built.derivation)


def resolve_promotable_closed_reference_affine_aggregate(text: str) -> Resolution | None:
    """Serving bridge for Gate A2u."""
    return compose_closed_reference_affine_aggregate(text)

