"""DETERMINE — one-hop sound relational entailment (mastery-v2 Step 3 lead).

A relational query may hold by ONE sound predicate-algebra rule that reads a stored
edge in its OTHER lawful direction:

    INVERSE/converse   greater_than(a, b)  <=  told less_than(b, a)
    SYMMETRIC          sibling_of(b, a)    <=  told sibling_of(a, b)

Scope is deliberately narrow: OPEN-WORLD (asserts only True, never False), ONE hop
(NO transitive chaining), DECLARED rules only (less_than is NOT self-inverse;
parent_of is NOT symmetric). Closed-world / assert-False / FrameVerdict are out of
scope (a later slice). The wrong=0 discipline lives in the confuser block below.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from generate.determine import Determined, Undetermined, determine
from generate.meaning_graph.relational import (
    INVERSE_OF,
    RELATIONAL_PREDICATES,
    SYMMETRIC_PREDICATES,
    TRANSITIVE_PREDICATES,
    comprehend_relational,
    load_relational_pack_lemmas,
    load_relational_pack_symmetric,
)
from generate.realize import realize_comprehension
from session.context import SessionContext

_HIGH = 10**9


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


@pytest.fixture(scope="module")
def pack():
    return load_relational_pack_lemmas()


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH)


def _tell(text: str, ctx: SessionContext, pack):
    return realize_comprehension(comprehend_relational(text, pack), ctx)


def _ask(text: str, ctx: SessionContext, pack):
    return determine(comprehend_relational(text, pack), ctx)


# --------------------------------------------------------------------------- #
# Positive — the engine now derives the simplest entailed relational facts
# --------------------------------------------------------------------------- #


def test_inverse_converse_admits_true(vocab_persona, pack) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Bob is less than Alice.", ctx, pack)  # less_than(bob, alice)
    res = _ask("Is Alice greater than Bob?", ctx, pack)  # greater_than(alice, bob)
    assert isinstance(res, Determined)
    assert res.answer is True and res.basis == "as_told" and res.rule == "inverse"
    assert res.predicate == "greater_than"
    assert res.subject == "alice" and res.object == "bob"
    # grounds = the single stored converse edge
    assert len(res.grounds) == 1 and res.grounds[0].relation_predicate == "less_than"


def test_symmetric_admits_true(vocab_persona, pack) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Alice is the sibling of Bob.", ctx, pack)  # sibling_of(alice, bob)
    res = _ask("Is Bob the sibling of Alice?", ctx, pack)  # sibling_of(bob, alice)
    assert isinstance(res, Determined) and res.answer is True
    assert res.rule == "symmetric" and res.predicate == "sibling_of"
    assert res.subject == "bob" and res.object == "alice"


def test_direct_stored_direction_still_determines(vocab_persona, pack) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Alice is the sibling of Bob.", ctx, pack)
    res = _ask("Is Alice the sibling of Bob?", ctx, pack)  # the stored direction
    assert isinstance(res, Determined) and res.answer is True and res.rule == "direct"


# --------------------------------------------------------------------------- #
# wrong=0 confuser block — the rule must not over-fire
# --------------------------------------------------------------------------- #


def test_less_than_is_not_self_inverse(vocab_persona, pack) -> None:
    """less_than is asymmetric: a<b does NOT entail b<a (its converse is greater_than)."""
    ctx = _ctx(vocab_persona)
    _tell("Alice is less than Bob.", ctx, pack)  # less_than(alice, bob)
    res = _ask("Is Bob less than Alice?", ctx, pack)  # less_than(bob, alice)?
    assert isinstance(res, Undetermined)


def test_sibling_does_not_imply_parent(vocab_persona, pack) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Alice is the sibling of Bob.", ctx, pack)
    res = _ask("Is Alice the parent of Bob?", ctx, pack)
    assert isinstance(res, Undetermined)


def test_greater_than_does_not_imply_equal(vocab_persona, pack) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Alice is greater than Bob.", ctx, pack)
    res = _ask("Is Alice equal to Bob?", ctx, pack)
    assert isinstance(res, Undetermined)


def test_no_one_hop_chaining_of_nontransitive_predicate(vocab_persona, pack) -> None:
    """One-hop rules never silently chain a NON-transitive predicate: parent_of is not
    transitive, so ``a parent_of b`` + ``b parent_of c`` must refuse. (A same-predicate
    STRICT-ORDER chain like ``a<b<c`` now determines via the transitive rule — that moved
    to the B2 capability; see ``test_determine_relational_transitive``.)"""
    ctx = _ctx(vocab_persona)
    _tell("Alice is the parent of Bob.", ctx, pack)
    _tell("Bob is the parent of Carol.", ctx, pack)
    res = _ask("Is Alice the parent of Carol?", ctx, pack)
    assert isinstance(res, Undetermined)


def test_no_transitive_chain_through_inverse(vocab_persona, pack) -> None:
    """The inverse rule is also one hop: it must not become a transitive bridge."""
    ctx = _ctx(vocab_persona)
    _tell("Bob is less than Alice.", ctx, pack)  # => greater_than(alice, bob) by inverse
    _tell("Carol is less than Bob.", ctx, pack)  # => greater_than(bob, carol) by inverse
    res = _ask("Is Alice greater than Carol?", ctx, pack)  # needs transitive — refuse
    assert isinstance(res, Undetermined)


def test_unsupported_predicate_refuses(vocab_persona, pack) -> None:
    ctx = _ctx(vocab_persona)
    # No told fact at all → ungrounded refusal, never a guess.
    res = _ask("Is Alice the sibling of Bob?", ctx, pack)
    assert isinstance(res, Undetermined)


def test_never_asserts_false(vocab_persona, pack) -> None:
    """Open-world: every determination is True-or-refuse; answer=False is unreachable
    (INV-30 is the structural guarantee — this is the behavioral echo on this path)."""
    ctx = _ctx(vocab_persona)
    _tell("Alice is less than Bob.", ctx, pack)
    for q in (
        "Is Bob less than Alice?",
        "Is Alice greater than Bob?",
        "Is Alice equal to Bob?",
        "Is Alice the parent of Bob?",
        "Is Alice less than Bob?",
    ):
        res = _ask(q, ctx, pack)
        if isinstance(res, Determined):
            assert res.answer is True


# --------------------------------------------------------------------------- #
# Ontology pins — the algebra cannot silently diverge from the pack / vocab
# --------------------------------------------------------------------------- #


def test_symmetric_table_matches_pack_ontology(pack) -> None:
    """SYMMETRIC_PREDICATES MUST equal the pack's graph.edge.symmetric declarations —
    the pack is the source of truth; the constant is the runtime-cheap mirror."""
    assert SYMMETRIC_PREDICATES == load_relational_pack_symmetric()


def test_algebra_members_are_relational_predicates() -> None:
    """Every inverse/symmetric lemma is a real reader predicate — a typo cannot mint
    an unknown predicate into the determination path."""
    for lemma in set(INVERSE_OF) | SYMMETRIC_PREDICATES:
        assert lemma in RELATIONAL_PREDICATES


def test_inverse_is_an_involution() -> None:
    """inverse(inverse(p)) == p, and no predicate is its own inverse (asymmetry)."""
    for lemma, other in INVERSE_OF.items():
        assert lemma != other
        assert INVERSE_OF[other] == lemma


def test_transitive_predicates_closed_and_excludes() -> None:
    """TRANSITIVE_PREDICATES is CLOSED, default-off, and exactly the four strict orders —
    every member is a real reader predicate, and every predicate that is symmetric,
    asymmetric-kinship, spatial, or containment STAYS OUT (admitting any would be unsound
    or needs a shared-frame proof this slice lacks)."""
    assert TRANSITIVE_PREDICATES == {
        "less_than",
        "greater_than",
        "before_event",
        "after_event",
    }
    # every transitive lemma is a real reader predicate (a typo cannot mint an unknown one)
    for lemma in TRANSITIVE_PREDICATES:
        assert lemma in RELATIONAL_PREDICATES
    # the deliberately-excluded predicates are explicitly absent (default-off)
    excluded = {
        "sibling_of",
        "spouse_of",
        "parent_of",
        "child_of",
        "left_of",
        "right_of",
        "inside_of",
        "during_event",
        "overlaps_event",
    }
    assert excluded.isdisjoint(TRANSITIVE_PREDICATES)
    # the excluded set names real reader predicates (so the exclusion is meaningful)
    for lemma in excluded:
        assert lemma in RELATIONAL_PREDICATES
