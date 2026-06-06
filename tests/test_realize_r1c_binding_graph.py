"""REALIZE slice R1c — a comprehended arithmetic structure (binding_graph) is
realized as a SPECULATIVE, structurally-recallable vault entry.

This is the SECOND substrate behind the shared ``structure_kind`` record. Its
entities (``alice``, the synthesized ``total``) are symbolic/OOV, so correctness
rests on the structural key + structural recall, never the (colliding) field
versor — and reboot-stability rests on the Shape B+ snapshot of the exact bytes.
"""

from __future__ import annotations

import pytest

from algebra.versor import versor_condition
from chat.runtime import ChatRuntime
from generate.quantitative_comprehension import comprehend_quantitative
from generate.realize import (
    NotRealized,
    Realized,
    realize_quantitative,
    recall_realized,
)
from session.context import SessionContext
from teaching.epistemic import EpistemicStatus

_HIGH_INTERVAL = 10**9

_FACT = "alice has 3 coins. how many coins does alice have?"
_SUM = (
    "alice has 3 coins. bob has 2 more coins than alice. "
    "how many coins do alice and bob have?"
)


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)


def _realize(text: str, ctx: SessionContext):
    return realize_quantitative(comprehend_quantitative(text), ctx)


# --------------------------------------------------------------------------- #
# wrong=0 — a Refusal realizes nothing
# --------------------------------------------------------------------------- #


def test_refusal_realizes_nothing(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = realize_quantitative(comprehend_quantitative("the weather is nice."), ctx)
    assert isinstance(res, NotRealized) and res.reason == "refusal"
    assert len(ctx.vault._metadata) == 0


# --------------------------------------------------------------------------- #
# A told arithmetic fact is realized as a binding_graph record
# --------------------------------------------------------------------------- #


def test_arithmetic_fact_is_realized(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _realize(_FACT, ctx)
    assert isinstance(res, Realized) and res.created is True
    r = res.record
    assert r.structure_kind == "binding_graph"
    assert r.epistemic_status == "speculative"  # never COHERENT by default
    assert "alice" in r.entity_names
    assert r.structure_canonical and r.content_hash and r.structure_key and r.replay_hash
    assert r.source_span  # provenance present
    assert len(ctx.vault._metadata) == 1


def test_sum_problem_is_realized_with_synthesized_total(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _realize(_SUM, ctx)
    assert isinstance(res, Realized) and res.created is True
    # the synthesized "total" entity and the real ones are all captured
    assert set(res.record.entity_names) >= {"alice", "bob", "total"}


# --------------------------------------------------------------------------- #
# Structural recall (R1a) finds binding_graph records by kind / entity
# --------------------------------------------------------------------------- #


def test_recall_by_structure_kind_and_entity(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _realize(_FACT, ctx)
    got = recall_realized(ctx, structure_kind="binding_graph")
    assert len(got) == 1
    assert recall_realized(ctx, structure_kind="binding_graph", entity="alice")[0].content_hash == (
        got[0].content_hash
    )
    # the meaning_graph subject filter does not match a binding_graph record
    assert recall_realized(ctx, subject="alice") == ()


# --------------------------------------------------------------------------- #
# Idempotency — same arithmetic structure dedups
# --------------------------------------------------------------------------- #


def test_arithmetic_realize_is_idempotent(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    first = _realize(_FACT, ctx)
    second = _realize(_FACT, ctx)
    assert isinstance(first, Realized) and first.created is True
    assert isinstance(second, Realized) and second.created is False
    assert second.record.structure_key == first.record.structure_key
    assert len(ctx.vault._metadata) == 1


def test_distinct_arithmetic_not_collapsed(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _realize(_FACT, ctx)
    _realize(_SUM, ctx)  # different facts/equations -> different structure_key
    assert len(ctx.vault._metadata) == 2
    assert len({m["structure_key"] for m in ctx.vault._metadata}) == 2


# --------------------------------------------------------------------------- #
# Exit gate — realize -> snapshot -> reboot -> structural recall, byte-exact
# --------------------------------------------------------------------------- #


def test_binding_graph_survives_reboot_and_recalls_structurally(vocab_persona) -> None:
    vocab, persona = vocab_persona
    ctx = _ctx(vocab_persona)
    res = _realize(_FACT, ctx)
    assert isinstance(res, Realized)
    pre_versor_bytes = ctx.vault._versors[res.record.vault_index].tobytes()

    rebooted = SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)
    rebooted.restore(ctx.snapshot())

    got = recall_realized(rebooted, structure_kind="binding_graph", entity="alice")
    assert len(got) == 1
    assert got[0].content_hash == res.record.content_hash
    assert got[0].structure_key == res.record.structure_key
    # exact bytes restored (no reprojection on load) and still a valid versor
    post_versor = rebooted.vault._versors[got[0].vault_index]
    assert post_versor.tobytes() == pre_versor_bytes
    assert versor_condition(post_versor) < 1e-6


def test_binding_graph_record_not_admitted_as_evidence(vocab_persona) -> None:
    # SPECULATIVE: a realized arithmetic fact is a candidate, not evidence.
    ctx = _ctx(vocab_persona)
    res = _realize(_FACT, ctx)
    assert isinstance(res, Realized)
    query = ctx.vault._versors[res.record.vault_index]
    coherent = ctx.vault.recall(query, top_k=5, min_status=EpistemicStatus.COHERENT)
    assert not any(h["metadata"].get("kind") == "realized" for h in coherent)
