"""ADR-0170 W2 — DCS-S1 acquisition verbs: first ``CandidateOperation``
emission from the recognizer-injector path.

W2 proves the W1 contract widening with concrete real-emission code:
the DCS injector now dispatches on the matcher's recorded
``anchor_kind`` and emits ``CandidateOperation(add)`` for acquisition
verbs (collected / received / bought / got) instead of
``CandidateInitial``.

This preserves ADR-0131.G.1's branch-disagreement discipline:
acquisition verbs route to operations, not initials, so the regex
parser's ADD_VERBS path and the injector's CandidateOperation path
emit compatible kinds for the same sentence (collapsed-tie OK).

Hard invariants:

- ``wrong == 0`` — verify against case 0050 hazard
- The acquisition path emits only ``CandidateOperation(add)``,
  matching ADR-0131.G.1
- Verbs deliberately excluded (gained, donated, saved) still refuse
"""

from __future__ import annotations

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.math_candidate_parser import CandidateInitial, CandidateOperation
from generate.math_problem_graph import Operation, Quantity
from generate.recognizer_anchor_inject import (
    _build_operation_from_discrete_count_acquisition,
    inject_discrete_count_statement,
    inject_from_match,
)
from generate.recognizer_match import (
    _ACQUISITION_VERBS,
    _POSSESSION_VERBS,
    _try_extract_discrete_count_anchor,
    _padded_lower,
)
from generate.math_candidate_graph import _load_ratified_registry_or_empty


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dcs_spec():
    reg = _load_ratified_registry_or_empty()
    for r in reg:
        if r.shape_category.value == "discrete_count_statement":
            return r.canonical_pattern
    raise RuntimeError("no ratified discrete_count_statement spec on main")


def _extract(stmt: str):
    return _try_extract_discrete_count_anchor(stmt, _padded_lower(stmt), _dcs_spec())


def _make_match(parsed_anchors):
    from generate.recognizer_registry import RatifiedRecognizer
    from generate.recognizer_match import RecognizerMatch

    rec = RatifiedRecognizer(
        proposal_id="test-w2",
        shape_category=ShapeCategory.DISCRETE_COUNT_STATEMENT,
        canonical_pattern=dict(_dcs_spec()),
        spec_digest="test-digest",
        review_date="2026-05-27",
        ratified_at_revision="test",
    )
    return RecognizerMatch(
        recognizer=rec,
        category=ShapeCategory.DISCRETE_COUNT_STATEMENT,
        outcome="admissible",
        graph_intent="count",
        parsed_anchors=parsed_anchors,
    )


# ---------------------------------------------------------------------------
# Verb-set membership pins
# ---------------------------------------------------------------------------


def test_acquisition_verbs_set_contains_expected_verbs():
    expected = {"collected", "collects", "collect",
                "received", "receives", "receive",
                "bought", "buys", "buy",
                "got", "gets", "get"}
    assert _ACQUISITION_VERBS == frozenset(expected)


def test_possession_verbs_set_unchanged():
    # Pre-W2 set preserved.
    assert _POSSESSION_VERBS == frozenset({"has", "have", "had"})


def test_acquisition_and_possession_sets_disjoint():
    assert _ACQUISITION_VERBS.isdisjoint(_POSSESSION_VERBS)


def test_acquisition_verbs_subset_of_add_verbs():
    # Every acquisition verb must be in ADD_VERBS so the downstream
    # CandidateOperation post-init whitelist accepts the matched_verb
    # token.
    from generate.math_roundtrip import ADD_VERBS
    assert _ACQUISITION_VERBS.issubset(ADD_VERBS)


# ---------------------------------------------------------------------------
# Extractor — anchor_kind discrimination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "verb,canonical",
    [
        ("collected", "collected"),
        ("received", "received"),
        ("bought", "bought"),
        ("got", "got"),
    ],
)
def test_extractor_records_acquisition_anchor_kind(verb: str, canonical: str):
    anchor = _extract(f"Nicole {verb} 400 paperclips.")
    assert anchor is not None
    assert anchor["anchor_kind"] == "acquisition"
    assert anchor["verb_token"] == canonical


def test_extractor_records_possession_anchor_kind():
    anchor = _extract("Nicole has 400 paperclips.")
    assert anchor is not None
    assert anchor["anchor_kind"] == "possession"
    assert anchor["verb_token"] == "has"


# ---------------------------------------------------------------------------
# Injector — emits CandidateOperation for acquisition
# ---------------------------------------------------------------------------


def test_acquisition_anchor_produces_candidate_operation_add():
    anchor = _extract("Nicole collected 400 paperclips.")
    assert anchor is not None
    match = _make_match((anchor,))
    out = inject_discrete_count_statement(match, "Nicole collected 400 paperclips.")
    assert len(out) == 1
    cand = out[0]
    assert isinstance(cand, CandidateOperation), (
        f"acquisition anchor must emit CandidateOperation, got {type(cand).__name__}"
    )
    assert cand.op.kind == "add"
    assert cand.op.actor == "Nicole"
    assert cand.op.operand.value == 400
    assert cand.op.operand.unit == "paperclips"
    assert cand.matched_verb == "collected"


def test_possession_anchor_still_produces_candidate_initial():
    """Pre-W2 behavior preserved: possession anchors still emit
    CandidateInitial, not CandidateOperation."""
    anchor = _extract("Nicole has 400 paperclips.")
    assert anchor is not None
    match = _make_match((anchor,))
    out = inject_discrete_count_statement(match, "Nicole has 400 paperclips.")
    assert len(out) == 1
    cand = out[0]
    assert isinstance(cand, CandidateInitial)
    assert cand.matched_anchor == "has"


@pytest.mark.parametrize("verb", ["collected", "received", "bought", "got"])
def test_all_acquisition_verbs_emit_candidate_operation(verb: str):
    anchor = _extract(f"Sam {verb} 5 apples.")
    assert anchor is not None
    match = _make_match((anchor,))
    out = inject_discrete_count_statement(match, f"Sam {verb} 5 apples.")
    assert len(out) == 1
    cand = out[0]
    assert isinstance(cand, CandidateOperation)
    assert cand.op.kind == "add"
    assert cand.matched_verb == verb


# ---------------------------------------------------------------------------
# Deliberate exclusions — verbs that must still refuse
# ---------------------------------------------------------------------------


def test_gained_still_refused_delta_of_attribute_hazard():
    """``gained`` is delta-of-attribute (weight, age), not acquisition;
    admitting it as add-operation would risk wrong>0 on questions
    that ask total state. Deliberately excluded from
    _ACQUISITION_VERBS."""
    assert _extract("Orlando gained 5 pounds.") is None


def test_donated_still_refused_subtract_verb():
    """``donated`` is a SUBTRACT verb (actor gives away). Future W2.1
    PR may add depletion-verb handling; for now, refuses."""
    assert _extract("Alice donated 3 books.") is None


def test_saved_still_refused_ambiguous():
    """``saved`` is ambiguous between time/money/effort. Deliberately
    excluded from _ACQUISITION_VERBS until disambiguation lands."""
    assert _extract("Bob saved 50 apples.") is None


# ---------------------------------------------------------------------------
# Case 0050 hazard pin — wrong=0 safety net
# ---------------------------------------------------------------------------


def test_case_0050_hazard_unaffected_by_w2():
    """Case gsm8k-train-sample-v1-0050 must remain refused at
    sentence_index=0. The acquisition-verb extension does not affect
    the case 0050 sentence ``Mark does a gig every other day for 2
    weeks.`` — ``does`` is not in _POSSESSION_VERBS or
    _ACQUISITION_VERBS, so the DCS extractor refuses."""
    from generate.math_candidate_graph import parse_and_solve
    case_text = (
        "Mark does a gig every other day for 2 weeks.  "
        "For each gig, he plays 3 songs.  "
        "2 of the songs are 5 minutes long and the last song is twice that long.  "
        "How many minutes did he play?"
    )
    result = parse_and_solve(case_text)
    assert not result.is_admitted, (
        f"case 0050 admitted post-W2: answer={result.answer!r} "
        f"graph={result.selected_graph!r}"
    )


# ---------------------------------------------------------------------------
# Determinism + wrong=0 invariant
# ---------------------------------------------------------------------------


def test_w2_emission_deterministic_across_reruns():
    """Same anchor → byte-identical CandidateOperation. The new
    acquisition path inherits the determinism contract."""
    anchor = _extract("Nicole collected 400 paperclips.")
    match = _make_match((anchor,))
    out1 = inject_discrete_count_statement(match, "Nicole collected 400 paperclips.")
    out2 = inject_discrete_count_statement(match, "Nicole collected 400 paperclips.")
    assert out1 == out2


def test_w2_admission_path_passes_roundtrip_admissible():
    """The injected CandidateOperation must pass
    ``roundtrip_admissible`` — the existing wrong=0 safety net for
    operations. This is the layer-3 check in ADR-0163.D.2's
    five-layer net, now extended to the acquisition path."""
    from generate.math_roundtrip import roundtrip_admissible
    anchor = _extract("Nicole collected 400 paperclips.")
    match = _make_match((anchor,))
    out = inject_discrete_count_statement(match, "Nicole collected 400 paperclips.")
    assert len(out) == 1
    assert roundtrip_admissible(out[0])


# ---------------------------------------------------------------------------
# Dispatcher pin
# ---------------------------------------------------------------------------


def test_inject_from_match_dispatches_to_acquisition_path():
    """The W1 dispatcher routes through to the W2 acquisition path
    via the type-widened return contract."""
    anchor = _extract("Sam bought 5 apples.")
    match = _make_match((anchor,))
    out = inject_from_match(match, "Sam bought 5 apples.")
    assert len(out) == 1
    assert isinstance(out[0], CandidateOperation)
    assert out[0].op.kind == "add"
