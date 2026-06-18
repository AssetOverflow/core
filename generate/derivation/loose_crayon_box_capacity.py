"""Gate A2s — loose crayon box capacity remainder (ClusterContract organ).

Sprint 12: train_sample **0007** — actor has ``N full boxes`` plus loose items,
friend contributes loose items, conditional total count, derive per-box capacity
from boxed portion, question asks ``how many more boxes`` for all loose items.

Chain (0007-class):

    boxed = total − loose_primary
    per_box = boxed / num_full_boxes
    loose_total = loose_primary + loose_friend
    boxes_needed = loose_total / per_box

Algebraically (single fold):

    boxes_needed = (loose_primary + loose_friend) × num_full_boxes / (total − loose_primary)

Narrow organ — not equal-distribution/DCS (0047), not currency, not weight surfaces.
Promotion requires ClusterContract positive anchors and 0047-class hazard refusal.

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Final

from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, SelfVerification
from generate.math_roundtrip import WORD_NUMBERS, _token_in, _tokens, _value_grounds

_FULL_BOXES_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(\w+)\s+has\s+(\w+)\s+full\s+boxes\s+of\s+(\w+)"
)
_LOOSE_PRIMARY_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(\d+)\s+loose\s+(\w+)"
)
_FRIEND_LOOSE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:\w+\s+)?friend\s+has\s+(\d+)\s+loose"
)
_TOTAL_CONDITIONAL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)total\s+of\s+(\d+)"
)
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "bags",
        "bakes",
        "brother",
        "eats",
        "equal",
        "macaroons",
        "ounces",
        "packs",
        "steve",
        "weighing",
        "weight",
    }
)
_QUESTION_BLOCKERS: Final[frozenset[str]] = frozenset(
    {"ounces", "weight", "per", "macaroons"}
)


def _box_count_token(problem_text: str, num_boxes: float) -> str:
    match = _FULL_BOXES_RE.search(problem_text)
    if match is not None:
        return match.group(2).lower()
    return str(int(num_boxes))


def _resolve_count(token: str) -> float | None:
    lowered = token.lower()
    if lowered in WORD_NUMBERS:
        return float(WORD_NUMBERS[lowered])
    try:
        return float(token)
    except ValueError:
        return None


def _asks_more_boxes(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return (
        "how" in tokens
        and "many" in tokens
        and "more" in tokens
        and "boxes" in tokens
    )


def _asks_per_box(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "each" in tokens or "per" in tokens


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if "$" in problem_text:
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    if _asks_per_box(question_clause):
        return True
    if "equal number" in problem_text.lower():
        return True
    if not _FULL_BOXES_RE.search(problem_text):
        return True
    if not _FRIEND_LOOSE_RE.search(problem_text):
        return True
    if not _TOTAL_CONDITIONAL_RE.search(question_clause):
        return True
    return False


def _parse_bindings(problem_text: str) -> dict[str, float] | None:
    boxes_match = _FULL_BOXES_RE.search(problem_text)
    if boxes_match is None:
        return None
    num_boxes = _resolve_count(boxes_match.group(2))
    if num_boxes is None or num_boxes <= 0:
        return None

    friend_match = _FRIEND_LOOSE_RE.search(problem_text)
    if friend_match is None:
        return None
    friend_pos = friend_match.start()

    loose_primary_matches = [
        match
        for match in _LOOSE_PRIMARY_RE.finditer(problem_text)
        if match.start() < friend_pos
    ]
    if len(loose_primary_matches) != 1:
        return None
    loose_primary = float(loose_primary_matches[0].group(1))
    loose_friend = float(friend_match.group(1))

    total_match = _TOTAL_CONDITIONAL_RE.search(_question_clause(problem_text))
    if total_match is None:
        return None
    total = float(total_match.group(1))

    item_unit = loose_primary_matches[0].group(2).lower()
    return {
        "num_boxes": num_boxes,
        "loose_primary": loose_primary,
        "loose_friend": loose_friend,
        "total": total,
        "item_unit": item_unit,
    }


def _recompute_boxes_needed(bindings: dict[str, float]) -> float:
    boxed = bindings["total"] - bindings["loose_primary"]
    per_box = boxed / bindings["num_boxes"]
    loose_total = bindings["loose_primary"] + bindings["loose_friend"]
    return loose_total / per_box


def build_loose_crayon_box_capacity(
    problem_text: str,
) -> tuple[GroundedDerivation, float] | None:
    """Construct the ungated box-capacity chain, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_more_boxes(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    bindings = _parse_bindings(problem_text)
    if bindings is None:
        return None

    boxed_total = bindings["total"] - bindings["loose_primary"]
    if boxed_total <= 0:
        return None

    loose_total = bindings["loose_primary"] + bindings["loose_friend"]
    answer = _recompute_boxes_needed(bindings)

    item_unit = bindings["item_unit"]
    derivation = GroundedDerivation(
        start=Quantity(
            value=bindings["loose_primary"],
            unit=item_unit,
            source_token=str(int(bindings["loose_primary"])),
        ),
        steps=(
            Step(
                op="add",
                operand=Quantity(
                    value=bindings["loose_friend"],
                    unit=item_unit,
                    source_token=str(int(bindings["loose_friend"])),
                ),
                cue="friend",
            ),
            Step(
                op="multiply",
                operand=Quantity(
                    value=bindings["num_boxes"],
                    unit="boxes",
                    source_token=_box_count_token(problem_text, bindings["num_boxes"]),
                ),
                cue=_box_count_token(problem_text, bindings["num_boxes"]),
            ),
            Step(
                op="divide",
                operand=Quantity(
                    value=boxed_total,
                    unit=item_unit,
                    source_token=str(int(bindings["total"])),
                ),
                cue="total",
                comparative=True,
            ),
        ),
    )
    return derivation, answer


def _self_verifies_box_capacity(
    derivation: GroundedDerivation, problem_text: str, expected: float
) -> SelfVerification:
    tokens = _tokens(problem_text)
    reasons: list[str] = []

    for q in [derivation.start, *(s.operand for s in derivation.steps if not s.comparative)]:
        if not _value_grounds(q.source_token, tokens):
            reasons.append(f"operand {q.source_token!r} not grounded in text")

    for step in derivation.steps:
        if not _token_in(step.cue, tokens):
            reasons.append(f"operation cue {step.cue!r} not grounded in text")

    bindings = _parse_bindings(problem_text)
    if bindings is None:
        reasons.append("missing box-capacity bindings")
    elif abs(_recompute_boxes_needed(bindings) - expected) > 1e-9:
        reasons.append("arithmetic mismatch on boxes needed")

    if abs(derivation.answer - expected) > 1e-9:
        reasons.append("derivation fold mismatch")

    obligation = Counter(q.source_token for q in extract_quantities(problem_text))
    used = Counter(
        [
            derivation.start.source_token,
            *(step.operand.source_token for step in derivation.steps),
        ]
    )
    unused = obligation - used
    if unused:
        reasons.append(f"incomplete: unused quantities {sorted(unused.keys())}")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_loose_crayon_box_capacity(problem_text: str) -> Resolution | None:
    """Gate the typed box-capacity chain through self-verification."""
    built = build_loose_crayon_box_capacity(problem_text)
    if built is None:
        return None
    derivation, answer = built
    if not _self_verifies_box_capacity(derivation, problem_text, answer).verified:
        return None
    return Resolution(
        answer=answer,
        answer_unit="boxes",
        derivation=derivation,
    )


def resolve_promotable_loose_crayon_box_capacity(
    problem_text: str,
) -> Resolution | None:
    """Serving promotion bridge (Gate A2s, ClusterContract loose_crayon_box)."""
    return compose_loose_crayon_box_capacity(problem_text)