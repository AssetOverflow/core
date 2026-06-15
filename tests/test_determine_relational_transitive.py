"""DETERMINE — transitive RELATIONAL closure over declared strict orders (B2).

A declared strict-order predicate (``less_than`` / ``greater_than`` / ``before_event`` /
``after_event``) may hold by SOUND transitive closure over its OWN realized edges
(``p(a,b) ∧ p(b,c) ⊨ p(a,c)``) — search (BFS reachability) then verify (proof_chain
ROBDD). Open-world: asserts only ``answer=True``, never False; composes only same-predicate
edges (no transitive-through-inverse, no cross-predicate).

The load-bearing wrong=0 bites: a NON-transitive predicate's chain MUST refuse
(``sibling_of`` / ``parent_of`` / ``left_of`` / ``right_of``), a MIXED-predicate chain
MUST refuse, a chain with a missing middle MUST refuse, and a reflexive / cyclic query MUST
NOT fabricate. Any ``Determined`` on those is an over-fire.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from generate.determine import Determined, Undetermined, determine
from generate.meaning_graph.relational import (
    comprehend_relational,
    load_relational_pack_lemmas,
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


def _tell(text: str, ctx: SessionContext, pack) -> None:
    realize_comprehension(comprehend_relational(text, pack), ctx)


def _ask(text: str, ctx: SessionContext, pack):
    return determine(comprehend_relational(text, pack), ctx)


def _scenario(facts, query, vocab_persona, pack):
    ctx = _ctx(vocab_persona)
    for fact in facts:
        _tell(fact, ctx, pack)
    return _ask(query, ctx, pack)


# --------------------------------------------------------------------------- #
# Positives — the four declared strict orders close transitively
# --------------------------------------------------------------------------- #


def test_less_than_two_hop(vocab_persona, pack) -> None:
    res = _scenario(
        ["Alice is less than Bob.", "Bob is less than Carol."],
        "Is Alice less than Carol?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Determined)
    assert res.answer is True and res.basis == "as_told" and res.rule == "transitive"
    assert res.predicate == "less_than" and res.subject == "alice" and res.object == "carol"
    assert len(res.grounds) == 2  # the two edges on the chain


def test_less_than_three_hop_scales(vocab_persona, pack) -> None:
    res = _scenario(
        [
            "Amy is less than Bea.",
            "Bea is less than Cleo.",
            "Cleo is less than Dana.",
        ],
        "Is Amy less than Dana?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Determined) and res.answer is True and res.rule == "transitive"
    assert res.subject == "amy" and res.object == "dana" and len(res.grounds) == 3


def test_greater_than_two_hop(vocab_persona, pack) -> None:
    res = _scenario(
        ["Carol is greater than Bob.", "Bob is greater than Alice."],
        "Is Carol greater than Alice?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Determined) and res.answer is True and res.rule == "transitive"
    assert res.predicate == "greater_than" and res.subject == "carol" and res.object == "alice"


def test_before_event_chain(vocab_persona, pack) -> None:
    res = _scenario(
        ["Dawn is before noon.", "Noon is before dusk."],
        "Is dawn before dusk?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Determined) and res.answer is True and res.rule == "transitive"
    assert res.predicate == "before_event" and res.subject == "dawn" and res.object == "dusk"


def test_after_event_chain(vocab_persona, pack) -> None:
    res = _scenario(
        ["Dusk is after noon.", "Noon is after dawn."],
        "Is dusk after dawn?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Determined) and res.answer is True and res.rule == "transitive"
    assert res.predicate == "after_event" and res.subject == "dusk" and res.object == "dawn"


# --------------------------------------------------------------------------- #
# wrong=0 BITES — non-transitive predicates, mixed chains, gaps, cycles refuse
# --------------------------------------------------------------------------- #


def test_sibling_of_chain_refuses(vocab_persona, pack) -> None:
    # sibling_of is SYMMETRIC, not transitive — a sib b, b sib c does NOT give a sib c.
    res = _scenario(
        ["Alice is the sibling of Bob.", "Bob is the sibling of Carol."],
        "Is Alice the sibling of Carol?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_parent_of_chain_refuses(vocab_persona, pack) -> None:
    # parent ∘ parent = grandparent ≠ parent — must refuse.
    res = _scenario(
        ["Alice is the parent of Bob.", "Bob is the parent of Carol."],
        "Is Alice the parent of Carol?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_left_of_chain_refuses(vocab_persona, pack) -> None:
    # spatial left_of is NOT admitted as transitive (needs a shared-frame proof).
    res = _scenario(
        ["The box is left of the cup.", "The cup is left of the plate."],
        "Is the box left of the plate?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_right_of_chain_refuses(vocab_persona, pack) -> None:
    res = _scenario(
        ["The plate is right of the cup.", "The cup is right of the box."],
        "Is the plate right of the box?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_mixed_predicate_chain_refuses(vocab_persona, pack) -> None:
    # less_than + before_event must NOT compose: the less_than search sees only the
    # alice→bob edge; carol is unreachable over less_than edges.
    res = _scenario(
        ["Alice is less than Bob.", "Bob is before Carol."],
        "Is Alice less than Carol?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_missing_middle_refuses(vocab_persona, pack) -> None:
    # a<b and c<d with b != c — no contiguous chain from alice to dana.
    res = _scenario(
        ["Alice is less than Bob.", "Carol is less than Dana."],
        "Is Alice less than Dana?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_reflexive_query_refuses(vocab_persona, pack) -> None:
    # strict orders are irreflexive — a chain never fabricates a < a.
    res = _scenario(
        ["Alice is less than Bob.", "Bob is less than Carol."],
        "Is Alice less than Alice?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_cyclic_conflicting_no_fabrication(vocab_persona, pack) -> None:
    # a<b and b<a (conflicting). A query for an absent target has no forward path —
    # the cycle must not fabricate a reachability claim.
    res = _scenario(
        ["Alice is less than Bob.", "Bob is less than Alice."],
        "Is Alice less than Carol?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_transitive_through_inverse_not_composed(vocab_persona, pack) -> None:
    # B2 does NOT compose transitive-with-inverse: bob<alice, carol<bob entail carol<alice
    # (a less_than chain), but the GREATER_THAN query has no greater_than edges to chain
    # and one-hop inverse is a single hop — so it must refuse.
    res = _scenario(
        ["Bob is less than Alice.", "Carol is less than Bob."],
        "Is Alice greater than Carol?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)


def test_unsupported_predicate_still_undetermined(vocab_persona, pack) -> None:
    # a categorical/propositional predicate is not in the supported set at all.
    res = _scenario([], "Is Alice less than Bob?", vocab_persona, pack)
    assert isinstance(res, Undetermined)  # ungrounded — absence never asserts


def test_edge_budget_exhaustion_refuses(vocab_persona, pack, monkeypatch) -> None:
    # Above the edge budget the transitive search declines (a safe COVERAGE refusal —
    # never an unsound answer): the SAME chain that determines under the normal budget
    # refuses when the predicate's realized-edge count exceeds the cap. (Patch the module
    # object, not the dotted path — `generate.determine.determine` resolves to the
    # re-exported function, not the submodule.)
    import importlib

    det_mod = importlib.import_module("generate.determine.determine")
    monkeypatch.setattr(det_mod, "_TRANSITIVE_EDGE_BUDGET", 1)
    res = _scenario(
        ["Alice is less than Bob.", "Bob is less than Carol."],
        "Is Alice less than Carol?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Undetermined)  # 2 edges > budget(1) → coverage refusal, not a proof


# --------------------------------------------------------------------------- #
# Regression — one-hop inverse/symmetric and direct entailment are intact
# --------------------------------------------------------------------------- #


def test_one_hop_inverse_still_determines(vocab_persona, pack) -> None:
    res = _scenario(
        ["Bob is less than Alice."], "Is Alice greater than Bob?", vocab_persona, pack
    )
    assert isinstance(res, Determined) and res.answer is True and res.rule == "inverse"


def test_one_hop_symmetric_still_determines(vocab_persona, pack) -> None:
    res = _scenario(
        ["Alice is the sibling of Bob."],
        "Is Bob the sibling of Alice?",
        vocab_persona,
        pack,
    )
    assert isinstance(res, Determined) and res.answer is True and res.rule == "symmetric"


def test_direct_strict_order_is_direct_not_transitive(vocab_persona, pack) -> None:
    # a single told edge answers directly (rule="direct") — the transitive step is only
    # reached when direct and one-hop both miss.
    res = _scenario(
        ["Alice is less than Bob."], "Is Alice less than Bob?", vocab_persona, pack
    )
    assert isinstance(res, Determined) and res.answer is True and res.rule == "direct"
