"""REALIZE slice R1 — structural identity & recall.

The R0 store keys a realized fact by its subject's FIELD versor. That versor is
not an injective identity: two facts about the same subject embed to the
*byte-identical* versor, so metric recall returns both at score ``inf`` and
cannot tell them apart (proven by ``test_metric_recall_collides_on_same_subject``).

R1 adds the missing key: a realized fact carries its ordered
``relation_arguments`` and a span-free ``structure_key``, and
``recall_realized`` retrieves facts by their EXACT structural metadata
(subject / predicate / content_hash / structure_key) — exact and deterministic,
no metric, no vault mutation. Span-free idempotency dedups the same proposition
told from a different source/offset (which R0's span-inclusive content_hash
missed).
"""

from __future__ import annotations

import pytest

from algebra.versor import versor_condition
from chat.runtime import ChatRuntime
from generate.meaning_graph.reader import comprehend
from generate.realize import (
    NotRealized,
    Realized,
    RealizedRecord,
    realize_comprehension,
    recall_realized,
)
from session.context import SessionContext

_HIGH_INTERVAL = 10**9  # never auto-reproject in these tests


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)


def _realize(text: str, ctx: SessionContext, source_id: str = "input"):
    return realize_comprehension(comprehend(text, source_id=source_id), ctx)


# --------------------------------------------------------------------------- #
# The problem: the field versor is NOT an injective key (collision is real)
# --------------------------------------------------------------------------- #


def test_metric_recall_collides_on_same_subject(vocab_persona) -> None:
    """Two distinct facts about the same subject store at the byte-identical
    versor, so metric recall returns both at ``inf`` — structurally blind.
    This is the falsifiable justification for structural recall."""
    ctx = _ctx(vocab_persona)
    a = _realize("Truth is a concept.", ctx)
    b = _realize("Truth is a thought.", ctx)
    assert isinstance(a, Realized) and isinstance(b, Realized)
    assert a.record.content_hash != b.record.content_hash  # genuinely distinct facts
    # byte-identical stored versors -> the metric cannot separate them
    assert ctx.vault._versors[0].tobytes() == ctx.vault._versors[1].tobytes()
    hits = ctx.vault.recall(ctx.probe_ingest(["truth"]).F, top_k=5)
    realized = [h for h in hits if h["metadata"].get("kind") == "realized"]
    assert len(realized) == 2
    assert all(h["score"] == float("inf") for h in realized)  # both collide at inf


# --------------------------------------------------------------------------- #
# Structural recall — exact metadata match, deterministic, distinct
# --------------------------------------------------------------------------- #


def test_structural_recall_by_subject_returns_all_same_subject_facts(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _realize("Truth is a concept.", ctx)
    _realize("Truth is a thought.", ctx)
    _realize("Knowledge is a concept.", ctx)  # different subject
    got = recall_realized(ctx, subject="truth")
    assert all(isinstance(r, RealizedRecord) for r in got)
    assert len(got) == 2  # both truth facts, NOT the knowledge fact
    hashes = {r.content_hash for r in got}
    assert len(hashes) == 2  # distinctly recalled
    assert all(r.relation_arguments[0] == "truth" for r in got)


def test_structural_recall_by_content_hash_disambiguates(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    a = _realize("Truth is a concept.", ctx)
    _realize("Truth is a thought.", ctx)
    assert isinstance(a, Realized)
    got = recall_realized(ctx, content_hash=a.record.content_hash)
    assert len(got) == 1
    assert got[0].content_hash == a.record.content_hash
    assert "concept" in got[0].entity_names


def test_structural_recall_by_predicate(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _realize("Truth is a concept.", ctx)
    _realize("Truth is a thought.", ctx)
    assert len(recall_realized(ctx, predicate="member")) == 2
    assert recall_realized(ctx, predicate="no_such_predicate") == ()


def test_structural_recall_conjoins_filters(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _realize("Truth is a concept.", ctx)
    _realize("Truth is a thought.", ctx)
    _realize("Knowledge is a concept.", ctx)
    got = recall_realized(ctx, subject="truth", predicate="member")
    assert len(got) == 2
    assert recall_realized(ctx, subject="knowledge", predicate="member")[0].relation_arguments == (
        "knowledge",
        "concept",
    )


def test_structural_recall_empty_on_no_match(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _realize("Truth is a concept.", ctx)
    assert recall_realized(ctx, subject="nonexistent") == ()
    assert recall_realized(ctx) == recall_realized(ctx, subject=None)  # no filter -> all realized


def test_structural_recall_survives_reboot(vocab_persona) -> None:
    vocab, persona = vocab_persona
    ctx = _ctx(vocab_persona)
    a = _realize("Truth is a concept.", ctx)
    assert isinstance(a, Realized)
    rebooted = SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)
    rebooted.restore(ctx.snapshot())
    got = recall_realized(rebooted, subject="truth")
    assert len(got) == 1
    assert got[0].content_hash == a.record.content_hash
    assert got[0].relation_arguments == ("truth", "concept")
    # field versor still valid after the round trip (recall is structural, but the
    # stored placement must remain a versor)
    v = rebooted.vault._versors[got[0].vault_index]
    assert versor_condition(v) < 1e-6


def test_record_carries_ordered_relation_arguments(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    a = _realize("Truth is a concept.", ctx)
    assert isinstance(a, Realized)
    # ordered (subject, object) — NOT the sorted entity_names
    assert a.record.relation_arguments == ("truth", "concept")
    assert a.record.entity_names == ("concept", "truth")  # sorted, unchanged from R0


# --------------------------------------------------------------------------- #
# Span-free idempotency — the same proposition from a different source dedups
# --------------------------------------------------------------------------- #


def test_structure_key_is_span_free_but_content_hash_is_not(vocab_persona) -> None:
    a_ctx = _ctx(vocab_persona)
    b_ctx = _ctx(vocab_persona)
    ra = _realize("Truth is a concept.", a_ctx, source_id="docA")
    rb = _realize("Truth is a concept.", b_ctx, source_id="docB")
    assert isinstance(ra, Realized) and isinstance(rb, Realized)
    # same proposition, different provenance:
    assert ra.record.structure_key == rb.record.structure_key  # span/source-free
    assert ra.record.content_hash != rb.record.content_hash  # span-INCLUSIVE differs


def test_span_free_idempotency_dedups_across_source(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    first = _realize("Truth is a concept.", ctx, source_id="docA")
    second = _realize("Truth is a concept.", ctx, source_id="docB")
    assert isinstance(first, Realized) and first.created is True
    # R0's content_hash dedup would MISS this (different span -> different hash);
    # the span-free structure_key catches it.
    assert isinstance(second, Realized) and second.created is False
    assert len(ctx.vault._metadata) == 1


def test_distinct_facts_not_collapsed_by_structure_key(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    _realize("Truth is a concept.", ctx)
    _realize("Truth is a thought.", ctx)  # same subject+predicate, different object
    assert len(ctx.vault._metadata) == 2  # NOT collapsed
    keys = {m["structure_key"] for m in ctx.vault._metadata}
    assert len(keys) == 2


def test_ineligible_input_still_realizes_nothing(vocab_persona) -> None:
    # R1 does not loosen R0's wrong=0 floor.
    ctx = _ctx(vocab_persona)
    assert isinstance(_realize("Is truth a concept?", ctx), NotRealized)
    assert isinstance(_realize("The weather is nice today.", ctx), NotRealized)
    assert len(ctx.vault._metadata) == 0


def test_duplicate_entity_names_refused(vocab_persona) -> None:
    """wrong=0 defense: the model permits distinct entity_ids to share a NAME.
    A name-keyed structure_key would collapse a converse/homonym fact onto an
    existing one (dropping a distinct proposition), so realize refuses the
    ambiguous graph rather than risk the silent drop. Latent in today's reader
    (entity_id == name), but proven to bite via a hand-built graph."""
    from generate.meaning_graph.model import Entity, MeaningGraph, MeaningSpan, Relation
    from generate.meaning_graph.reader import Comprehension

    span = MeaningSpan(source_id="input", start=0, end=10, text="dup vs dup")
    graph = MeaningGraph(
        entities=(
            Entity(entity_id="dup_1", name="dup", span=span),
            Entity(entity_id="dup_2", name="dup", span=span),
        ),
        relations=(Relation(predicate="member", arguments=("dup_1", "dup_2"), span=span),),
    )
    ctx = _ctx(vocab_persona)
    res = realize_comprehension(Comprehension(meaning_graph=graph, queries=()), ctx)
    assert isinstance(res, NotRealized) and res.reason == "ambiguous_entity_names"
    assert len(ctx.vault._metadata) == 0
