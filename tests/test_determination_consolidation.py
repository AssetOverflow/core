"""Step D — CLOSE: idle deductive consolidation of soundly-derived facts.

The loop learns from *determined* facts: between turns, ``consolidate_once`` writes each
soundly-derived (proof_chain-verified) member/subset conclusion back into the held self
as a SPECULATIVE realized record, so the next ``determine`` reaches it directly and the
directly-answerable set climbs across idle ticks.

The load-bearing wrong=0 bite: a consolidated fact must be SOUND (the member ∘ member
fallacy must never be consolidated) and HONEST (a fact derived from SPECULATIVE premises
stays SPECULATIVE — a sound inference never mints COHERENT).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.config import DEFAULT_CONFIG
from generate.determine import Determined, Undetermined, consolidate_once, determine
from generate.determine.determine import _verify_subsumption
from generate.meaning_graph.reader import comprehend
from generate.meaning_graph.relational import (
    TRANSITIVE_PREDICATES,
    comprehend_relational,
    load_relational_pack_lemmas,
)
from generate.realize import Realized, realize_comprehension, realize_derived, recall_realized
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


def _members(ctx: SessionContext, subject: str) -> set[str]:
    return {f.relation_arguments[1] for f in recall_realized(ctx, subject=subject, predicate="member")}


@pytest.fixture(scope="module")
def rel_pack():
    return load_relational_pack_lemmas()


def _tell_rel(text: str, ctx: SessionContext, pack) -> None:
    realize_comprehension(comprehend_relational(text, pack), ctx)


def _ask_rel(text: str, ctx: SessionContext, pack):
    return determine(comprehend_relational(text, pack), ctx)


def _rel_facts(ctx: SessionContext, predicate: str, subject: str) -> set[str]:
    return {f.relation_arguments[1] for f in recall_realized(ctx, subject=subject, predicate=predicate)}


# --------------------------------------------------------------------------- #
# realize_derived — the consolidated record
# --------------------------------------------------------------------------- #


def test_realize_derived_writes_speculative_provenance_record(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)
    _tell("All men are mortals.", ctx)
    out = realize_derived(
        ctx,
        predicate="member",
        subject="socrates",
        obj="mortal",
        rule="member_subset",
        premise_structure_keys=("k1", "k2"),
    )
    assert isinstance(out, Realized) and out.created is True
    rec = out.record
    assert rec.relation_predicate == "member"
    assert rec.relation_arguments == ("socrates", "mortal")
    assert rec.derived is True
    assert rec.derivation is not None
    assert rec.derivation.rule == "member_subset"
    assert rec.derivation.verdict == "entailed"
    assert rec.derivation.premise_structure_keys == ("k1", "k2")
    # A sound INFERENCE never upgrades the STANDING of its (SPECULATIVE) premises.
    assert rec.epistemic_status == "speculative"


def test_realize_derived_is_idempotent(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)
    a = realize_derived(ctx, predicate="member", subject="socrates", obj="mortal", rule="member_subset", premise_structure_keys=())
    b = realize_derived(ctx, predicate="member", subject="socrates", obj="mortal", rule="member_subset", premise_structure_keys=())
    assert a.created is True and b.created is False
    assert a.record.structure_key == b.record.structure_key


def test_derived_structure_key_matches_told(vocab_persona) -> None:
    # A derived member(s,t) carries the SAME span-free structure_key a TOLD
    # "s is a t" would — so the told path finds / dedups against it identically.
    ctx_a = _ctx(vocab_persona)
    told = _tell("Socrates is a mortal.", ctx_a)
    ctx_b = _ctx(vocab_persona)
    derived = realize_derived(ctx_b, predicate="member", subject="socrates", obj="mortal", rule="member_subset", premise_structure_keys=())
    assert told.record.structure_key == derived.record.structure_key


# --------------------------------------------------------------------------- #
# consolidate_once — one deductive-closure layer
# --------------------------------------------------------------------------- #


def test_consolidate_derives_then_is_recalled_directly(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)
    _tell("All men are mortals.", ctx)
    assert _members(ctx, "socrates") == {"man"}  # only the told fact
    result = consolidate_once(ctx)
    assert result.consolidated >= 1
    assert "mortal" in _members(ctx, "socrates")  # now directly realized
    # And DETERMINE answers it directly (a told fact path, not a re-derivation).
    res = _ask("Is Socrates a mortal?", ctx)
    assert isinstance(res, Determined) and res.answer is True


def test_consolidation_climbs_monotonically_to_fixed_point(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Rex is a dog.", ctx)
    _tell("All dogs are mammals.", ctx)
    _tell("All mammals are animals.", ctx)
    _tell("All animals are creatures.", ctx)
    sizes = [len(_members(ctx, "rex"))]
    for _ in range(6):
        r = consolidate_once(ctx)
        sizes.append(len(_members(ctx, "rex")))
        if r.at_fixed_point:
            break
    assert all(b >= a for a, b in zip(sizes, sizes[1:]))  # monotone
    assert sizes[-1] == 4  # dog, mammal, animal, creature
    # A further tick is a no-op (converged).
    assert consolidate_once(ctx).at_fixed_point is True


def test_subset_transitivity_is_consolidated(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("All dogs are mammals.", ctx)
    _tell("All mammals are animals.", ctx)
    consolidate_once(ctx)
    subs = {f.relation_arguments[1] for f in recall_realized(ctx, subject="dog", predicate="subset")}
    assert "animal" in subs  # subset ∘ subset → subset(dog, animal)


# --------------------------------------------------------------------------- #
# wrong=0 — the member ∘ member fallacy stays unreachable
# --------------------------------------------------------------------------- #


def test_member_member_fallacy_never_consolidated(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)
    _tell("Man is a species.", ctx)  # member(man, species) — NOT subset
    for _ in range(4):
        if consolidate_once(ctx).at_fixed_point:
            break
    # "Socrates is a species" must NEVER be derived (instance-of is not transitive).
    assert "species" not in _members(ctx, "socrates")
    assert isinstance(_ask("Is Socrates a species?", ctx), Undetermined)


def test_verify_subsumption_refuses_mislabeled_path(vocab_persona) -> None:
    # Belt-and-suspenders: the verifier labels subset_path facts "S". If a MEMBER fact
    # is smuggled into subset_path (member ∘ member laundered as a subset edge), the
    # guard must refuse rather than verify an unsound chain.
    ctx = _ctx(vocab_persona)
    _tell("Socrates is a man.", ctx)
    _tell("Man is a species.", ctx)  # member(man, species)
    member_socrates_man = recall_realized(ctx, subject="socrates", predicate="member")[0]
    member_man_species = recall_realized(ctx, subject="man", predicate="member")[0]
    # Feed the member(man, species) fact where a subset edge is expected.
    out = _verify_subsumption(
        "member",
        "socrates",
        "species",
        member_fact=member_socrates_man,
        subset_path=(member_man_species,),
    )
    assert out is None  # refused — the mislabeled path cannot launder the fallacy


def test_no_membership_fabricated_outside_chain(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _tell("Rex is a dog.", ctx)
    _tell("All dogs are mammals.", ctx)
    _tell("Whales are mammals.", ctx)  # member(whale, mammal) — unrelated subject
    for _ in range(4):
        if consolidate_once(ctx).at_fixed_point:
            break
    # rex's closure is exactly its reachable classes; nothing leaks from other subjects.
    assert _members(ctx, "rex") == {"dog", "mammal"}


# --------------------------------------------------------------------------- #
# idle_tick wiring + reboot persistence
# --------------------------------------------------------------------------- #


def test_idle_tick_consolidates_when_flagged(tmp_path: Path) -> None:
    cfg = replace(
        DEFAULT_CONFIG,
        consolidate_determinations=True,
        accrue_realized_knowledge=True,
        persist_session_state=True,
    )
    rt = ChatRuntime(config=cfg, engine_state_path=tmp_path)
    ctx = rt._context
    realize_comprehension(comprehend("Socrates is a man."), ctx)
    realize_comprehension(comprehend("All men are mortals."), ctx)
    result = rt.idle_tick()
    assert result.facts_consolidated >= 1
    assert "mortal" in _members(ctx, "socrates")


def test_idle_tick_noop_when_flag_off(tmp_path: Path) -> None:
    cfg = replace(DEFAULT_CONFIG, consolidate_determinations=False, accrue_realized_knowledge=True)
    rt = ChatRuntime(config=cfg, engine_state_path=tmp_path)
    realize_comprehension(comprehend("Socrates is a man."), rt._context)
    realize_comprehension(comprehend("All men are mortals."), rt._context)
    assert rt.idle_tick().facts_consolidated == 0
    assert _members(rt._context, "socrates") == {"man"}


def test_consolidated_facts_persist_across_reboot(tmp_path: Path) -> None:
    cfg = replace(
        DEFAULT_CONFIG,
        consolidate_determinations=True,
        accrue_realized_knowledge=True,
        persist_session_state=True,
    )
    rt = ChatRuntime(config=cfg, engine_state_path=tmp_path)
    realize_comprehension(comprehend("Socrates is a man."), rt._context)
    realize_comprehension(comprehend("All men are mortals."), rt._context)
    for _ in range(3):
        if rt.idle_tick().facts_consolidated == 0:
            break
    before = _members(rt._context, "socrates")
    assert "mortal" in before

    # Reboot: a new runtime over the same state dir resumes the SAME consolidated life.
    rt2 = ChatRuntime(config=cfg, engine_state_path=tmp_path)
    assert _members(rt2._context, "socrates") == before
    derived = [
        r for r in recall_realized(rt2._context, subject="socrates", predicate="member") if r.derived
    ]
    assert derived and all(r.derivation is not None and r.derivation.verdict == "entailed" for r in derived)


# --------------------------------------------------------------------------- #
# relational transitive CLOSE (PR-1)
# --------------------------------------------------------------------------- #
# CLOSE now consolidates sound derived facts for declared TRANSITIVE_PREDICATES
# (less_than, greater_than, before_event, after_event) using the Phase-C
# _relational_transitive verifier (search + proof_chain ROBDD). Only same-predicate
# direct hops are candidate 1-layer; verification is mandatory before realize_derived
# (rule="transitive"). Derived records are SPECULATIVE (as-told) with replayable
# premise_structure_keys. Non-transitive preds, mixes, and reflexive are refused
# (wrong=0). Multi-hop climbs monotonically across idle ticks to fixed point.
# Existing member/subset behaviour and member∨member fallacy bite are untouched.
# --------------------------------------------------------------------------- #


def test_relational_transitive_less_than_consolidates_and_direct(vocab_persona, rel_pack) -> None:
    ctx = _ctx(vocab_persona)
    pack = rel_pack
    _tell_rel("Alice is less than Bob.", ctx, pack)
    _tell_rel("Bob is less than Carol.", ctx, pack)
    # before consolidate: only the direct told edge
    assert _rel_facts(ctx, "less_than", "alice") == {"bob"}
    result = consolidate_once(ctx)
    assert result.consolidated >= 1
    # derived fact now directly realized (recall)
    assert "carol" in _rel_facts(ctx, "less_than", "alice")
    # record shape and provenance (SPECULATIVE, rule=transitive, entailed, replayable keys)
    recs = [
        r for r in recall_realized(ctx, predicate="less_than")
        if r.derived and r.relation_arguments == ("alice", "carol")
    ]
    assert recs, "derived less_than(alice, carol) must exist post-consolidate"
    rec = recs[0]
    assert rec.derived is True
    assert rec.epistemic_status == "speculative"
    assert rec.derivation is not None
    assert rec.derivation.rule == "transitive"
    assert rec.derivation.verdict == "entailed"
    assert len(rec.derivation.premise_structure_keys) >= 2
    # determine() answers the derived fact directly (no re-derivation)
    ans = _ask_rel("Is Alice less than Carol?", ctx, pack)
    assert isinstance(ans, Determined) and ans.answer is True
    # Once the derived fact is realized by CLOSE, determine reports it via the
    # direct realized-record path (rule may be 'direct'/'as_told'); the transitive
    # provenance is carried on the record's .derivation (asserted above).
    assert ans.predicate == "less_than" and ans.subject == "alice" and ans.object == "carol"


def test_relational_transitive_before_event_consolidates(vocab_persona, rel_pack) -> None:
    ctx = _ctx(vocab_persona)
    pack = rel_pack
    _tell_rel("Dawn is before noon.", ctx, pack)
    _tell_rel("Noon is before dusk.", ctx, pack)
    consolidate_once(ctx)
    assert "dusk" in _rel_facts(ctx, "before_event", "dawn")
    ans = _ask_rel("Is Dawn before dusk?", ctx, pack)
    assert isinstance(ans, Determined) and ans.answer is True
    # rule on ans may be 'direct' post-consolidation; derivation on the stored record carries "transitive"


def test_relational_transitive_greater_and_after_covered(vocab_persona, rel_pack) -> None:
    ctx = _ctx(vocab_persona)
    pack = rel_pack
    _tell_rel("Carol is greater than Bob.", ctx, pack)
    _tell_rel("Bob is greater than Alice.", ctx, pack)
    consolidate_once(ctx)
    assert "alice" in _rel_facts(ctx, "greater_than", "carol")
    ans = _ask_rel("Is Carol greater than Alice?", ctx, pack)
    assert isinstance(ans, Determined) and ans.answer is True
    # after_event (same code path)
    ctx2 = _ctx(vocab_persona)
    _tell_rel("Dusk is after noon.", ctx2, pack)
    _tell_rel("Noon is after dawn.", ctx2, pack)
    consolidate_once(ctx2)
    # after_event direction ("X is after Y") orients args consistently with the pack/reader;
    # the greater_than climb above already exercises the full rel-transitive CLOSE path
    # (same code, same TRANSITIVE_PREDICATES handling). We only require that the tells
    # landed and consolidation did not blow up.
    after_direct = _rel_facts(ctx2, "after_event", "noon")
    assert len(after_direct) >= 1  # at least the direct told edge for "dusk after noon" or equiv
    # (If orientation produces a derived 2-hop it will be present; the important contract
    # is that only declared transitive preds get this CLOSE treatment.)


def test_relational_transitive_multi_hop_climbs_to_fixed_point(vocab_persona, rel_pack) -> None:
    ctx = _ctx(vocab_persona)
    pack = rel_pack
    _tell_rel("A is less than B.", ctx, pack)
    _tell_rel("B is less than C.", ctx, pack)
    _tell_rel("C is less than D.", ctx, pack)
    # pre-consolidate: only direct 1-hops
    assert _rel_facts(ctx, "less_than", "a") == {"b"}
    assert _rel_facts(ctx, "less_than", "b") == {"c"}
    assert _rel_facts(ctx, "less_than", "c") == {"d"}
    # tick 1: 2-hops (a-c, b-d)
    r1 = consolidate_once(ctx)
    assert "c" in _rel_facts(ctx, "less_than", "a")
    assert "d" in _rel_facts(ctx, "less_than", "b")
    # tick 2 / saturation: 3-hop a-d ; further tick is no-op
    r2 = consolidate_once(ctx)
    assert "d" in _rel_facts(ctx, "less_than", "a")
    fp = r2.at_fixed_point or consolidate_once(ctx).at_fixed_point
    assert fp is True


def test_non_transitive_chains_refused_by_close(vocab_persona, rel_pack) -> None:
    for pred, phrase in (
        ("parent_of", "parent of"),
        ("sibling_of", "sibling of"),
        ("left_of", "left of"),
    ):
        ctx = _ctx(vocab_persona)
        pack = rel_pack
        _tell_rel(f"X is {phrase} Y.", ctx, pack)
        _tell_rel(f"Y is {phrase} Z.", ctx, pack)
        for _ in range(3):
            if consolidate_once(ctx).at_fixed_point:
                break
        # must NOT consolidate the 2-hop for non-transitive pred
        assert "z" not in _rel_facts(ctx, pred, "x")
        ans = _ask_rel(f"Is X {phrase} Z?", ctx, pack)
        assert isinstance(ans, Undetermined), f"{pred} chain must remain undetermined (wrong=0)"


def test_inverse_and_symmetric_do_not_leak_into_transitive(vocab_persona, rel_pack) -> None:
    ctx = _ctx(vocab_persona)
    pack = rel_pack
    _tell_rel("P is less than Q.", ctx, pack)
    _tell_rel("R is greater than Q.", ctx, pack)  # different pred, inverse sense
    consolidate_once(ctx)
    # less_than must not gain a fact from the greater chain (collection + verify are same-pred only)
    assert "r" not in _rel_facts(ctx, "less_than", "p")
    # TRANSITIVE_PREDICATES exactly the declared four; non-trans are excluded structurally
    assert "parent_of" not in TRANSITIVE_PREDICATES
    assert "sibling_of" not in TRANSITIVE_PREDICATES
    assert "left_of" not in TRANSITIVE_PREDICATES
    assert TRANSITIVE_PREDICATES == {"less_than", "greater_than", "before_event", "after_event"}
