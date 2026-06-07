"""Failure-family registry (N4) — the heart of the contemplation batch.

Partitions every typed organ refusal reason (R1 reader/admissibility, R2 reader/solver/
answer-choice) into a named **failure family** that declares:

- ``owner``                — which organ surfaces it (``r1`` / ``r2`` / ``cross``)
- ``must_remain_refused``  — is this a correct wrong=0 boundary that must stay refused?
- ``proposal_allowed``     — is this a genuine coverage gap a proposal may target?
- ``safe_next_action``     — the human-readable next step
- ``proposal_target``      — what artifact a proposal would suggest (e.g. ``r2_gold_fixture``)

Only three families are growth surfaces (``proposal_allowed = True``): the R2 ``missing_*``
gaps. Everything else is a correct boundary — `correct refusal != missing capability`. The
registry is a **partition**: every reachable reason maps to exactly one family (asserted by
test), so ``family_for_reason`` is total and unambiguous. ``answer_key_contradiction`` carries
no refusal reason — it is reached from the answer-choice ``contradiction`` *verdict* (N6).

Some R1 reasons are coarse (``unreadable_quantity_clause`` covers both the pronoun and distractor
cases; ``admissibility_refused`` covers both ungrounded and unit-incompatible). v0 folds each to a
single conservative family — the *action* (refuse, no proposal) is identical for the folded cases,
so no wrong=0 signal is lost. The reserved families are forward-declared for R3 with no current
reason mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from core.comprehension_attempt.model import ComprehensionAttempt

Owner = Literal["r1", "r2", "cross"]


@dataclass(frozen=True, slots=True)
class FailureFamily:
    """A named class of comprehension failure with its growth/refusal policy."""

    name: str
    owner: Owner
    must_remain_refused: bool
    proposal_allowed: bool
    safe_next_action: str
    proposal_target: str | None = None
    refusal_reasons: tuple[str, ...] = ()


#: The registry. Every reachable organ refusal reason appears in exactly one family.
REGISTRY: tuple[FailureFamily, ...] = (
    # --- correct wrong=0 boundaries (no proposal) ---------------------------------------- #
    FailureFamily(
        "input_shape", "cross", True, False,
        "refuse — the text is not a readable problem shape",
        refusal_reasons=(
            "empty", "no_quantity_template", "non_digit_quantity", "non_identifier_name",
            "unreadable_quantity_query", "invalid_binding_graph", "query_target_not_a_category",
            "unprojectable", "category_pair_not_found",
        ),
    ),
    FailureFamily(
        "unsupported_clause_shape", "r1", True, False,
        "refuse — compound/pronoun clause the template cannot isolate (subsumes "
        "ambiguous_referent + unsupported_distractor_clause until a finer signal exists)",
        refusal_reasons=("unreadable_quantity_clause",),
    ),
    FailureFamily(
        "ungrounded_base", "r1", True, False,
        "refuse — the asked quantity has no grounded anchor (underdetermined)",
        refusal_reasons=("no_single_quantity_query",),
    ),
    FailureFamily(
        "admissibility_incompatible", "cross", True, False,
        "refuse — operands are ungrounded or unit-incompatible (cannot combine across dimensions)",
        refusal_reasons=("admissibility_refused", "coefficient_unit_mismatch", "coefficient_conflict"),
    ),
    FailureFamily(
        "over_determined", "r1", True, False,
        "refuse — structurally incoherent (multiple bases / partition mismatch)",
        refusal_reasons=(
            "multiple_inverse_bases", "multiple_partitions",
            "partition_query_mismatch", "partition_container_mismatch",
        ),
    ),
    FailureFamily(
        "unsupported_system_size", "r2", True, False,
        "refuse — more than two categories; needs an n-variable solver (R3)",
        refusal_reasons=("too_many_categories",),
    ),
    FailureFamily(
        "indistinguishable_system", "r2", True, False,
        "refuse — the system is singular/underdetermined; no unique solution",
        refusal_reasons=("indistinguishable_weights", "query_target_unsolved", "verification_failed"),
    ),
    FailureFamily(
        "non_integer_solution", "r2", True, False,
        "refuse — no integer solution exists; never round",
        refusal_reasons=("non_integer_solution",),
    ),
    FailureFamily(
        "negative_solution", "r2", True, False,
        "refuse — a solved count is negative; out of domain",
        refusal_reasons=("negative_solution",),
    ),
    FailureFamily(
        "answer_choice_unresolved", "r2", True, False,
        "refuse — the proven value cannot be tied to exactly one option",
        refusal_reasons=(
            "no_matching_option", "ambiguous_options", "no_options",
            "unknown_provided_label", "unparseable_option",
        ),
    ),
    # --- growth surfaces (proposal allowed) ---------------------------------------------- #
    FailureFamily(
        "missing_total_count", "r2", False, True,
        "propose a total-count-constraint gold fixture for review",
        proposal_target="r2_gold_fixture", refusal_reasons=("missing_total_count",),
    ),
    FailureFamily(
        "missing_weighted_total", "r2", False, True,
        "propose a weighted-total-constraint gold fixture for review",
        proposal_target="r2_gold_fixture", refusal_reasons=("missing_weighted_total",),
    ),
    # --- verdict (not a refusal) --------------------------------------------------------- #
    FailureFamily(
        "answer_key_contradiction", "r2", False, False,
        "report the contradiction — the proven value disagrees with the supplied key",
        refusal_reasons=(),
    ),
    # --- reserved / forward-declared for R3 (no current emitter) ------------------------- #
    FailureFamily(
        "missing_category_pair", "r2", False, True,
        "RESERVED — propose a category-pair fixture once the reader distinguishes a partial "
        "(one-category) R2 problem from non-R2 text; the raw category_pair_not_found reason is "
        "too broad to propose against safely (it fires on any non-R2 text), so it maps to "
        "input_shape until that split exists",
        proposal_target="r2_gold_fixture",
    ),
    FailureFamily(
        "missing_attribute_coefficient", "r2", False, True,
        "RESERVED — propose an attribute-coefficient fixture (no emitter yet)",
        proposal_target="r2_gold_fixture",
    ),
    FailureFamily(
        "unsupported_rate_duration", "cross", True, False,
        "RESERVED — rate/duration frames are R3 (no emitter yet)",
    ),
    FailureFamily(
        "unsupported_temporal_state", "cross", True, False,
        "RESERVED — temporal-state frames are R3 (no emitter yet)",
    ),
)

_BY_NAME: dict[str, FailureFamily] = {f.name: f for f in REGISTRY}
_BY_REASON: dict[str, FailureFamily] = {
    reason: family for family in REGISTRY for reason in family.refusal_reasons
}

#: The verdict-derived family (no refusal reason maps to it).
ANSWER_KEY_CONTRADICTION = _BY_NAME["answer_key_contradiction"]


def family_for_reason(reason: str | None) -> FailureFamily | None:
    """The single failure family a typed organ refusal reason belongs to (or ``None``)."""
    if reason is None:
        return None
    return _BY_REASON.get(reason)


def family_by_name(name: str) -> FailureFamily | None:
    return _BY_NAME.get(name)


def enrich_family(attempt: ComprehensionAttempt) -> ComprehensionAttempt:
    """Return *attempt* with its ``family`` resolved from its refusal reason (or unchanged)."""
    family = family_for_reason(attempt.refusal_reason)
    if family is None:
        return attempt
    return replace(attempt, family=family.name)


__all__ = [
    "ANSWER_KEY_CONTRADICTION",
    "FailureFamily",
    "Owner",
    "REGISTRY",
    "enrich_family",
    "family_by_name",
    "family_for_reason",
]
