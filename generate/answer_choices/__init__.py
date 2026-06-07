"""Multiple-choice answer verification (off-serving).

Ties a PROVEN value to exactly one labeled option and flags answer-key contradictions — the
engine asserts the consistent answer and names a wrong key, never silently accepting it. Used
by the R2 constraint organ (and reusable by any lane that proves an integer answer). Imports no
``generate.derivation`` / ``core.reliability_gate``.
"""

from __future__ import annotations

from generate.answer_choices.parse import parse_option_value, parse_options
from generate.answer_choices.verify import (
    ChoiceVerdict,
    VERDICT_STATUSES,
    verify_answer_choice,
)

__all__ = [
    "ChoiceVerdict",
    "VERDICT_STATUSES",
    "parse_option_value",
    "parse_options",
    "verify_answer_choice",
]
