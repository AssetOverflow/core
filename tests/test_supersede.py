"""ADR-0057 follow-up — operator-driven supersession.

Pins:

  - ``supersede_chain`` is the only path that emits a chain with a
    ``superseded_by`` field.
  - Single write surface preserved: it composes around
    ``proposals.append_chain_to_corpus``, not its own writer.
  - Pack-consistency, intent whitelist, and self-supersede gates
    fire before any byte is written.
  - Already-superseded targets cannot be double-retired.
  - Post-audit shifts exactly one chain from active → dropped and
    adds the replacement to active.
  - Failure modes leave the corpus byte-identical.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from teaching.audit import audit_corpus
from teaching.supersede import SupersessionError, supersede_chain


def _seed(tmp_path: Path) -> Path:
    """Two pack-consistent active chains; we'll retire the first."""
    p = tmp_path / "cognition_chains_v1.jsonl"
    lines = [
        json.dumps({
            "chain_id": "cause_light_reveals_truth",
            "subject": "light", "intent": "cause", "connective": "reveals",
            "object": "truth",
            "provenance": "adr-test:hand_authored:2026-05-18",
        }),
        json.dumps({
            "chain_id": "verification_memory_requires_recall",
            "subject": "memory", "intent": "verification", "connective": "requires",
            "object": "recall",
            "provenance": "adr-test:hand_authored:2026-05-18",
        }),
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_supersede_appends_one_line_and_retires_target(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    pre_lines = corpus.read_text(encoding="utf-8").splitlines()
    new_id = supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    assert new_id == "cause_light_grounds_truth"

    post_lines = corpus.read_text(encoding="utf-8").splitlines()
    assert len(post_lines) == len(pre_lines) + 1
    # Earlier lines are byte-identical (append-only at disk level).
    assert post_lines[: len(pre_lines)] == pre_lines

    last = json.loads(post_lines[-1])
    assert last["chain_id"] == "cause_light_grounds_truth"
    assert last["superseded_by"] == "cause_light_reveals_truth"
    assert "supersede(cause_light_reveals_truth)" in last["provenance"]


def test_audit_after_supersede_shifts_active_set(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    report = audit_corpus(corpus)
    active_ids = {c.chain_id for c in report.loaded}
    dropped_ids = {d.chain_id for d in report.dropped}
    assert "cause_light_reveals_truth" not in active_ids
    assert "cause_light_reveals_truth" in dropped_ids
    assert "cause_light_grounds_truth" in active_ids
    # Unrelated chain untouched.
    assert "verification_memory_requires_recall" in active_ids


def test_explicit_new_chain_id_honoured(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    new_id = supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
        new_chain_id="cause_light_revised_v2",
    )
    assert new_id == "cause_light_revised_v2"


# ---------------------------------------------------------------------------
# Eligibility / validation gates
# ---------------------------------------------------------------------------


def test_rejects_unknown_old_chain_id(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    bytes_before = corpus.read_bytes()
    with pytest.raises(SupersessionError, match="not in the active corpus"):
        supersede_chain(
            old_chain_id="does_not_exist",
            subject="light", intent="cause",
            connective="grounds", object_="truth",
            review_date="2026-05-18",
            corpus_path=corpus,
        )
    assert corpus.read_bytes() == bytes_before


def test_rejects_double_supersede(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    bytes_after_first = corpus.read_bytes()
    with pytest.raises(SupersessionError, match="already inactive"):
        supersede_chain(
            old_chain_id="cause_light_reveals_truth",
            subject="light", intent="cause",
            connective="orders", object_="truth",
            review_date="2026-05-18",
            corpus_path=corpus,
        )
    assert corpus.read_bytes() == bytes_after_first


def test_rejects_pack_missing_subject(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    bytes_before = corpus.read_bytes()
    with pytest.raises(SupersessionError):
        supersede_chain(
            old_chain_id="cause_light_reveals_truth",
            subject="zzznotalemma", intent="cause",
            connective="grounds", object_="truth",
            review_date="2026-05-18",
            corpus_path=corpus,
        )
    assert corpus.read_bytes() == bytes_before


def test_rejects_unsupported_intent(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    bytes_before = corpus.read_bytes()
    with pytest.raises(SupersessionError, match="whitelist"):
        supersede_chain(
            old_chain_id="cause_light_reveals_truth",
            subject="light", intent="definition",
            connective="grounds", object_="truth",
            review_date="2026-05-18",
            corpus_path=corpus,
        )
    assert corpus.read_bytes() == bytes_before


def test_rejects_self_supersede(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    bytes_before = corpus.read_bytes()
    with pytest.raises(SupersessionError, match="identical"):
        supersede_chain(
            old_chain_id="cause_light_reveals_truth",
            subject="light", intent="cause",
            connective="reveals", object_="truth",
            review_date="2026-05-18",
            corpus_path=corpus,
        )
    assert corpus.read_bytes() == bytes_before


def test_rejects_collision_with_active_chain_id(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    bytes_before = corpus.read_bytes()
    with pytest.raises(SupersessionError, match="already active"):
        supersede_chain(
            old_chain_id="cause_light_reveals_truth",
            subject="memory", intent="verification",
            connective="requires", object_="recall",
            review_date="2026-05-18",
            corpus_path=corpus,
        )
    assert corpus.read_bytes() == bytes_before


def test_rejects_bad_review_date(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    bytes_before = corpus.read_bytes()
    with pytest.raises(SupersessionError, match="YYYY-MM-DD"):
        supersede_chain(
            old_chain_id="cause_light_reveals_truth",
            subject="light", intent="cause",
            connective="grounds", object_="truth",
            review_date="May 18 2026",
            corpus_path=corpus,
        )
    assert corpus.read_bytes() == bytes_before


def test_rejects_empty_required_field(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    bytes_before = corpus.read_bytes()
    with pytest.raises(SupersessionError, match="required"):
        supersede_chain(
            old_chain_id="cause_light_reveals_truth",
            subject="light", intent="cause",
            connective="  ", object_="truth",
            review_date="2026-05-18",
            corpus_path=corpus,
        )
    assert corpus.read_bytes() == bytes_before


# ---------------------------------------------------------------------------
# Runtime parity
# ---------------------------------------------------------------------------


def test_runtime_loader_honours_supersede_chain_output(tmp_path: Path) -> None:
    """After supersede_chain runs, the live runtime loader (pointed
    at this tmp corpus) sees the same active set as the audit report."""
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    from unittest.mock import patch

    from chat import teaching_grounding as tg

    with patch.object(tg, "_CORPUS_PATH", corpus):
        tg._corpus_index.cache_clear()
        try:
            index = tg._corpus_index()
            runtime_ids = {c.chain_id for c in index.values()}
        finally:
            tg._corpus_index.cache_clear()

    audit_ids = {c.chain_id for c in audit_corpus(corpus).loaded}
    assert runtime_ids == audit_ids
    assert "cause_light_reveals_truth" not in runtime_ids
    assert "cause_light_grounds_truth" in runtime_ids


# ---------------------------------------------------------------------------
# Provenance shape
# ---------------------------------------------------------------------------


def test_provenance_is_hand_authored_with_supersede_tag(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    report = audit_corpus(corpus)
    new_entry = next(
        c for c in report.loaded if c.chain_id == "cause_light_grounds_truth"
    )
    assert new_entry.provenance.source == "hand_authored"
    assert new_entry.provenance.review_date is not None
    assert new_entry.provenance.review_date.startswith("2026-05-18")
    assert "supersede(cause_light_reveals_truth)" in new_entry.provenance.raw
