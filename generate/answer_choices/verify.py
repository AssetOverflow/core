"""Verify a computed answer against multiple-choice options, flagging key contradictions (R2 C4).

Truth discipline (the user's Phase 5): the engine ties its PROVEN value to exactly one labeled
option. If a provided answer key disagrees with the proof, that is not a refusal — it is a
confident **contradiction** verdict ("the math says A; the key says C — the key is wrong"). The
verifier refuses only when the proof cannot be tied to exactly one option (no match, or a
duplicate-valued match). Off-serving; deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from generate.answer_choices.parse import parse_options
from generate.meaning_graph.reader import Refusal

#: A confident verdict status — NOT a refusal. ``contradiction`` asserts the key is wrong while
#: the engine's value stands; ``consistent`` confirms (or, with no key, simply labels) it.
VERDICT_STATUSES = frozenset({"consistent", "contradiction"})


@dataclass(frozen=True, slots=True)
class ChoiceVerdict:
    """The outcome of tying a proven value to the options. ``computed_label`` is the option the
    proof matches; ``provided_label`` is the supplied key (or ``None``); ``message`` is the
    user-facing sentence."""

    computed_value: int
    computed_label: str
    provided_label: str | None
    status: str
    message: str


def _suffix(noun: str) -> str:
    return f" {noun}" if noun else ""


def verify_answer_choice(
    computed_value: int, options: Any, provided_label: str | None = None, *, noun: str = ""
) -> ChoiceVerdict | Refusal:
    """Match the solver's proven value to the options; confirm or contradict a provided key.

    Returns a :class:`ChoiceVerdict` (``consistent`` / ``contradiction``) when the value ties to
    exactly one option, else a typed :class:`Refusal` (``no_options`` / ``unparseable_option`` /
    ``no_matching_option`` / ``ambiguous_options`` / ``unknown_provided_label``).
    """
    parsed = parse_options(options)
    if isinstance(parsed, Refusal):
        return parsed
    matches = sorted(label for label, value in parsed.items() if value == computed_value)
    if not matches:
        return Refusal("no_matching_option", f"no option equals {computed_value}")
    if len(matches) > 1:
        return Refusal("ambiguous_options", f"{matches} all equal {computed_value}")

    computed_label = matches[0]
    suffix = _suffix(noun)
    if provided_label is None or provided_label == computed_label:
        return ChoiceVerdict(
            computed_value,
            computed_label,
            provided_label,
            "consistent",
            f"The mathematically consistent answer is {computed_label}. {computed_value}{suffix}.",
        )
    if provided_label not in parsed:
        return Refusal("unknown_provided_label", str(provided_label))
    return ChoiceVerdict(
        computed_value,
        computed_label,
        provided_label,
        "contradiction",
        f"The mathematically consistent answer is {computed_label} ({computed_value}{suffix}). "
        f"The supplied answer key says {provided_label} ({parsed[provided_label]}{suffix}), "
        f"which contradicts the equations.",
    )


__all__ = ["ChoiceVerdict", "VERDICT_STATUSES", "verify_answer_choice"]
