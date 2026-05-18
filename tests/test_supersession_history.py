"""Supersession history view over the audit report.

Pins:

  - Pure derived view; no corpus mutation.
  - Deterministic order (retired-line ascending).
  - Each retired→replacement pair is surfaced; orphans
    (retired with no matching live ``superseded_by``) are flagged
    with ``replacement=None`` instead of being silently dropped.
  - Chained supersessions (A retired by B, B retired by C) surface
    both pairs.
"""

from __future__ import annotations

import json
from pathlib import Path

from teaching.audit import audit_corpus, supersession_history
from teaching.supersede import supersede_chain


def _seed(tmp_path: Path) -> Path:
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


def test_empty_history_on_clean_corpus(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    report = audit_corpus(corpus)
    assert supersession_history(report) == ()


def test_history_pairs_retired_with_replacement(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    report = audit_corpus(corpus)
    records = supersession_history(report)
    assert len(records) == 1
    r = records[0]
    assert r.retired_chain_id == "cause_light_reveals_truth"
    assert r.replacement is not None
    assert r.replacement.chain_id == "cause_light_grounds_truth"
    assert r.replacement.connective == "grounds"
    assert "supersede(cause_light_reveals_truth)" in r.replacement.provenance.raw


def test_chained_supersession_surfaces_both_pairs(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    supersede_chain(
        old_chain_id="cause_light_grounds_truth",
        subject="light", intent="cause",
        connective="orders", object_="truth",
        review_date="2026-05-19",
        corpus_path=corpus,
    )
    report = audit_corpus(corpus)
    records = supersession_history(report)
    retired_ids = [r.retired_chain_id for r in records]
    assert "cause_light_reveals_truth" in retired_ids
    assert "cause_light_grounds_truth" in retired_ids
    # Latest replacement is the only thing still active for (light, cause).
    by_retired = {r.retired_chain_id: r for r in records}
    final = by_retired["cause_light_grounds_truth"].replacement
    assert final is not None
    assert final.chain_id == "cause_light_orders_truth"


def test_records_sorted_by_retired_line_no(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    supersede_chain(
        old_chain_id="verification_memory_requires_recall",
        subject="memory", intent="verification",
        connective="grounds", object_="recall",
        review_date="2026-05-19",
        corpus_path=corpus,
    )
    report = audit_corpus(corpus)
    records = supersession_history(report)
    line_nos = [r.retired_line_no for r in records]
    assert line_nos == sorted(line_nos)


def test_orphan_supersession_surfaces_replacement_none(tmp_path: Path) -> None:
    """A corpus where a chain claims supersession but the retiring entry
    itself is later retired by something with a different ``superseded_by``."""
    p = tmp_path / "cognition_chains_v1.jsonl"
    # B retires A.  C retires B (so B drops too).  C carries
    # superseded_by=B only — A is now an orphan: dropped (because B
    # said so) but no live entry carries superseded_by=A.
    lines = [
        json.dumps({
            "chain_id": "cause_light_reveals_truth",
            "subject": "light", "intent": "cause", "connective": "reveals",
            "object": "truth",
            "provenance": "adr-test:hand_authored:2026-05-18",
        }),
        json.dumps({
            "chain_id": "cause_light_grounds_truth",
            "subject": "light", "intent": "cause", "connective": "grounds",
            "object": "truth",
            "provenance": "adr-test:hand_authored:2026-05-18",
            "superseded_by": "cause_light_reveals_truth",
        }),
        json.dumps({
            "chain_id": "cause_light_orders_truth",
            "subject": "light", "intent": "cause", "connective": "orders",
            "object": "truth",
            "provenance": "adr-test:hand_authored:2026-05-19",
            "superseded_by": "cause_light_grounds_truth",
        }),
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = audit_corpus(p)
    records = supersession_history(report)
    by_retired = {r.retired_chain_id: r for r in records}
    # A is dropped (B's superseded_by points at it), but no LIVE entry
    # carries superseded_by=A — B itself was retired.  Orphan.
    assert by_retired["cause_light_reveals_truth"].replacement is None
    # B has a live replacement: C.
    rep_b = by_retired["cause_light_grounds_truth"].replacement
    assert rep_b is not None
    assert rep_b.chain_id == "cause_light_orders_truth"


def test_as_dict_round_trips_through_json(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    report = audit_corpus(corpus)
    records = supersession_history(report)
    blob = json.dumps([r.as_dict() for r in records], sort_keys=True)
    assert "cause_light_reveals_truth" in blob
    assert "cause_light_grounds_truth" in blob


def test_pure_function_no_corpus_mutation(tmp_path: Path) -> None:
    corpus = _seed(tmp_path)
    supersede_chain(
        old_chain_id="cause_light_reveals_truth",
        subject="light", intent="cause",
        connective="grounds", object_="truth",
        review_date="2026-05-18",
        corpus_path=corpus,
    )
    bytes_before = corpus.read_bytes()
    report = audit_corpus(corpus)
    supersession_history(report)
    supersession_history(report)
    assert corpus.read_bytes() == bytes_before
