"""DETERMINE — transitive subsumption (Step C).

When direct entailment misses, a member/subset query may still hold by SOUND is-a
chaining: ``member ∘ subset*`` and ``subset ∘ subset`` (Description-Logic subsumption),
decided by search (reachability over the sound edges) then verified by the proof_chain
ROBDD. ``member ∘ member`` is NEVER an edge.

The load-bearing wrong=0 bite: the instance-of fallacy ("Socrates is a man" + "man is a
species" ⊬ "Socrates is a species") MUST refuse — if it ever determines, an unsound
member∘member rule was smuggled in.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from generate.determine import Determined, Undetermined, determine
from generate.meaning_graph.reader import comprehend
from generate.realize import realize_comprehension
from session.context import SessionContext

_HIGH = 10**9


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH)


def _tell(text: str, ctx: SessionContext):
    return realize_comprehension(comprehend(text), ctx)


def _ask(text: str, ctx: SessionContext):
    return determine(comprehend(text), ctx)


# --------------------------------------------------------------------------- #
# Sound subsumption: the engine reasons across told facts
# --------------------------------------------------------------------------- #


def test_member_subset_syllogism(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)
    _tell("All men are mortals.", ctx)
    res = _ask("Is Socrates a mortal?", ctx)  # member ∘ subset
    assert isinstance(res, Determined)
    assert res.answer is True and res.basis == "as_told"
    assert res.predicate == "member" and res.subject == "socrates" and res.object == "mortal"


def test_multi_hop_subsumption(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)
    _tell("All men are mortals.", ctx)
    _tell("All mortals are beings.", ctx)
    res = _ask("Is Socrates a being?", ctx)  # member ∘ subset ∘ subset
    assert isinstance(res, Determined) and res.answer is True


def test_subset_transitivity(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("All dogs are mammals.", ctx)
    _tell("All mammals are animals.", ctx)
    res = _ask("Are all dogs animals?", ctx)  # subset ∘ subset
    assert isinstance(res, Determined) and res.answer is True and res.predicate == "subset"


def test_grounds_are_the_chain(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)
    _tell("All men are mortals.", ctx)
    res = _ask("Is Socrates a mortal?", ctx)
    preds = sorted(g.relation_predicate for g in res.grounds)
    assert preds == ["member", "subset"]  # the member fact + the subset edge on the path


def test_long_chain_scales(vocab_persona) -> None:
    # search-then-verify is O(path); a deep chain still determines (no O(n³) blowup).
    ctx = _ctx(vocab_persona)
    syms = [f"glorp{i}" for i in range(11)]
    for i in range(10):
        _tell(f"All {syms[i]}s are {syms[i + 1]}s.", ctx)
    _tell("Socrates is a glorp0.", ctx)
    res = _ask("Is Socrates a glorp10?", ctx)
    assert isinstance(res, Determined) and res.answer is True


# --------------------------------------------------------------------------- #
# wrong=0 BITE — the instance-of fallacy MUST refuse (no member∘member)
# --------------------------------------------------------------------------- #


def test_socrates_species_fallacy_refused(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)  # member(socrates, man)
    _tell("Man is a species.", ctx)  # member(man, species) — NOT subset
    res = _ask("Is Socrates a species?", ctx)
    # member ∘ member is never chained → the fallacy is unreachable.
    assert isinstance(res, Undetermined)
    assert res.reason in {"not_entailed", "ungrounded"}


def test_no_sound_chain_refuses_open_world(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("All dogs are mammals.", ctx)
    _tell("All mammals are animals.", ctx)
    res = _ask("Are all dogs reptiles?", ctx)  # no edge to reptile
    assert isinstance(res, Undetermined) and res.reason == "not_entailed"


def test_reverse_direction_not_entailed(vocab_persona) -> None:
    # subset is directional: dogs ⊆ animals does NOT give animals ⊆ dogs.
    ctx = _ctx(vocab_persona)
    _tell("All dogs are mammals.", ctx)
    _tell("All mammals are animals.", ctx)
    res = _ask("Are all animals dogs?", ctx)
    assert isinstance(res, Undetermined)


# --------------------------------------------------------------------------- #
# Direct entailment is unchanged; subset direct now answers
# --------------------------------------------------------------------------- #


def test_direct_member_still_determines(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Truth is a concept.", ctx)
    res = _ask("Is truth a concept?", ctx)
    assert isinstance(res, Determined) and res.answer is True


def test_direct_subset_now_determines(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("All dogs are mammals.", ctx)
    res = _ask("Are all dogs mammals?", ctx)  # direct subset fact
    assert isinstance(res, Determined) and res.answer is True and res.predicate == "subset"
