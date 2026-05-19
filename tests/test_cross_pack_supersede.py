"""ADR-0067 follow-up — cross-pack supersession tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from teaching.cross_pack_supersede import supersede_cross_pack_chain
from teaching.supersede import SupersessionError


@pytest.fixture
def cross_pack_corpus(tmp_path, monkeypatch) -> Path:
    """A fresh copy of the production cross-pack corpus we can mutate."""
    import chat.cross_pack_grounding as mod
    src_bytes = mod._CORPUS_PATH.read_bytes()
    target = tmp_path / "cp.jsonl"
    target.write_bytes(src_bytes)
    monkeypatch.setattr(mod, "_CORPUS_PATH", target)
    mod.clear_cross_pack_cache()
    try:
        yield target
    finally:
        mod.clear_cross_pack_cache()


def test_supersede_appends_new_active_and_retires_old(cross_pack_corpus) -> None:
    new_id = supersede_cross_pack_chain(
        old_chain_id="cause_family_grounds_identity",
        subject="family",
        intent="cause",
        connective="precedes",
        object_="identity",
        subject_pack_id="en_core_relations_v1",
        object_pack_id="en_core_cognition_v1",
        review_date="2026-05-18",
        corpus_path=cross_pack_corpus,
    )
    assert new_id == "cause_family_precedes_identity"
    last = json.loads(cross_pack_corpus.read_text().splitlines()[-1])
    assert last["chain_id"] == new_id
    assert last["superseded_by"] == "cause_family_grounds_identity"
    assert last["subject_pack_id"] == "en_core_relations_v1"
    assert last["object_pack_id"] == "en_core_cognition_v1"


def test_supersede_rejects_same_pack(cross_pack_corpus) -> None:
    with pytest.raises(SupersessionError, match="must differ"):
        supersede_cross_pack_chain(
            old_chain_id="cause_family_grounds_identity",
            subject="family",
            intent="cause",
            connective="precedes",
            object_="identity",
            subject_pack_id="en_core_relations_v1",
            object_pack_id="en_core_relations_v1",
            review_date="2026-05-18",
            corpus_path=cross_pack_corpus,
        )


def test_supersede_rejects_lemma_outside_declared_pack(cross_pack_corpus) -> None:
    with pytest.raises(SupersessionError, match="not resident"):
        supersede_cross_pack_chain(
            old_chain_id="cause_family_grounds_identity",
            subject="family",
            intent="cause",
            connective="precedes",
            object_="identity",
            # WRONG: family is in relations, not cognition
            subject_pack_id="en_core_cognition_v1",
            object_pack_id="en_core_relations_v1",
            review_date="2026-05-18",
            corpus_path=cross_pack_corpus,
        )


def test_supersede_rejects_unknown_old_chain_id(cross_pack_corpus) -> None:
    with pytest.raises(SupersessionError, match="not active"):
        supersede_cross_pack_chain(
            old_chain_id="nonexistent_chain_id",
            subject="family",
            intent="cause",
            connective="grounds",
            object_="identity",
            subject_pack_id="en_core_relations_v1",
            object_pack_id="en_core_cognition_v1",
            review_date="2026-05-18",
            corpus_path=cross_pack_corpus,
        )


def test_supersede_rejects_invalid_review_date(cross_pack_corpus) -> None:
    with pytest.raises(SupersessionError, match="review_date"):
        supersede_cross_pack_chain(
            old_chain_id="cause_family_grounds_identity",
            subject="family", intent="cause", connective="precedes",
            object_="identity",
            subject_pack_id="en_core_relations_v1",
            object_pack_id="en_core_cognition_v1",
            review_date="2026/05/18",  # wrong format
            corpus_path=cross_pack_corpus,
        )


def test_supersede_rejects_invalid_intent(cross_pack_corpus) -> None:
    with pytest.raises(SupersessionError, match="whitelist"):
        supersede_cross_pack_chain(
            old_chain_id="cause_family_grounds_identity",
            subject="family", intent="definition", connective="precedes",
            object_="identity",
            subject_pack_id="en_core_relations_v1",
            object_pack_id="en_core_cognition_v1",
            review_date="2026-05-18",
            corpus_path=cross_pack_corpus,
        )


def test_supersede_rejects_self_supersede(cross_pack_corpus) -> None:
    with pytest.raises(SupersessionError, match="identical"):
        supersede_cross_pack_chain(
            old_chain_id="cause_family_grounds_identity",
            subject="family", intent="cause", connective="grounds",
            object_="identity",
            subject_pack_id="en_core_relations_v1",
            object_pack_id="en_core_cognition_v1",
            review_date="2026-05-18",
            corpus_path=cross_pack_corpus,
            # ⇒ new id resolves to same as old
        )


def test_supersede_byte_identical_on_failure(cross_pack_corpus) -> None:
    before = cross_pack_corpus.read_bytes()
    with pytest.raises(SupersessionError):
        supersede_cross_pack_chain(
            old_chain_id="nonexistent",
            subject="family", intent="cause", connective="precedes",
            object_="identity",
            subject_pack_id="en_core_relations_v1",
            object_pack_id="en_core_cognition_v1",
            review_date="2026-05-18",
            corpus_path=cross_pack_corpus,
        )
    assert cross_pack_corpus.read_bytes() == before


def test_supersede_drops_retired_from_active_index(cross_pack_corpus) -> None:
    supersede_cross_pack_chain(
        old_chain_id="cause_family_grounds_identity",
        subject="family", intent="cause", connective="precedes",
        object_="identity",
        subject_pack_id="en_core_relations_v1",
        object_pack_id="en_core_cognition_v1",
        review_date="2026-05-18",
        corpus_path=cross_pack_corpus,
    )
    from chat.cross_pack_grounding import _all_cross_pack_chains
    active_ids = {c.chain_id for c in _all_cross_pack_chains()}
    assert "cause_family_grounds_identity" not in active_ids
    assert "cause_family_precedes_identity" in active_ids
