"""Phase 2 — reflective rendering via subject pronominalization.

The Phase 1 (commit ``63ffd88``) planner produces multi-clause plans
but the renderer walks moves in order without awareness of what was
just surfaced.  On a typical EXPLAIN/PARAGRAPH/compound output that
yields a mechanical-feeling cascade in which the subject lemma
repeats in every clause:

    Truth is what is true.
    Furthermore, truth belongs to cognition.truth.
    In turn, truth grounds knowledge.
    Truth belongs to epistemic.ground.
    Furthermore, truth belongs to logos.core.
    In turn, truth requires evidence.

Phase 2 wires the renderer with the **lightest possible interleaved
reflection**: track the most-recently-introduced subject (the
"focus") and, when the next move's subject is byte-equal to it,
emit a pronoun ("it") instead of repeating the lemma.  The
substitution rules:

* Same subject AND no topic shift (i.e. ``move.topic`` agrees with
  the prior focus) → swap to ``"it"``.
* Topic shift (TRANSITION move, or any move whose topic differs
  from prior focus) → reset focus, keep the explicit subject.
* Sentence-initial position (no connective): capitalise ``"It"``.
* Mid-sentence position (after connective + comma): lowercase ``"it"``.

This is deterministic, replayable, and adds nothing the bundle
didn't already contain — it is a pure rendering improvement.
"""

from __future__ import annotations

from generate.discourse_planner import (
    DiscourseMove,
    DiscourseMoveKind,
    DiscoursePlan,
    FactSource,
    GroundedFact,
    render_plan,
)
from generate.intent import DialogueIntent, IntentTag, ResponseMode


def _fact(subject: str, predicate: str, obj: str) -> GroundedFact:
    return GroundedFact(
        subject=subject,
        predicate=predicate,
        obj=obj,
        source=FactSource.PACK,
        source_id="test_pack_v1",
    )


def _intent(subject: str = "truth") -> DialogueIntent:
    return DialogueIntent(tag=IntentTag.DEFINITION, subject=subject)


def _move(
    kind: DiscourseMoveKind,
    fact: GroundedFact,
    *,
    given: tuple[str, ...] = (),
    new: tuple[str, ...] = (),
) -> DiscourseMove:
    return DiscourseMove(
        kind=kind,
        topic=fact.subject,
        given=given,
        new=new,
        relation_to_previous=None,
        fact=fact,
    )


# ---------------------------------------------------------------------------
# Pronominalization fires across consecutive same-subject moves
# ---------------------------------------------------------------------------


def test_reflective_replaces_repeated_subject_with_it() -> None:
    """Two moves with byte-equal subject → second clause uses ``it``."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.EXPLAIN,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
                new=("truth",),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
                given=("truth",),
                new=("cognition.truth",),
            ),
        ),
    )
    rendered = render_plan(plan, reflective=True)
    assert (
        rendered
        == "Truth is what is true. Furthermore, it belongs to cognition.truth."
    )


def test_reflective_handles_three_consecutive_same_subject_moves() -> None:
    """Three same-subject moves → first is canonical, next two are ``it``."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
                new=("truth",),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
            _move(
                DiscourseMoveKind.RELATION,
                _fact("truth", "grounds", "knowledge"),
            ),
        ),
    )
    rendered = render_plan(plan, reflective=True)
    assert rendered == (
        "Truth is what is true. "
        "Furthermore, it belongs to cognition.truth. "
        "In turn, it grounds knowledge."
    )


def test_reflective_capitalises_sentence_initial_pronoun() -> None:
    """When the next clause has no connective (e.g. CLOSURE), the
    pronoun must be sentence-initial and therefore capitalised."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.CLOSURE,
                _fact("truth", "belongs_to", "epistemic.ground"),
            ),
        ),
    )
    rendered = render_plan(plan, reflective=True)
    assert rendered == (
        "Truth is what is true. It belongs to epistemic.ground."
    )


def test_reflective_resets_focus_on_topic_shift() -> None:
    """When the next move's subject differs (topic shift), keep the
    explicit lemma — pronouns would be ambiguous."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.TRANSITION,
                _fact("knowledge", "belongs_to", "cognition.knowledge"),
            ),
            _move(
                DiscourseMoveKind.RELATION,
                _fact("knowledge", "grounds", "judgment"),
            ),
        ),
    )
    rendered = render_plan(plan, reflective=True)
    # After the TRANSITION shifts focus to ``knowledge``, the next
    # ``knowledge`` reference becomes ``it`` again.
    assert rendered == (
        "Truth is what is true. "
        "Consequently, knowledge belongs to cognition.knowledge. "
        "In turn, it grounds judgment."
    )


# ---------------------------------------------------------------------------
# Backward compatibility: reflective=False preserves Phase 1 output
# ---------------------------------------------------------------------------


def test_reflective_off_preserves_phase1_output() -> None:
    """``reflective=False`` reproduces the pre-Phase-2 byte-equivalent
    output — the default kept for any caller pinning the raw shape."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.EXPLAIN,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
        ),
    )
    rendered = render_plan(plan, reflective=False)
    assert rendered == (
        "Truth is what is true. "
        "Furthermore, truth belongs to cognition.truth."
    )


def test_reflective_default_is_off_for_back_compat() -> None:
    """``render_plan(plan)`` without an explicit kwarg keeps the
    Phase-1 default so existing call sites (and existing tests) are
    not silently rewritten.  The runtime wiring explicitly opts in."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.EXPLAIN,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
        ),
    )
    assert render_plan(plan) == render_plan(plan, reflective=False)


# ---------------------------------------------------------------------------
# Determinism: same input → same output, twice
# ---------------------------------------------------------------------------


def test_reflective_is_deterministic() -> None:
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.PARAGRAPH,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
            _move(
                DiscourseMoveKind.SUPPORT,
                _fact("truth", "belongs_to", "cognition.truth"),
            ),
            _move(
                DiscourseMoveKind.RELATION,
                _fact("truth", "grounds", "knowledge"),
            ),
        ),
    )
    a = render_plan(plan, reflective=True)
    b = render_plan(plan, reflective=True)
    assert a == b


# ---------------------------------------------------------------------------
# Single-move plans are byte-identical regardless of reflective mode
# (no second move ⇒ no pronoun substitution possible)
# ---------------------------------------------------------------------------


def test_reflective_single_move_byte_identical_to_non_reflective() -> None:
    """A BRIEF/single-move plan can't trigger pronominalization — the
    output must be byte-identical to ``reflective=False``.  This is
    the load-bearing claim that lets the cognition eval (mostly
    single-fact prompts) stay byte-equal across the Phase 2 flip."""
    plan = DiscoursePlan(
        intent=_intent(),
        mode=ResponseMode.BRIEF,
        moves=(
            _move(
                DiscourseMoveKind.ANCHOR,
                _fact("truth", "is_defined_as", "what is true"),
            ),
        ),
    )
    assert render_plan(plan, reflective=True) == render_plan(
        plan, reflective=False
    )
