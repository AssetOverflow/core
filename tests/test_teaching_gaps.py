"""Phase 1.1 — discovery-gap aggregation tests.

The contract these tests pin:

  - ``aggregate_gaps`` is a pure reader: never mutates sink files,
    returns deterministic ordering, skips malformed lines silently.
  - Filenames follow ``YYYY-MM.jsonl`` under ``<root>/<YYYY>/`` —
    other names are ignored.
  - ``--since YYYY-MM`` filters by month (inclusive lower bound).
  - ``boundary_clean=false`` candidates are counted but split out so
    operators can filter refusal/hedge-tainted cells separately.
  - ``top`` truncation preserves order.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from teaching.gaps import Gap, aggregate_gaps


def _write_line(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        fh.write("\n")


def _candidate(
    *,
    candidate_id: str,
    subject: str,
    intent: str,
    boundary_clean: bool = True,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "proposed_chain": {
            "subject": subject,
            "intent": intent,
            "connective": None,
            "object": None,
        },
        "trigger": "would_have_grounded",
        "source_turn_trace": "trace-" + candidate_id,
        "pack_consistent": True,
        "boundary_clean": boundary_clean,
        "review_state": "unreviewed",
    }


# ---------------------------------------------------------------------------
# Aggregation — basic counts, ordering, sample retention
# ---------------------------------------------------------------------------


def test_aggregates_by_subject_intent(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    _write_line(sink, _candidate(candidate_id="a", subject="parent", intent="cause"))
    _write_line(sink, _candidate(candidate_id="b", subject="parent", intent="cause"))
    _write_line(sink, _candidate(candidate_id="c", subject="child", intent="verification"))

    rows = aggregate_gaps(tmp_path)

    assert len(rows) == 2
    parent_cause = next(g for g in rows if g.subject == "parent")
    child_verif = next(g for g in rows if g.subject == "child")
    assert parent_cause.intent == "cause"
    assert parent_cause.count == 2
    assert parent_cause.boundary_clean_count == 2
    assert parent_cause.sample_candidate_ids == ("a", "b")
    assert parent_cause.months_seen == ("2026-05",)
    assert child_verif.count == 1


def test_rank_order_count_desc_then_subject(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    # 3x parent-cause, 2x child-cause, 1x family-cause
    for i in range(3):
        _write_line(sink, _candidate(candidate_id=f"p{i}", subject="parent", intent="cause"))
    for i in range(2):
        _write_line(sink, _candidate(candidate_id=f"c{i}", subject="child", intent="cause"))
    _write_line(sink, _candidate(candidate_id="f0", subject="family", intent="cause"))

    rows = aggregate_gaps(tmp_path)

    assert [g.subject for g in rows] == ["parent", "child", "family"]
    assert [g.count for g in rows] == [3, 2, 1]


def test_top_truncation_preserves_order(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    for i in range(3):
        _write_line(sink, _candidate(candidate_id=f"p{i}", subject="parent", intent="cause"))
    _write_line(sink, _candidate(candidate_id="c0", subject="child", intent="cause"))

    rows = aggregate_gaps(tmp_path)
    assert len(rows) == 2
    # Top-1 should yield the parent cell only.
    assert rows[0].subject == "parent"
    assert rows[0].count == 3


# ---------------------------------------------------------------------------
# Boundary-clean accounting
# ---------------------------------------------------------------------------


def test_boundary_tainted_candidates_count_but_split(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    _write_line(sink, _candidate(candidate_id="clean", subject="parent", intent="cause"))
    _write_line(sink, _candidate(
        candidate_id="tainted", subject="parent", intent="cause", boundary_clean=False,
    ))

    rows = aggregate_gaps(tmp_path)
    assert len(rows) == 1
    assert rows[0].count == 2
    assert rows[0].boundary_clean_count == 1


# ---------------------------------------------------------------------------
# --since month filter
# ---------------------------------------------------------------------------


def test_since_filter_excludes_earlier_months(tmp_path: Path) -> None:
    _write_line(tmp_path / "2026" / "2026-04.jsonl",
                _candidate(candidate_id="april", subject="parent", intent="cause"))
    _write_line(tmp_path / "2026" / "2026-05.jsonl",
                _candidate(candidate_id="may", subject="parent", intent="cause"))

    rows = aggregate_gaps(tmp_path, since="2026-05")
    assert len(rows) == 1
    assert rows[0].count == 1
    assert rows[0].sample_candidate_ids == ("may",)


def test_since_filter_includes_boundary_month(tmp_path: Path) -> None:
    _write_line(tmp_path / "2026" / "2026-05.jsonl",
                _candidate(candidate_id="may", subject="parent", intent="cause"))
    rows = aggregate_gaps(tmp_path, since="2026-05")
    assert len(rows) == 1


def test_since_rejects_malformed_token(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        aggregate_gaps(tmp_path, since="May 2026")


# ---------------------------------------------------------------------------
# Robustness — missing root, malformed JSONL, non-monthly filenames
# ---------------------------------------------------------------------------


def test_missing_root_returns_empty_tuple(tmp_path: Path) -> None:
    rows = aggregate_gaps(tmp_path / "does_not_exist")
    assert rows == ()


def test_malformed_lines_silently_skipped(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    sink.parent.mkdir(parents=True, exist_ok=True)
    sink.write_text(
        "\n".join([
            "not json",
            "{}",                                              # missing proposed_chain
            json.dumps({"proposed_chain": {"subject": ""}}),  # empty subject
            json.dumps(_candidate(candidate_id="ok", subject="parent", intent="cause")),
        ]),
        encoding="utf-8",
    )
    rows = aggregate_gaps(tmp_path)
    assert len(rows) == 1
    assert rows[0].subject == "parent"
    assert rows[0].count == 1


def test_non_monthly_filenames_ignored(tmp_path: Path) -> None:
    bad = tmp_path / "2026" / "notes.jsonl"
    good = tmp_path / "2026" / "2026-05.jsonl"
    _write_line(bad, _candidate(candidate_id="bad", subject="parent", intent="cause"))
    _write_line(good, _candidate(candidate_id="good", subject="parent", intent="cause"))

    rows = aggregate_gaps(tmp_path)
    assert len(rows) == 1
    assert rows[0].count == 1
    assert rows[0].sample_candidate_ids == ("good",)


def test_aggregation_is_deterministic(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    for s in ("parent", "child", "ancestor"):
        _write_line(sink, _candidate(candidate_id=f"id-{s}", subject=s, intent="cause"))

    a = aggregate_gaps(tmp_path)
    b = aggregate_gaps(tmp_path)
    assert a == b
    assert [g.as_dict() for g in a] == [g.as_dict() for g in b]


def test_sample_limit_caps_retained_ids(tmp_path: Path) -> None:
    sink = tmp_path / "2026" / "2026-05.jsonl"
    for i in range(10):
        _write_line(sink, _candidate(candidate_id=f"id-{i:02d}", subject="parent", intent="cause"))
    rows = aggregate_gaps(tmp_path, sample_limit=3)
    assert rows[0].count == 10
    assert len(rows[0].sample_candidate_ids) == 3


def test_gap_dataclass_is_frozen() -> None:
    gap = Gap(
        subject="parent", intent="cause", count=1,
        boundary_clean_count=1, sample_candidate_ids=("a",), months_seen=("2026-05",),
    )
    with pytest.raises((AttributeError, TypeError)):
        gap.count = 99  # type: ignore[misc]
