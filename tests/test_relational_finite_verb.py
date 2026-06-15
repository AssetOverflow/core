"""Relational reader — the closed finite-verb surface (B3): ``overlaps_event``.

The reader admits ONE finite verb with NO copula: ``<A> overlaps <B>`` (declarative) and
``Does <A> overlap <B>?`` (query). Everything else still requires the copula. Fail-closed:
an adverb-modified overlap, a coordinated/leftover slot, a second verb, a negation, a
non-table verb, or a bare connective-without-copula all REFUSE.

Two adversarial-audit hazards are pinned here:
  1. adverb absorption — ``A nearly overlaps B`` must NOT fabricate the entity ``a_nearly``;
  2. copula bypass — admitting the finite verb must NOT let the OTHER connectives drop the
     copula: ``Monday before Friday.`` must still refuse.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from generate.determine import Determined, Undetermined, determine
from generate.meaning_graph.reader import Comprehension, Refusal
from generate.meaning_graph.relational import (
    comprehend_relational,
    load_relational_pack_lemmas,
)
from generate.realize import NotRealized, realize_comprehension
from session.context import SessionContext

_HIGH = 10**9
_PACK = load_relational_pack_lemmas()


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH)


def _read(text: str):
    return comprehend_relational(text, _PACK)


# --------------------------------------------------------------------------- #
# Positives — the finite-verb declarative + interrogative read overlaps_event
# --------------------------------------------------------------------------- #


def test_declarative_overlaps_reads() -> None:
    comp = _read("Sunrise overlaps dawn.")
    assert isinstance(comp, Comprehension), comp
    assert not comp.queries and len(comp.meaning_graph.relations) == 1
    rel = comp.meaning_graph.relations[0]
    assert rel.predicate == "overlaps_event"
    assert rel.arguments == ("sunrise", "dawn")
    assert rel.negated is False


def test_interrogative_does_overlap_reads_a_query() -> None:
    comp = _read("Does Sunrise overlap dawn?")
    assert isinstance(comp, Comprehension), comp
    assert not comp.meaning_graph.relations and len(comp.queries) == 1
    q = comp.queries[0]
    assert q.predicate == "overlaps_event" and q.arguments == ("sunrise", "dawn")
    assert not q.negated


def test_oov_arguments_in_finite_verb_surface() -> None:
    rel = _read("Zorptak overlaps Quxley.").meaning_graph.relations[0]
    assert rel.predicate == "overlaps_event" and rel.arguments == ("zorptak", "quxley")


def test_read_then_determine_direct_and_symmetric(vocab_persona) -> None:
    # the finite-verb read integrates with determine: direct, and the symmetric converse
    # (overlaps_event is pack-declared symmetric) determines via the one-hop rule.
    ctx = _ctx(vocab_persona)
    realize_comprehension(_read("Sunrise overlaps dawn."), ctx)
    direct = determine(_read("Does Sunrise overlap dawn?"), ctx)
    assert isinstance(direct, Determined) and direct.answer is True and direct.rule == "direct"
    converse = determine(_read("Does dawn overlap Sunrise?"), ctx)
    assert isinstance(converse, Determined) and converse.answer is True
    assert converse.rule == "symmetric"


# --------------------------------------------------------------------------- #
# Hazard 1 (pinned) — adverb absorption must NOT fabricate an entity
# --------------------------------------------------------------------------- #


def test_adverb_modified_overlap_refuses_no_fabrication(vocab_persona) -> None:
    res = _read("Alice nearly overlaps Bob.")
    assert isinstance(res, Refusal) and res.reason == "finite_verb_modifier"
    # and nothing fabricated is realized — no `alice_nearly` enters memory.
    ctx = _ctx(vocab_persona)
    told = realize_comprehension(_read("Alice nearly overlaps Bob."), ctx)
    assert isinstance(told, NotRealized)
    assert isinstance(determine(_read("Does alice_nearly overlap Bob?"), ctx), Undetermined)


# --------------------------------------------------------------------------- #
# Hazard 2 (pinned) — the finite verb must NOT let other connectives bypass copula
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    [
        "Monday before Friday.",
        "The cat inside the house.",
        "The room adjacent the hall.",
    ],
)
def test_connective_without_copula_still_refuses(text) -> None:
    res = _read(text)
    assert isinstance(res, Refusal) and res.reason == "no_relational_template"


# --------------------------------------------------------------------------- #
# Mandatory confusers — every malformed finite-verb / non-finite-verb surface refuses
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    [
        "Alice overlaps with the team and Bob.",  # coordinated/leftover structure
        "A overlaps B and C.",  # coordination
        "A nearly overlaps B.",  # adverb
        "A completely overlaps B.",  # adverb
        "Does A nearly overlap B?",  # adverb in the query
        "A does not overlap B.",  # negation
        "A borders B.",  # finite verb not in the closed table
        "A overlaps B overlaps C.",  # a second finite verb
        "A overlaps B then C.",  # sequencing modifier
    ],
)
def test_finite_verb_confusers_refuse(text) -> None:
    res = _read(text)
    assert isinstance(res, Refusal), f"{text!r} should refuse but committed {res!r}"


def test_no_finite_verb_confuser_fabricates_a_relation() -> None:
    # stronger than "is a Refusal": not a single relation/query is produced for any of them.
    for text in (
        "Alice overlaps with the team and Bob.",
        "A nearly overlaps B.",
        "A overlaps B overlaps C.",
        "A overlaps B then C.",
        "A does not overlap B.",
    ):
        comp = _read(text)
        assert isinstance(comp, Refusal), text


# --------------------------------------------------------------------------- #
# Slot-fabrication hazards (adversarial audit) — the single-token slot gate closes
# the UNBOUNDED adverb / negation / qualifier / second-verb class a blocklist cannot.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    [
        "Alice almost overlaps Bob.",  # adverb NOT in the enumerated modifier set
        "Meeting sometimes overlaps lunch.",  # another non-enumerated adverb
        "Sprint overlaps almost lunch.",  # right-slot adverb
        "Sprint overlaps lunch almost.",  # trailing right-slot adverb
        "Meeting overlaps lunch today.",  # trailing temporal qualifier glued into the id
        "North station overlaps south station.",  # multi-word entities deferred (narrow v1)
        "Does A overlap B overlap C?",  # interrogative double-verb (base form not in net)
        "Does Sprint overlap lunch now?",  # interrogative trailing adverb
    ],
)
def test_unclean_finite_verb_slots_refuse(text) -> None:
    # any slot that is not exactly one content token refuses rather than glue extra tokens
    # into a fabricated id — this is the backstop the enumerated blocklists cannot provide.
    res = _read(text)
    assert isinstance(res, Refusal), f"{text!r} should refuse but committed {res!r}"


def test_never_negation_is_not_committed_as_positive(vocab_persona) -> None:
    # THE worst class the audit found: 'never' is not a reserved word, so without the
    # single-token gate "Meeting never overlaps lunch." was committed as a POSITIVE
    # overlaps_event(meeting_never, lunch). It must refuse and hold no positive belief.
    res = _read("Meeting never overlaps lunch.")
    assert isinstance(res, Refusal)
    ctx = _ctx(vocab_persona)
    told = realize_comprehension(_read("Meeting never overlaps lunch."), ctx)
    assert isinstance(told, NotRealized)
    assert isinstance(determine(_read("Does meeting overlap lunch?"), ctx), Undetermined)
    assert isinstance(
        determine(_read("Does meeting_never overlap lunch?"), ctx), Undetermined
    )
