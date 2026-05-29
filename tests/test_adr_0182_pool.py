"""ADR-0182 — cross-composer disagreement pooling (distractor refusal).

Two surfaces under test:

* :func:`generate.derivation.verify.classify_derivation` — the commit-eligibility
  class (``complete`` / ``exempt`` / ``None``) and, critically, that the
  isolated-foreign exemption is *narrow* (an empty-unit or same-unit unused
  quantity is never exempt — it is real signal, not a distractor).
* :func:`generate.derivation.pool.resolve_pooled` — the pooled resolution: a clean
  reading commits, a distractor problem's product-vs-additive disagreement refuses,
  and (the wrong=0-critical property) an ``exempt``-only answer **never commits**.

Sealed lane: ``chat/`` does not import these; serving ``3/47/0`` cannot move.
"""

from __future__ import annotations

from generate.derivation import pool
from generate.derivation.accumulate import accumulation_candidates
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.pool import resolve_pooled
from generate.derivation.target import asks_prior_state
from generate.derivation.verify import classify_derivation

_DISTRACTOR_0014 = (
    "Kate has 20 pencils. She studies for 3 hours and then buys 5 more pencils. "
    "How many pencils does Kate have?"
)
# A distractor whose pool contains an exempt additive reading (20+5=25, "3 hours"
# unused) AND a complete product (20*3*5=300) — three distinct answers, so refusal
# here comes from the DISAGREEMENT rule, not commit-ineligibility. (The aggressive
# composers manufacture the product from any such text, which is exactly why a
# natural fixture cannot isolate the commit-ineligibility branch — see
# test_exempt_only_never_commits, which injects a single-exempt pool directly.)
_EXEMPT_PLUS_PRODUCT = (
    "Kate has 20 pencils. She rests for 3 hours and buys 5 more pencils."
)
_CLEAN_ACCUMULATION = "Sam has 14 apples. He buys 9 more apples."


class TestClassifyDerivation:
    def test_complete_reading_is_commit_eligible(self) -> None:
        # uses every quantity -> complete
        derivation = accumulation_candidates(_CLEAN_ACCUMULATION)[0]
        assert classify_derivation(derivation, _CLEAN_ACCUMULATION) == "complete"

    def test_isolated_foreign_unused_is_exempt(self) -> None:
        # the additive reading of 0014 leaves "3 hours" unused; hours is foreign to
        # the used unit (pencils) -> exempt (commit-ineligible).
        derivation = GroundedDerivation(
            start=Quantity(20.0, "pencils", "20"),
            steps=(Step(op="add", operand=Quantity(5.0, "pencils", "5"), cue="more"),),
        )
        assert classify_derivation(derivation, _DISTRACTOR_0014) == "exempt"

    def test_same_unit_unused_is_not_exempt(self) -> None:
        # a quantity sharing the reading's unit is real signal, never a distractor:
        # leaving it unused must NOT be exempted (it stays invalid -> None).
        text = "Sam has 14 apples. He buys 9 more apples. He eats 2 apples."
        derivation = GroundedDerivation(
            start=Quantity(14.0, "apples", "14"),
            steps=(Step(op="add", operand=Quantity(9.0, "apples", "9"), cue="more"),),
        )
        assert classify_derivation(derivation, text) is None

    def test_empty_unit_unused_is_not_exempt(self) -> None:
        # an unused quantity with an unknown (empty) unit cannot be shown foreign,
        # so it is never exempt — completeness still rejects the reading.
        text = "Sam has 14 apples. He buys 9 more apples. He had 2."
        derivation = GroundedDerivation(
            start=Quantity(14.0, "apples", "14"),
            steps=(Step(op="add", operand=Quantity(9.0, "apples", "9"), cue="more"),),
        )
        assert classify_derivation(derivation, text) is None

    def test_ungrounded_operand_is_invalid(self) -> None:
        derivation = GroundedDerivation(
            start=Quantity(14.0, "apples", "14"),
            steps=(Step(op="add", operand=Quantity(999.0, "apples", "999"), cue="more"),),
        )
        assert classify_derivation(derivation, _CLEAN_ACCUMULATION) is None


class TestResolvePooled:
    def test_clean_accumulation_commits(self) -> None:
        resolution = resolve_pooled(_CLEAN_ACCUMULATION)
        assert resolution is not None
        assert resolution.answer == 23.0

    def test_distractor_0014_refuses_via_disagreement(self) -> None:
        # product 300 (complete) vs additive 25 (exempt) disagree -> refuse.
        assert resolve_pooled(_DISTRACTOR_0014) is None

    def test_extra_exempt_readings_do_not_break_refusal(self) -> None:
        # A pool carrying an exempt additive reading alongside the complete product
        # still refuses (three distinct answers -> disagreement). Guards that the
        # exempt class does not accidentally suppress the disagreement rule.
        assert accumulation_candidates(_EXEMPT_PLUS_PRODUCT), "expected a candidate"
        assert classify_derivation(
            accumulation_candidates(_EXEMPT_PLUS_PRODUCT)[-1], _EXEMPT_PLUS_PRODUCT
        ) == "exempt"
        assert resolve_pooled(_EXEMPT_PLUS_PRODUCT) is None

    def test_exempt_only_never_commits(self, monkeypatch) -> None:
        # THE wrong=0-critical obligation, isolated. A pool whose ONLY verifying
        # reading is exempt — a single distinct answer with no `complete` reading —
        # must refuse on commit-ineligibility (pool.resolve_pooled requires a
        # `complete` candidate to commit; an exempt-only answer never commits).
        #
        # The aggressive composers synthesise a competing `complete` product for any
        # natural text (see test_extra_exempt_readings_do_not_break_refusal), so a
        # corpus fixture cannot isolate this branch. We inject a single-exempt pool
        # directly. Removing the commit-ineligibility clause makes this commit 25 and
        # fails loudly; it is otherwise unguarded.
        exempt = GroundedDerivation(
            start=Quantity(20.0, "pencils", "20"),
            steps=(Step(op="add", operand=Quantity(5.0, "pencils", "5"), cue="more"),),
        )
        assert classify_derivation(exempt, _DISTRACTOR_0014) == "exempt"
        monkeypatch.setattr(pool, "pooled_candidates", lambda *_a: [exempt])
        # one distinct answer (25), zero `complete` readings -> commit-ineligibility
        # is the only clause that can refuse here.
        assert resolve_pooled(_DISTRACTOR_0014) is None

    def test_deterministic(self) -> None:
        assert resolve_pooled(_DISTRACTOR_0014) == resolve_pooled(_DISTRACTOR_0014)
        a = resolve_pooled(_CLEAN_ACCUMULATION)
        b = resolve_pooled(_CLEAN_ACCUMULATION)
        assert a is not None and b is not None and a.answer == b.answer


_BEFORE_Q = "Lisa had 50 dollars. She spent 20 on lunch. How much money did Lisa have before lunch?"
_LEFT_TWIN = "Lisa had 50 dollars. She spent 20 on lunch. How much money does Lisa have left?"


class TestPriorStateQuestionGuard:
    """ADR-0182 — a question asking for a *prior* state is refused (the forward
    composers compute the final state, the wrong temporal point). Question-clause
    scoped, so body narrative ('before school starts') does not trip it."""

    def test_before_question_detected(self) -> None:
        assert asks_prior_state(_BEFORE_Q) is True

    def test_left_twin_not_detected(self) -> None:
        # the minimal-pair twin asks for the net ('left') -> forward reading, solvable.
        assert asks_prior_state(_LEFT_TWIN) is False

    def test_before_in_body_not_detected(self) -> None:
        # 'before' in narrative (not the question clause) must NOT trip the guard,
        # or it would wrongly refuse train-0003 (gold 864, currently committed).
        body_before = (
            "The student council sells erasers in the morning before school starts. "
            "There are 24 erasers in each box. If they sell 48 boxes, how many erasers?"
        )
        assert asks_prior_state(body_before) is False

    def test_used_to_make_is_not_a_prior_marker(self) -> None:
        # the purpose infinitive 'used to make' is a false positive guarded against.
        assert asks_prior_state("If 50 beads are used to make one bracelet, how many bracelets?") is False

    def test_prior_state_question_refuses(self) -> None:
        # the forward reading computes 50-20=30 (the net); the question asks the
        # pre-change state -> refuse, not commit 30.
        assert resolve_pooled(_BEFORE_Q) is None

    def test_left_twin_still_resolves_forward(self) -> None:
        # discrimination: the twin asking 'left' commits the forward net (30).
        resolution = resolve_pooled(_LEFT_TWIN)
        assert resolution is not None and resolution.answer == 30.0


_ANCHOR_SKIP_0016 = (
    "A train travels at 60 miles per hour for 2 hours. Tom has 8 tickets and "
    "buys 4 more tickets. How many tickets does Tom have?"
)
_INTRACLAUSE_TWIN = "Tom has 8 tickets and buys 4 more tickets. How many tickets does Tom have?"


class TestAnchorSkipIntraClause:
    """ADR-0182 anchor-skip: a sentence packing state+change ("Tom has 8 tickets and
    buys 4 more tickets") is read by splitting on the conjunction, and a leading
    all-foreign block ("A train travels 60 miles ... for 2 hours") is skipped from
    anchor selection. Its quantities go unused -> the pool's isolated-foreign
    exemption makes the reading commit-ineligible -> it forces a disagreement refusal
    on the distractor case, while the clean twin commits."""

    def test_intra_clause_state_and_change_resolves(self) -> None:
        # the clean twin: "has 8 ... and buys 4 more" -> 12, committed.
        resolution = resolve_pooled(_INTRACLAUSE_TWIN)
        assert resolution is not None and resolution.answer == 12.0

    def test_anchor_skip_candidate_is_exempt(self) -> None:
        # the 0016 reading skips the train block; 8+4=12 leaves 60/2 unused-foreign.
        cands = accumulation_candidates(_ANCHOR_SKIP_0016)
        assert cands, "expected an anchor-skip accumulation candidate"
        twelve = [d for d in cands if d.answer == 12.0]
        assert twelve, "expected the 8+4=12 reading"
        assert classify_derivation(twelve[0], _ANCHOR_SKIP_0016) == "exempt"

    def test_distractor_0016_refuses_via_disagreement(self) -> None:
        # product 3840 (complete) vs additive 12 (exempt) disagree -> refuse.
        assert resolve_pooled(_ANCHOR_SKIP_0016) is None

    def test_no_anchor_skip_candidate_without_conjunction(self) -> None:
        # a plain single-quantity sentence yields no spurious extra reading.
        cands = accumulation_candidates("Sam has 14 apples. He buys 9 more apples.")
        assert all(d.answer == 23.0 for d in cands)
