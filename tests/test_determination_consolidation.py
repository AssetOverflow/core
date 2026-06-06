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
