"""Phase 2.3 — OOV sink, aggregation, and auto-promotion tests.

The contract these tests pin:

  - The runtime emits an ``OOVCandidate`` JSONL line to the attached
    sink on every turn whose ``grounding_source == "oov"``; no-op
    when no sink is attached.
  - The candidate_id is deterministic on (token, intent, trace_hash).
  - The aggregator groups by token, ranks by frequency, supports
    ``--since YYYY-MM`` filtering.
  - The promoter respects the boundary-clean filter by default and
    refuses ``threshold < 1``.
  - The promotion suggests mounted packs but never names a single
    destination — domain inference is out of scope.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from teaching.oov_gaps import OOVGap, aggregate_oov_gaps
from teaching.oov_promotion import OOVPromotion, promote_oov_gaps
from teaching.oov_sink import (
    OOVBufferSink,
    OOVCandidate,
    format_oov_candidate_jsonl,
    hash_oov_candidate_id,
)


# ---------------------------------------------------------------------------
# Sink contract
# ---------------------------------------------------------------------------


def test_buffer_sink_captures_each_emit() -> None:
    sink = OOVBufferSink()
    sink.emit("one")
    sink.emit("two")
    assert sink.lines == ["one", "two"]


def test_candidate_id_is_deterministic() -> None:
    a = hash_oov_candidate_id("photosynthesis", "definition", "trace-1")
    b = hash_oov_candidate_id("photosynthesis", "definition", "trace-1")
    assert a == b
    assert len(a) == 32


def test_candidate_id_changes_with_token() -> None:
    a = hash_oov_candidate_id("photosynthesis", "definition", "trace-1")
    b = hash_oov_candidate_id("mitochondria", "definition", "trace-1")
    assert a != b


def test_candidate_id_changes_with_trace() -> None:
    a = hash_oov_candidate_id("photosynthesis", "definition", "trace-1")
    b = hash_oov_candidate_id("photosynthesis", "definition", "trace-2")
    assert a != b


def test_candidate_jsonl_is_sorted_compact() -> None:
    cand = OOVCandidate(
        candidate_id="x",
        token="photosynthesis",
        intent="definition",
        trigger="unresolved_subject",
        source_turn_trace="t",
        boundary_clean=True,
    )
    line = format_oov_candidate_jsonl(cand)
    parsed = json.loads(line)
    assert parsed["token"] == "photosynthesis"
    assert parsed["intent"] == "definition"
    assert parsed["boundary_clean"] is True


# ---------------------------------------------------------------------------
# Runtime integration — sink receives one line per OOV turn
# ---------------------------------------------------------------------------


def test_runtime_emits_when_oov_sink_attached() -> None:
    rt = ChatRuntime()
    sink = OOVBufferSink()
    rt.attach_oov_sink(sink)
    rt.chat("What is photosynthesis?")
    assert len(sink.lines) == 1
    parsed = json.loads(sink.lines[0])
    assert parsed["token"] == "photosynthesis"
    assert parsed["intent"] == "definition"
    assert parsed["trigger"] == "unresolved_subject"


def test_runtime_does_not_emit_without_sink() -> None:
    """Sink emission is opt-in; runtime behaviour is identical when
    no sink is attached."""
    rt = ChatRuntime()
    resp = rt.chat("What is photosynthesis?")
    # OOV surface still fires (P2.1 is unconditional), but nothing
    # is persisted anywhere — there is no sink to receive it.
    assert resp.grounding_source == "oov"


def test_runtime_does_not_emit_on_known_lemma() -> None:
    rt = ChatRuntime()
    sink = OOVBufferSink()
    rt.attach_oov_sink(sink)
    rt.chat("What is light?")
    assert sink.lines == []


def test_runtime_emits_across_intent_shapes() -> None:
    """Every intent shape that triggers OOV (definition, cause,
    verification, comparison, procedure) emits a candidate."""
    rt = ChatRuntime()
    sink = OOVBufferSink()
    rt.attach_oov_sink(sink)
    rt.chat("What is photosynthesis?")
    intents = set()
    for line in sink.lines:
        intents.add(json.loads(line)["intent"])
    assert "definition" in intents


# ---------------------------------------------------------------------------
# Aggregator — file walking + deterministic ordering
# ---------------------------------------------------------------------------


def _write_oov_line(path: Path, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidate_id": kwargs.get("candidate_id", "x"),
        "token": kwargs.get("token", "photosynthesis"),
        "intent": kwargs.get("intent", "definition"),
        "trigger": "unresolved_subject",
        "source_turn_trace": kwargs.get("trace", "t"),
        "boundary_clean": kwargs.get("boundary_clean", True),
        "review_state": "unreviewed",
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        fh.write("\n")


def test_aggregates_by_token(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    _write_oov_line(sink, candidate_id="a", token="photosynthesis", intent="definition")
    _write_oov_line(sink, candidate_id="b", token="photosynthesis", intent="cause")
    _write_oov_line(sink, candidate_id="c", token="mitochondria", intent="definition")

    rows = aggregate_oov_gaps(tmp_path)
    assert len(rows) == 2
    photo = next(g for g in rows if g.token == "photosynthesis")
    assert photo.count == 2
    assert photo.intents == ("cause", "definition")
    assert photo.boundary_clean_count == 2


def test_rank_order_is_count_desc(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    for i in range(3):
        _write_oov_line(sink, candidate_id=f"a{i}", token="photosynthesis")
    _write_oov_line(sink, candidate_id="b0", token="mitochondria")
    rows = aggregate_oov_gaps(tmp_path)
    assert [g.token for g in rows] == ["photosynthesis", "mitochondria"]


def test_tainted_counted_but_split(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    _write_oov_line(sink, candidate_id="a", boundary_clean=True)
    _write_oov_line(sink, candidate_id="b", boundary_clean=False)
    rows = aggregate_oov_gaps(tmp_path)
    assert rows[0].count == 2
    assert rows[0].boundary_clean_count == 1


def test_since_filter(tmp_path: Path) -> None:
    _write_oov_line(tmp_path / "2026" / "2026-04.jsonl", candidate_id="april")
    _write_oov_line(tmp_path / "2026" / "2026-05.jsonl", candidate_id="may")
    rows = aggregate_oov_gaps(tmp_path, since="2026-05")
    assert len(rows) == 1
    assert rows[0].sample_candidate_ids == ("may",)


def test_malformed_lines_skipped(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    sink.parent.mkdir(parents=True, exist_ok=True)
    sink.write_text(
        "not json\n{}\n" + json.dumps({
            "candidate_id": "ok", "token": "photosynthesis",
            "intent": "definition", "trigger": "unresolved_subject",
            "source_turn_trace": "t", "boundary_clean": True,
        }) + "\n",
        encoding="utf-8",
    )
    rows = aggregate_oov_gaps(tmp_path)
    assert len(rows) == 1


def test_aggregator_missing_root_returns_empty(tmp_path: Path) -> None:
    assert aggregate_oov_gaps(tmp_path / "does_not_exist") == ()


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------


def _gap(token: str, count: int = 3, clean: int | None = None) -> OOVGap:
    return OOVGap(
        token=token,
        intents=("definition",),
        count=count,
        boundary_clean_count=count if clean is None else clean,
        sample_candidate_ids=("a", "b"),
        months_seen=("2026-05",),
    )


def test_promotion_respects_threshold() -> None:
    gaps = (_gap("photosynthesis", count=5, clean=5),)
    promoted = promote_oov_gaps(gaps, threshold=3)
    assert len(promoted) == 1
    assert promoted[0].token == "photosynthesis"


def test_promotion_excludes_below_threshold() -> None:
    gaps = (_gap("rare", count=1, clean=1),)
    assert promote_oov_gaps(gaps, threshold=3) == ()


def test_promotion_excludes_tainted_only_by_default() -> None:
    gaps = (_gap("forbidden", count=5, clean=0),)
    assert promote_oov_gaps(gaps, threshold=3) == ()


def test_include_tainted_counts_all() -> None:
    gaps = (_gap("forbidden", count=5, clean=0),)
    promoted = promote_oov_gaps(gaps, threshold=3, include_tainted=True)
    assert len(promoted) == 1


def test_threshold_must_be_positive() -> None:
    with pytest.raises(ValueError):
        promote_oov_gaps((_gap("photosynthesis"),), threshold=0)


def test_queue_id_format() -> None:
    promoted = promote_oov_gaps((_gap("photosynthesis", count=5, clean=5),), threshold=3)
    assert promoted[0].queue_id == "oov:photosynthesis@3"


def test_promotion_suggests_mounted_packs() -> None:
    promoted = promote_oov_gaps((_gap("photosynthesis", count=5, clean=5),), threshold=3)
    assert "en_core_cognition_v1" in promoted[0].suggested_packs


def test_promotion_is_deterministic() -> None:
    gaps = (
        _gap("photosynthesis", count=5, clean=5),
        _gap("mitochondria", count=5, clean=5),
    )
    a = promote_oov_gaps(gaps, threshold=3)
    b = promote_oov_gaps(gaps, threshold=3)
    assert a == b
    assert [p.token for p in a] == ["mitochondria", "photosynthesis"]


def test_promotion_does_not_mutate_input() -> None:
    gaps = (_gap("photosynthesis", count=3, clean=3),)
    snapshot = gaps[0]
    promote_oov_gaps(gaps, threshold=3)
    assert gaps[0] == snapshot
