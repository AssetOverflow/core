"""DETERMINE slice D0 — answer a membership question from realized structure, or refuse.

The pinned tests BITE: D0 asserts only on direct entailment by a realized fact and
carries ``basis="as_told"`` (never "verified", since realized facts are SPECULATIVE);
a present-but-non-entailing question (a record about the subject exists, but not the
asked relation) must REFUSE, and removing the grounding flips Determined→Undetermined.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from generate.determine import Determined, Undetermined, determine
from generate.meaning_graph.reader import comprehend
from generate.realize import realize_comprehension
from session.context import SessionContext

_HIGH_INTERVAL = 10**9


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)


def _tell(text: str, ctx: SessionContext):
    return realize_comprehension(comprehend(text), ctx)


def _ask(text: str, ctx: SessionContext):
    return determine(comprehend(text), ctx)


# --------------------------------------------------------------------------- #
# Refuse the ungrounded — never assert from absence (open-world, wrong=0)
# --------------------------------------------------------------------------- #


def test_ask_before_realizing_is_undetermined(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _ask("Is truth a concept?", ctx)
    assert isinstance(res, Undetermined) and res.reason == "ungrounded"


def test_non_question_is_undetermined(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Truth is a concept.", ctx)
    # a declarative (no query) is intake, not a question to determine
    assert isinstance(_ask("Truth is a concept.", ctx), Undetermined)
    # a Refusal question
    assert isinstance(determine(comprehend("The weather is nice today."), ctx), Undetermined)


# --------------------------------------------------------------------------- #
# Assert (as-told) on direct entailment by a realized fact
# --------------------------------------------------------------------------- #


def test_realized_fact_answers_its_own_question_as_told(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Truth is a concept.", ctx)
    res = _ask("Is truth a concept?", ctx)
    assert isinstance(res, Determined)
    assert res.answer is True
    assert res.basis == "as_told"  # SPECULATIVE -> as-told, NEVER "verified"
    assert res.predicate == "member" and res.subject == "truth" and res.object == "concept"
    assert len(res.grounds) == 1
    assert res.grounds[0].relation_arguments == ("truth", "concept")


def test_negated_query_is_refused(vocab_persona) -> None:
    # The reader refuses negated membership questions upstream, so determine() can
    # only meet a negated `member` query via a hand-built comprehension. D0 declines
    # it explicitly (ships no entailment path the reader cannot exercise).
    from generate.meaning_graph.model import MeaningGraph, MeaningSpan
    from generate.meaning_graph.reader import Comprehension, Query

    ctx = _ctx(vocab_persona)
    _tell("Truth is a concept.", ctx)  # positive member(truth, concept) realized
    span = MeaningSpan(source_id="input", start=0, end=5, text="dummy")
    negated = Comprehension(
        meaning_graph=MeaningGraph(),
        queries=(Query("member", ("truth", "concept"), span, negated=True),),
    )
    res = determine(negated, ctx)
    assert isinstance(res, Undetermined) and res.reason == "negated_query_unsupported"


# --------------------------------------------------------------------------- #
# Present-but-non-entailing — a record about the subject exists, but not the
# asked relation. MUST refuse (the discriminant bites: not "a record exists").
# --------------------------------------------------------------------------- #


def test_present_but_non_entailing_is_refused(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Truth is a concept.", ctx)  # member(truth, concept) realized
    res = _ask("Is truth a number?", ctx)  # member(truth, number) NOT realized
    assert isinstance(res, Undetermined) and res.reason == "not_entailed"


def test_other_subject_does_not_ground(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Knowledge is a concept.", ctx)
    # nothing realized about `truth` -> ungrounded, not a stray match on `concept`
    assert isinstance(_ask("Is truth a concept?", ctx), Undetermined)


# --------------------------------------------------------------------------- #
# Mutation bite — the verdict is entailment, not "a record exists"
# --------------------------------------------------------------------------- #


def test_verdict_is_entailment_not_mere_presence(vocab_persona) -> None:
    # With the grounding present -> Determined; the SAME question against a fresh
    # context with NO realized facts -> Undetermined. Proves the Determined verdict
    # is carried by the realized fact, not by the question alone.
    grounded = _ctx(vocab_persona)
    _tell("Truth is a concept.", grounded)
    assert isinstance(_ask("Is truth a concept?", grounded), Determined)

    empty = _ctx(vocab_persona)
    assert isinstance(_ask("Is truth a concept?", empty), Undetermined)


def test_unsupported_query_predicate_is_refused(vocab_persona) -> None:
    # A non-`member` query (e.g. subset/compare) is an honest refusal in D0 — built
    # by hand so the branch bites regardless of which predicates the reader emits.
    from generate.meaning_graph.model import MeaningGraph, MeaningSpan
    from generate.meaning_graph.reader import Comprehension, Query

    ctx = _ctx(vocab_persona)
    _tell("Truth is a concept.", ctx)
    span = MeaningSpan(source_id="input", start=0, end=5, text="dummy")
    subset_q = Comprehension(
        meaning_graph=MeaningGraph(),
        queries=(Query("subset", ("concept", "thought"), span),),
    )
    res = determine(subset_q, ctx)
    assert isinstance(res, Undetermined) and res.reason == "unsupported_query"


def test_multi_query_is_refused(vocab_persona) -> None:
    # A two-question input yields TWO queries (reachable from real input); D0 answers
    # one question at a time.
    ctx = _ctx(vocab_persona)
    _tell("Truth is a concept.", ctx)
    res = _ask("Is truth a concept? Is knowledge a thought?", ctx)
    assert isinstance(res, Undetermined) and res.reason == "not_single_query"


def test_malformed_member_query_is_refused(vocab_persona) -> None:
    # `member` is binary; a unary member query is malformed. Hand-built, since the
    # reader always emits arity-2 member queries — the guard would otherwise be
    # asserted-but-unproven.
    from generate.meaning_graph.model import MeaningGraph, MeaningSpan
    from generate.meaning_graph.reader import Comprehension, Query

    ctx = _ctx(vocab_persona)
    span = MeaningSpan(source_id="input", start=0, end=5, text="dummy")
    unary = Comprehension(
        meaning_graph=MeaningGraph(), queries=(Query("member", ("truth",), span),)
    )
    res = determine(unary, ctx)
    assert isinstance(res, Undetermined) and res.reason == "malformed_query"


def test_non_comprehension_input_is_refused(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = determine(object(), ctx)  # neither Comprehension nor Refusal
    assert isinstance(res, Undetermined) and res.reason == "not_a_comprehension"
