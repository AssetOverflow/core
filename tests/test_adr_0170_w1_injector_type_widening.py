"""ADR-0170 W1 — type widening pinning tests.

These tests pin the no-behavior-change widening of
``inject_from_match``'s return type. The contract becomes
``tuple[CandidateInitial | CandidateOperation, ...]`` so per-category
injectors can emit operations as well as initials. The existing
``inject_discrete_count_statement`` still emits only ``CandidateInitial``;
the widening is type-level only in this PR.

References:
- docs/decisions/ADR-0170-injector-contract-widening.md §"Implementation
  outline" W1 (this PR)
- docs/handoff/DCS-S1-FINDING.md — the investigation that surfaced the
  contract gap
- PR #369 (A2) — the schema-refusal that first observed the gap
"""

from __future__ import annotations

from typing import get_type_hints, Union, get_args, get_origin

import pytest

from generate.math_candidate_parser import CandidateInitial, CandidateOperation
from generate.recognizer_anchor_inject import (
    InjectorEmission,
    inject_from_match,
    inject_discrete_count_statement,
)


# ---------------------------------------------------------------------------
# Type-level contract
# ---------------------------------------------------------------------------


def test_injector_emission_union_includes_both_candidate_types():
    """``InjectorEmission`` is the union of ``CandidateInitial`` and
    ``CandidateOperation``. Future injector PRs can emit either."""
    args = get_args(InjectorEmission)
    assert CandidateInitial in args
    assert CandidateOperation in args
    # No third type smuggled in — the union is exactly two members.
    assert len(args) == 2


def test_inject_from_match_return_type_is_widened():
    """The dispatcher returns a tuple of ``InjectorEmission`` (not just
    ``CandidateInitial``). This pins the W1 widening; reverting to a
    narrower return type without an explicit ADR amendment fails this
    test."""
    hints = get_type_hints(inject_from_match)
    return_type = hints["return"]
    # tuple[InjectorEmission, ...]
    assert get_origin(return_type) is tuple
    inner = get_args(return_type)
    # tuple[X, ...] reports (X, Ellipsis)
    assert inner[-1] is Ellipsis
    inner_type = inner[0]
    # The element type is either InjectorEmission directly or its
    # Union[CandidateInitial, CandidateOperation] expansion.
    if get_origin(inner_type) is Union:
        members = set(get_args(inner_type))
        assert {CandidateInitial, CandidateOperation}.issubset(members)
    else:
        # Annotated alias case — resolve once.
        assert inner_type is InjectorEmission


# ---------------------------------------------------------------------------
# Behavioral pin — existing DCS injector unchanged
# ---------------------------------------------------------------------------


def test_discrete_count_injector_still_emits_only_candidate_initial():
    """W1 is type-level only. The existing
    ``inject_discrete_count_statement`` returns ``CandidateInitial`` —
    not ``CandidateOperation`` — at runtime. This is the byte-identical
    behavior guarantee for the W1 PR.

    Mechanically: pre-W1 the function returned
    ``tuple[CandidateInitial, ...]``. Post-W1 it still does. Subsequent
    PRs (W2 DCS-S1 acquisition, W3 currency, W4 multiplicative) widen
    the per-injector emission shapes; W1 ships only the dispatcher
    contract."""
    import inspect
    sig = inspect.signature(inject_discrete_count_statement)
    # With ``from __future__ import annotations`` the return annotation
    # is stored as a string. The W1 pin is that the existing DCS
    # injector's *narrower* return type is unchanged — only the
    # dispatcher (``inject_from_match``) widens.
    assert sig.return_annotation == "tuple[CandidateInitial, ...]"


# ---------------------------------------------------------------------------
# Behavioral pin — case 0050 hazard
# ---------------------------------------------------------------------------


def test_case_0050_remains_refused_post_widening():
    """The widening must not weaken the wrong=0 invariant. Case 0050
    refuses pre-W1 and must continue to refuse post-W1."""
    from generate.math_candidate_graph import parse_and_solve
    case_text = (
        "Mark does a gig every other day for 2 weeks.  "
        "For each gig, he plays 3 songs.  "
        "2 of the songs are 5 minutes long and the last song is twice that long.  "
        "How many minutes did he play?"
    )
    result = parse_and_solve(case_text)
    assert not result.is_admitted, (
        f"case 0050 admitted post-W1 — wrong=0 hazard re-introduced: "
        f"answer={result.answer!r} graph={result.selected_graph!r}"
    )


def test_unparseable_verb_still_refuses_post_widening():
    """The recognizer-no-injection refusal path (the #359 wrong=0 fix)
    is unchanged by the W1 widening. Unparseable verbs still produce
    explicit refusals, not silent admissions."""
    from generate.math_candidate_graph import parse_and_solve
    result = parse_and_solve(
        "Sam has 5 apples. Sam contemplates 3 apples. "
        "How many apples does Sam have?"
    )
    assert not result.is_admitted
    assert result.refusal_reason is not None


# ---------------------------------------------------------------------------
# Anti-regression: existing DCS path still admits
# ---------------------------------------------------------------------------


def test_existing_dcs_admission_path_unchanged():
    """A canonical narrow-form DCS sentence (proper noun + has + count
    + observed counted_noun) still admits via the existing injector.
    The widening must not regress the v1 admission path."""
    from generate.recognizer_match import _try_extract_discrete_count_anchor, _padded_lower
    from generate.math_candidate_graph import _load_ratified_registry_or_empty

    reg = _load_ratified_registry_or_empty()
    dcs_specs = [
        r.canonical_pattern for r in reg
        if r.shape_category.value == "discrete_count_statement"
    ]
    assert dcs_specs, "no ratified DCS recognizer on main"
    spec = dcs_specs[0]

    stmt = "Nicole has 400 Pokemon cards."
    padded = _padded_lower(stmt)
    anchor = _try_extract_discrete_count_anchor(stmt, padded, spec)
    assert anchor is not None, (
        "canonical DCS extraction regressed post-W1 — "
        f"'Nicole has 400 Pokemon cards.' should extract"
    )
    assert anchor["subject_role"] == "Nicole"
    assert anchor["count_token"] == "400"
    assert anchor["counted_noun"] == "Pokemon cards"
