"""REALIZE — OOV subjects are realizable (the in-vocab gate is lifted).

R0 declined OOV subjects on the (mistaken) belief that OOV grounding is
non-deterministic. It is in fact deterministic and reboot-stable, and #591 makes it
injective. These tests pin the consumer half: an OOV subject realizes a normal
SPECULATIVE record, distinct OOV facts stay distinct, and the fact survives reboot —
crucially via the VAULT RECORD, not the (session-scoped, snapshot-excluded) vocab
transient. They assert STRUCTURAL distinctness / stability (names + content_hash +
restored bytes), which holds regardless of whether the versor collides — versor
injectivity itself is #591's own test.
"""

from __future__ import annotations

import pytest

from algebra.versor import versor_condition
from chat.runtime import ChatRuntime
from generate.meaning_graph.reader import comprehend
from generate.realize import NotRealized, Realized, realize_comprehension, recall_realized
from session.context import SessionContext

_HIGH_INTERVAL = 10**9


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)


def _realize(text: str, ctx: SessionContext):
    return realize_comprehension(comprehend(text), ctx)


def test_oov_subject_realizes(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _realize("Rhea is a raven.", ctx)  # "rhea"/"raven" are OOV
    assert isinstance(res, Realized) and res.created is True
    assert res.record.relation_arguments == ("rhea", "raven")
    assert res.record.epistemic_status == "speculative"
    got = recall_realized(ctx, subject="rhea")
    assert len(got) == 1 and got[0].content_hash == res.record.content_hash


def test_distinct_oov_subjects_stay_distinct(vocab_persona) -> None:
    # Even if the field versor were to collide (pre-#591 substrate), the structural
    # key keeps distinct OOV facts distinct — correctness never rests on the versor.
    ctx = _ctx(vocab_persona)
    _realize("Rhea is a raven.", ctx)
    _realize("Zorg is a planet.", ctx)
    assert len(ctx.vault._metadata) == 2
    assert len({m["structure_key"] for m in ctx.vault._metadata}) == 2
    assert recall_realized(ctx, subject="rhea")[0].relation_arguments == ("rhea", "raven")
    assert recall_realized(ctx, subject="zorg")[0].relation_arguments == ("zorg", "planet")


def test_oov_fact_is_idempotent(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    first = _realize("Rhea is a raven.", ctx)
    second = _realize("Rhea is a raven.", ctx)
    assert isinstance(first, Realized) and first.created is True
    assert isinstance(second, Realized) and second.created is False
    assert len(ctx.vault._metadata) == 1


def test_oov_placement_deterministic_across_fresh_contexts(vocab_persona) -> None:
    # OOV grounding is deterministic: the same OOV fact realized in two independent
    # fresh contexts (same shared vocab) yields identical content_hash AND identical
    # stored versor bytes.
    a = _ctx(vocab_persona)
    b = _ctx(vocab_persona)
    ra = _realize("Rhea is a raven.", a)
    rb = _realize("Rhea is a raven.", b)
    assert isinstance(ra, Realized) and isinstance(rb, Realized)
    assert ra.record.content_hash == rb.record.content_hash
    va = a.vault._versors[ra.record.vault_index].tobytes()
    vb = b.vault._versors[rb.record.vault_index].tobytes()
    assert va == vb


def test_oov_fact_survives_reboot_into_a_FRESH_vocab(vocab_persona) -> None:
    # The strongest reboot claim: restore into a context built on a DIFFERENT vocab
    # instance (no "rhea" transient present) — the realized fact is still recalled
    # structurally and its versor bytes are restored exactly. Proves reboot-stability
    # rests on the VAULT RECORD, not on the session-scoped vocab transient.
    ctx = _ctx(vocab_persona)
    res = _realize("Rhea is a raven.", ctx)
    assert isinstance(res, Realized)
    pre_versor_bytes = ctx.vault._versors[res.record.vault_index].tobytes()
    snap = ctx.snapshot()

    fresh = ChatRuntime(no_load_state=True)  # a brand-new vocab/persona surface
    rebooted = SessionContext(
        vocab=fresh._context.vocab,
        persona=fresh._context.persona,
        vault_reproject_interval=_HIGH_INTERVAL,
    )
    rebooted.restore(snap)

    got = recall_realized(rebooted, subject="rhea")
    assert len(got) == 1
    assert got[0].content_hash == res.record.content_hash
    post_versor = rebooted.vault._versors[got[0].vault_index]
    assert post_versor.tobytes() == pre_versor_bytes  # exact restore, no reprojection
    assert versor_condition(post_versor) < 1e-6


def test_ineligible_oov_input_still_realizes_nothing(vocab_persona) -> None:
    # Lifting the in-vocab gate does NOT loosen the other wrong=0 floors.
    ctx = _ctx(vocab_persona)
    assert isinstance(_realize("Is rhea a raven?", ctx), NotRealized)  # query
    assert isinstance(_realize("Rhea is a raven. Zorg is a planet.", ctx), NotRealized)  # multi
    assert len(ctx.vault._metadata) == 0
