"""Relational reader — binary-relation NL → pack-named structure, realized & determined.

The reader is the first consumer of ``en_core_relational_predicates_v1``: it maps
``<A> is [the] <connective> <B>`` onto the pack's closed predicate vocabulary, FAIL-CLOSED
(a non-template surface, a negated form, or a lemma absent from the loaded pack REFUSES).
Realize/determine consume it unchanged.

The pinned tests BITE (wrong=0):
  - the reader REFUSES a non-template surface and a negated form (no fabricated read);
  - the reader REFUSES when the mapped lemma is absent from the passed pack (fail-closed);
  - DETERMINE asserts ONLY on direct entailment — a present-but-non-entailing question
    and a symmetric CONVERSE both REFUSE (no faked symmetric/transitive inference);
  - DETERMINE keeps categorical predicates EXCLUDED (admitting them would be unsound).
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from generate.determine import Determined, Undetermined, determine
from generate.meaning_graph.reader import Comprehension, Refusal, comprehend
from generate.meaning_graph.relational import (
    RELATIONAL_PREDICATES,
    comprehend_relational,
    load_relational_pack_lemmas,
)
from generate.realize import Realized, realize_comprehension
from session.context import SessionContext

_HIGH_INTERVAL = 10**9
_PACK_LEMMAS = load_relational_pack_lemmas()


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)


def _read(text: str):
    return comprehend_relational(text, _PACK_LEMMAS)


def _tell(text: str, ctx: SessionContext):
    return realize_comprehension(_read(text), ctx)


def _ask(text: str, ctx: SessionContext):
    return determine(_read(text), ctx)


def _only_relation(text: str):
    comp = _read(text)
    assert isinstance(comp, Comprehension), comp
    assert len(comp.meaning_graph.relations) == 1 and not comp.queries
    return comp.meaning_graph.relations[0]


# --------------------------------------------------------------------------- #
# Reader: each relation family reads onto the right pack lemma
# --------------------------------------------------------------------------- #


def test_pack_lemmas_match_grammar() -> None:
    # The static grammar and the shipped pack agree — no grammar entry outruns the pack.
    assert RELATIONAL_PREDICATES == _PACK_LEMMAS


@pytest.mark.parametrize(
    "text,predicate,args",
    [
        ("Alice is the parent of Bob.", "parent_of", ("alice", "bob")),
        ("Bob is the child of Alice.", "child_of", ("bob", "alice")),
        ("Three is less than five.", "less_than", ("three", "five")),
        ("Nine is greater than two.", "greater_than", ("nine", "two")),
        ("Five is equal to five.", "equal_to", ("five", "five")),
        ("The box is left of the cup.", "left_of", ("box", "cup")),
        ("North station is adjacent to south station.", "adjacent_to",
         ("north_station", "south_station")),
        ("Monday is before Friday.", "before_event", ("monday", "friday")),
        ("Lunch is after breakfast.", "after_event", ("lunch", "breakfast")),
    ],
)
def test_relation_reads_onto_pack_lemma(text, predicate, args) -> None:
    rel = _only_relation(text)
    assert rel.predicate == predicate
    assert rel.arguments == args
    assert rel.negated is False


def test_oov_arguments_are_read() -> None:
    # Only the PREDICATE is closed-vocabulary; the arguments may be arbitrary (OOV).
    rel = _only_relation("Zorptak is the parent of Quxley.")
    assert rel.predicate == "parent_of"
    assert rel.arguments == ("zorptak", "quxley")


def test_question_form_reads_a_query_not_a_fact() -> None:
    comp = _read("Is Alice the parent of Bob?")
    assert isinstance(comp, Comprehension)
    assert not comp.meaning_graph.relations
    assert len(comp.queries) == 1
    q = comp.queries[0]
    assert q.predicate == "parent_of" and q.arguments == ("alice", "bob") and not q.negated


# --------------------------------------------------------------------------- #
# Reader: fail-closed — never guess (wrong=0 at the comprehension layer)
# --------------------------------------------------------------------------- #


def test_no_connective_refuses() -> None:
    res = _read("Alice greets Bob.")
    assert isinstance(res, Refusal) and res.reason == "no_relational_template"


def test_no_copula_refuses() -> None:
    res = _read("Alice parent of Bob.")
    assert isinstance(res, Refusal) and res.reason == "no_relational_template"


def test_negated_form_refuses() -> None:
    # "not" leaks into the subject slot -> reserved-word refusal; negation never reads
    # as a positive relation.
    res = _read("Alice is not the parent of Bob.")
    assert isinstance(res, Refusal)
    assert res.reason in {"reserved_word_in_np", "incomplete_relation"}


def test_incomplete_relation_refuses() -> None:
    res = _read("Alice is the parent of.")
    assert isinstance(res, Refusal) and res.reason == "incomplete_relation"


def test_fail_closed_on_pack_membership_bites() -> None:
    # The fail-closed gate: a grammar lemma absent from the PASSED pack must refuse,
    # even though the static grammar maps it. Break the pack -> the read must refuse.
    starved_pack = _PACK_LEMMAS - {"parent_of"}
    res = comprehend_relational("Alice is the parent of Bob.", starved_pack)
    assert isinstance(res, Refusal) and res.reason == "relational_lemma_not_in_pack"
    # a different relation still reads through the same starved pack (only parent_of gone)
    ok = comprehend_relational("Three is less than five.", starved_pack)
    assert isinstance(ok, Comprehension)


# --------------------------------------------------------------------------- #
# End-to-end: realize a relational fact, then determine it (as-told, never verified)
# --------------------------------------------------------------------------- #


def test_realize_then_determine_relation(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    told = _tell("Alice is the parent of Bob.", ctx)
    assert isinstance(told, Realized) and told.created
    res = _ask("Is Alice the parent of Bob?", ctx)
    assert isinstance(res, Determined)
    assert res.answer is True
    assert res.basis == "as_told"  # SPECULATIVE grounds — never "verified"
    assert res.predicate == "parent_of"
    assert res.subject == "alice" and res.object == "bob"


def test_distinct_relations_about_one_subject_stay_distinct(vocab_persona) -> None:
    # R1 relation-space recall: two facts about "alice" collide on the field versor but
    # are keyed apart structurally; each determines independently.
    ctx = _ctx(vocab_persona)
    _tell("Alice is the parent of Bob.", ctx)
    _tell("Alice is the sibling of Carol.", ctx)
    assert isinstance(_ask("Is Alice the parent of Bob?", ctx), Determined)
    assert isinstance(_ask("Is Alice the sibling of Carol?", ctx), Determined)


# --------------------------------------------------------------------------- #
# wrong=0 BITE — direct entailment only; no fabricated inference
# --------------------------------------------------------------------------- #


def test_present_but_non_entailing_refuses(vocab_persona) -> None:
    # A record about "alice" exists, but not the asked pair -> REFUSE, never assert.
    ctx = _ctx(vocab_persona)
    _tell("Alice is the parent of Bob.", ctx)
    res = _ask("Is Alice the parent of Carol?", ctx)
    assert isinstance(res, Undetermined) and res.reason == "not_entailed"


def test_symmetric_converse_is_not_faked(vocab_persona) -> None:
    # sibling_of is symmetric in the world, but D0 does DIRECT reading only: the stored
    # direction determines; the converse is a sound-but-incomplete refusal, NOT a faked
    # assertion. (If this flips to Determined, symmetric inference was smuggled in.)
    ctx = _ctx(vocab_persona)
    _tell("Alice is the sibling of Bob.", ctx)
    assert isinstance(_ask("Is Alice the sibling of Bob?", ctx), Determined)  # stored dir
    converse = _ask("Is Bob the sibling of Alice?", ctx)
    # The bite is that the converse does NOT assert. Its reason is "ungrounded" (no
    # sibling_of fact has "bob" as subject) rather than "not_entailed" — either way it
    # is a refusal, proving symmetric inference was not smuggled in.
    assert isinstance(converse, Undetermined)
    assert converse.reason in {"ungrounded", "not_entailed"}


def test_ungrounded_relation_refuses(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _ask("Is Alice the parent of Bob?", ctx)
    assert isinstance(res, Undetermined) and res.reason == "ungrounded"


def test_categorical_predicate_stays_excluded(vocab_persona) -> None:
    # DETERMINE must NOT admit categorical predicates (subset/disjoint/…): their truth
    # is not a stored-pair lookup, so a direct-entailment answer would be unsound.
    ctx = _ctx(vocab_persona)
    subset_q = comprehend("Are all men mortals?")
    assert isinstance(subset_q, Comprehension) and subset_q.queries[0].predicate == "subset"
    res = determine(subset_q, ctx)
    assert isinstance(res, Undetermined) and res.reason == "unsupported_query"
