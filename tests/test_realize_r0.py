"""REALIZE slice R0 — one told fact survives reboot and recalls exactly, SPECULATIVE.

The load-bearing exit gate (test_r0_exit_gate_*) is falsifiable: it FAILS if REALIZE
is decoration (a Refusal that silently writes, a COHERENT default, a missing
provenance span, a reprojection mutating the versor on load, or a non-deterministic
placement). The other tests pin eligibility, idempotency, and the SPECULATIVE
status firewall (remembered != evidence).
"""

from __future__ import annotations

import pytest

from algebra.versor import versor_condition
from chat.runtime import ChatRuntime
from generate.meaning_graph.reader import comprehend
from generate.realize import NotRealized, Realized, realize_comprehension
from session.context import SessionContext
from teaching.epistemic import EpistemicStatus

_HIGH_INTERVAL = 10**9  # never auto-reproject in R0 tests (adjustment: reproject boundary)


@pytest.fixture(scope="module")
def vocab_persona():
    rt = ChatRuntime(no_load_state=True)
    return rt._context.vocab, rt._context.persona


def _ctx(vocab_persona) -> SessionContext:
    vocab, persona = vocab_persona
    return SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)


def _realize(text: str, ctx: SessionContext):
    return realize_comprehension(comprehend(text), ctx)


# --------------------------------------------------------------------------- #
# Eligibility — wrong=0: ineligible input realizes NOTHING (no vault write)
# --------------------------------------------------------------------------- #


def test_refusal_realizes_nothing(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _realize("The weather is nice today.", ctx)  # comprehend -> Refusal
    assert isinstance(res, NotRealized) and res.reason == "refusal"
    assert len(ctx.vault._metadata) == 0  # no vault write


def test_query_bearing_realizes_nothing(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _realize("Is truth a concept?", ctx)  # a question is recall, not intake
    assert isinstance(res, NotRealized) and res.reason == "query_bearing"
    assert len(ctx.vault._metadata) == 0


def test_multi_relation_realizes_nothing(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _realize("Truth is a concept. Knowledge is a thought.", ctx)
    assert isinstance(res, NotRealized) and res.reason == "not_single_relation"
    assert len(ctx.vault._metadata) == 0


def test_oov_subject_is_realized(vocab_persona) -> None:
    # The in-vocab gate is LIFTED: OOV grounding is deterministic, reboot-stable, and
    # injective (#591), and correctness rests on the structural key (not the versor),
    # so an OOV subject realizes a normal SPECULATIVE record.
    ctx = _ctx(vocab_persona)
    res = _realize("Rhea is a raven.", ctx)
    assert isinstance(res, Realized) and res.created is True
    assert res.record.relation_arguments[0] == "rhea"
    assert res.record.epistemic_status == "speculative"
    assert len(ctx.vault._metadata) == 1


def test_single_in_vocab_declarative_is_realized(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _realize("Truth is a concept.", ctx)
    assert isinstance(res, Realized) and res.created is True
    r = res.record
    assert r.structure_kind == "meaning_graph"
    assert r.relation_predicate == "member"
    assert r.epistemic_status == "speculative"  # never COHERENT by default
    assert r.tier == "session"
    assert r.source_span  # provenance present
    assert r.content_hash and r.replay_hash
    assert "truth" in r.entity_names and "concept" in r.entity_names
    assert len(ctx.vault._metadata) == 1


# --------------------------------------------------------------------------- #
# Idempotency — a re-told fact does not grow the vault (dedup by structure_key)
# --------------------------------------------------------------------------- #


def test_retold_fact_is_idempotent(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    first = _realize("Truth is a concept.", ctx)
    second = _realize("Truth is a concept.", ctx)
    assert isinstance(first, Realized) and first.created is True
    assert isinstance(second, Realized) and second.created is False  # dedup hit
    # dedup is on the span-free structure_key (content_hash coincides only because the
    # surface is identical here); name the actual dedup key.
    assert second.record.structure_key == first.record.structure_key
    assert second.record.content_hash == first.record.content_hash
    assert len(ctx.vault._metadata) == 1  # NOT grown


def test_negated_relation_realizes_nothing(vocab_persona) -> None:
    # The reader encodes declarative negation in the PREDICATE (some_not/disjoint), so
    # rel.negated=True is reachable only via a hand-built graph — but the defensive
    # refusal must bite: a negated relation ("X is NOT a Y") must never be realized as
    # a positive fact.
    from generate.meaning_graph.model import Entity, MeaningGraph, MeaningSpan, Relation
    from generate.meaning_graph.reader import Comprehension

    span = MeaningSpan(source_id="input", start=0, end=18, text="truth not concept")
    graph = MeaningGraph(
        entities=(
            Entity(entity_id="truth", name="truth", span=span),
            Entity(entity_id="concept", name="concept", span=span),
        ),
        relations=(Relation(predicate="member", arguments=("truth", "concept"), span=span, negated=True),),
    )
    ctx = _ctx(vocab_persona)
    res = realize_comprehension(Comprehension(meaning_graph=graph, queries=()), ctx)
    assert isinstance(res, NotRealized) and res.reason == "negated_relation"
    assert len(ctx.vault._metadata) == 0


# --------------------------------------------------------------------------- #
# Status firewall — SPECULATIVE is candidate memory, NOT evidence
# --------------------------------------------------------------------------- #


def test_speculative_record_is_not_admitted_as_evidence(vocab_persona) -> None:
    ctx = _ctx(vocab_persona)
    res = _realize("Truth is a concept.", ctx)
    assert isinstance(res, Realized)
    query = ctx.probe_ingest(["truth"]).F
    # default recall surfaces it as a CANDIDATE...
    default_hits = ctx.vault.recall(query, top_k=5)
    assert any(h["metadata"].get("kind") == "realized" for h in default_hits)
    # ...but min_status=COHERENT must NOT return it (remembered != evidence).
    coherent_hits = ctx.vault.recall(query, top_k=5, min_status=EpistemicStatus.COHERENT)
    assert not any(h["metadata"].get("kind") == "realized" for h in coherent_hits)


# --------------------------------------------------------------------------- #
# Exit gate — told -> realize -> snapshot -> reboot -> recall, byte-exact
# --------------------------------------------------------------------------- #


def test_r0_exit_gate_survives_reboot_and_recalls_exactly(vocab_persona) -> None:
    vocab, persona = vocab_persona
    ctx = _ctx(vocab_persona)

    res = _realize("Truth is a concept.", ctx)
    assert isinstance(res, Realized) and res.created
    pre_query = ctx.probe_ingest(["truth"]).F
    pre_hits = ctx.vault.recall(pre_query, top_k=5)
    pre = next(h for h in pre_hits if h["metadata"].get("kind") == "realized")
    pre_score = pre["score"]
    pre_content_hash = pre["metadata"]["content_hash"]
    pre_versor_bytes = pre["versor"].tobytes()

    # reboot: snapshot -> NEW context -> restore (no reprojection on load)
    snap = ctx.snapshot()
    rebooted = SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)
    rebooted.restore(snap)

    post_query = rebooted.probe_ingest(["truth"]).F
    post_hits = rebooted.vault.recall(post_query, top_k=5)
    post = next(h for h in post_hits if h["metadata"].get("kind") == "realized")

    # content_hash byte-identical, recall score byte-identical (exact f32 restore)
    assert post["metadata"]["content_hash"] == pre_content_hash
    assert post["score"] == pre_score
    assert post["metadata"]["epistemic_status"] == "speculative"
    # the restored versor is byte-identical (DIRECT catch of any reprojection/
    # normalization on load) and still a valid versor.
    assert post["versor"].tobytes() == pre_versor_bytes
    assert versor_condition(post["versor"]) < 1e-6
    # provenance survived the reboot
    assert post["metadata"]["source_span"]


def test_r0_replay_hash_is_rederivable_after_reboot(vocab_persona) -> None:
    # The replay_hash is the determinism anchor: re-deriving it from the RESTORED
    # metadata must reproduce the stored value byte-for-byte (closes the obligation
    # that replay_hash is a real replay proof, not just asserted structure).
    from formation.hashing import sha256_of

    vocab, persona = vocab_persona
    ctx = _ctx(vocab_persona)
    assert isinstance(_realize("Truth is a concept.", ctx), Realized)

    rebooted = SessionContext(vocab=vocab, persona=persona, vault_reproject_interval=_HIGH_INTERVAL)
    rebooted.restore(ctx.snapshot())
    meta = next(m for m in rebooted.vault._metadata if m.get("kind") == "realized")
    rederived = sha256_of(
        {
            "content_hash": meta["content_hash"],
            "source_span": meta["source_span"],
            "epistemic_status": meta["epistemic_status"],
        }
    )
    assert rederived == meta["replay_hash"]


def test_r0_placement_is_deterministic_across_fresh_contexts(vocab_persona) -> None:
    # Realizing the SAME fact in two independent fresh contexts (same vocab) yields
    # the identical content_hash AND identical stored versor bytes — guards
    # idempotency + placement determinism (in-vocab subject).
    a = _ctx(vocab_persona)
    b = _ctx(vocab_persona)
    ra = _realize("Truth is a concept.", a)
    rb = _realize("Truth is a concept.", b)
    assert isinstance(ra, Realized) and isinstance(rb, Realized)
    assert ra.record.content_hash == rb.record.content_hash
    va = a.vault.recall(a.probe_ingest(["truth"]).F, top_k=1)[0]["versor"]
    vb = b.vault.recall(b.probe_ingest(["truth"]).F, top_k=1)[0]["versor"]
    assert va.tobytes() == vb.tobytes()
