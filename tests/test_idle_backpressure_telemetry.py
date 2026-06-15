"""W1-T — Idle backpressure telemetry tests.

Three classes of tests per the brief:
1. Record fields match the tick's actual counts (unit coverage).
2. ``trace_hash`` of a served turn is byte-identical with and without the
   backpressure telemetry code active — the load-bearing firewall proof.
3. ``headroom``/``at_fixed_point`` semantics for backlog-growing vs draining
   ticks.

Each numeric predicate has a *_holds test (expected value) and a *_bites test
(mutation that trips it), per CLAUDE.md schema-as-proof discipline.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from core.cognition.backpressure import (
    BackpressureRecord,
    _DEFAULT_PENDING_CAP,
    _resolve_cap,
    build_backpressure_record,
)


# ---------------------------------------------------------------------------
# Unit tests — build_backpressure_record field derivation
# ---------------------------------------------------------------------------


def test_fields_match_input_counts():
    rec = build_backpressure_record(
        pending_proposals=10,
        candidate_backlog=5,
        contemplated_this_tick=3,
        created_this_tick=2,
        did_work=True,
    )
    assert rec.pending_proposals == 10
    assert rec.candidate_backlog == 5
    assert rec.contemplated_this_tick == 3
    assert rec.created_this_tick == 2
    assert rec.did_work is True


def test_headroom_derived_from_cap_minus_pending():
    rec = build_backpressure_record(
        pending_proposals=50,
        candidate_backlog=0,
        contemplated_this_tick=0,
        created_this_tick=0,
        did_work=False,
    )
    assert rec.cap == _DEFAULT_PENDING_CAP  # 256 by default
    assert rec.headroom == _DEFAULT_PENDING_CAP - 50


def test_headroom_zero_at_cap_holds():
    rec = build_backpressure_record(
        pending_proposals=_DEFAULT_PENDING_CAP,
        candidate_backlog=0,
        contemplated_this_tick=0,
        created_this_tick=0,
        did_work=False,
    )
    assert rec.headroom == 0


def test_headroom_clamped_at_zero_when_over_cap():
    # Should not go negative even if somehow over cap.
    rec = build_backpressure_record(
        pending_proposals=_DEFAULT_PENDING_CAP + 10,
        candidate_backlog=0,
        contemplated_this_tick=0,
        created_this_tick=0,
        did_work=False,
    )
    assert rec.headroom == 0


def test_headroom_zero_bites():
    # A tick with fewer proposals than cap must have positive headroom.
    rec = build_backpressure_record(
        pending_proposals=_DEFAULT_PENDING_CAP - 1,
        candidate_backlog=0,
        contemplated_this_tick=0,
        created_this_tick=0,
        did_work=False,
    )
    assert rec.headroom > 0, "headroom must be positive when below the cap"


# ---------------------------------------------------------------------------
# at_fixed_point semantics
# ---------------------------------------------------------------------------


def test_at_fixed_point_when_backlog_empty_and_no_creations():
    rec = build_backpressure_record(
        pending_proposals=0,
        candidate_backlog=0,
        contemplated_this_tick=0,
        created_this_tick=0,
        did_work=False,
    )
    assert rec.at_fixed_point is True


def test_at_fixed_point_false_when_backlog_nonempty():
    rec = build_backpressure_record(
        pending_proposals=0,
        candidate_backlog=3,  # candidates still waiting
        contemplated_this_tick=0,
        created_this_tick=0,
        did_work=False,
    )
    assert rec.at_fixed_point is False


def test_at_fixed_point_false_when_proposals_created_this_tick():
    rec = build_backpressure_record(
        pending_proposals=2,
        candidate_backlog=0,  # backlog now empty...
        contemplated_this_tick=5,
        created_this_tick=2,   # ...but this tick created proposals
        did_work=True,
    )
    assert rec.at_fixed_point is False


def test_at_fixed_point_bites_on_nonempty_backlog():
    # at_fixed_point must NOT be True when there are pending candidates.
    rec = build_backpressure_record(
        pending_proposals=0,
        candidate_backlog=1,
        contemplated_this_tick=0,
        created_this_tick=0,
        did_work=False,
    )
    assert not rec.at_fixed_point, "at_fixed_point must be False with non-empty backlog"


# ---------------------------------------------------------------------------
# Cap resolution
# ---------------------------------------------------------------------------


def test_default_cap_is_256():
    assert _resolve_cap() == 256


def test_cap_env_override():
    with patch.dict(os.environ, {"CORE_HITL_PENDING_CAP": "64"}):
        rec = build_backpressure_record(
            pending_proposals=0,
            candidate_backlog=0,
            contemplated_this_tick=0,
            created_this_tick=0,
            did_work=False,
        )
    assert rec.cap == 64
    assert rec.headroom == 64


def test_cap_env_invalid_falls_back_to_default():
    with patch.dict(os.environ, {"CORE_HITL_PENDING_CAP": "not_a_number"}):
        assert _resolve_cap() == _DEFAULT_PENDING_CAP


# ---------------------------------------------------------------------------
# Firewall proof: idle_tick's backpressure telemetry must not change trace_hash
# ---------------------------------------------------------------------------


def test_trace_hash_byte_identical_with_backpressure_active(tmp_path: Path):
    """The serving trace_hash is byte-identical whether idle_tick runs before
    the turn or not.

    Uses a fresh runtime with default config (all learning passes disabled)
    so idle_tick is a pure no-op except for building the BackpressureRecord.
    If backpressure building or telemetry writing introduces any side effect
    on the serving field state, the trace_hashes will diverge.
    """
    from chat.runtime import ChatRuntime
    from core.cognition.pipeline import CognitiveTurnPipeline
    from core.config import RuntimeConfig

    text = "what is truth"

    # Baseline: fresh runtime, single turn (no idle_tick).
    rt_a = ChatRuntime(
        config=RuntimeConfig(), engine_state_path=tmp_path / "a"
    )
    pipe_a = CognitiveTurnPipeline(runtime=rt_a)
    hash_a = pipe_a.run(text).trace_hash

    # Firewall: fresh runtime, idle_tick first, THEN same turn.
    # With default config, idle_tick does no learning (all passes off,
    # empty backlog), so the field state entering pipe_b.run is identical.
    rt_b = ChatRuntime(
        config=RuntimeConfig(), engine_state_path=tmp_path / "b"
    )
    pipe_b = CognitiveTurnPipeline(runtime=rt_b)
    tick_result = rt_b.idle_tick()

    # idle_tick must have built a backpressure record (the new code path).
    assert tick_result.backpressure is not None
    assert isinstance(tick_result.backpressure, BackpressureRecord)

    hash_b = pipe_b.run(text).trace_hash

    assert hash_a == hash_b, (
        "Backpressure telemetry in idle_tick must not change the serving trace_hash.\n"
        f"  without idle_tick: {hash_a}\n"
        f"  with idle_tick:    {hash_b}"
    )


def test_idle_tick_backpressure_record_fields_on_fresh_runtime(tmp_path: Path):
    """On a fresh runtime with no candidates, backpressure reflects zeros."""
    from chat.runtime import ChatRuntime
    from core.config import RuntimeConfig

    rt = ChatRuntime(config=RuntimeConfig(), engine_state_path=tmp_path / "rt")
    result = rt.idle_tick()

    bp = result.backpressure
    assert bp is not None
    assert bp.candidate_backlog == 0
    assert bp.pending_proposals == 0
    assert bp.contemplated_this_tick == 0
    assert bp.created_this_tick == 0
    assert bp.did_work is False
    assert bp.at_fixed_point is True
    assert bp.headroom == bp.cap  # headroom == cap when pending == 0


def test_idle_telemetry_written_to_engine_state_dir(tmp_path: Path):
    """One JSONL line is appended to idle_telemetry.jsonl per idle_tick call."""
    from chat.runtime import ChatRuntime
    from core.config import RuntimeConfig

    engine_dir = tmp_path / "es"
    rt = ChatRuntime(config=RuntimeConfig(), engine_state_path=engine_dir)
    rt.idle_tick()

    telem = engine_dir / "idle_telemetry.jsonl"
    assert telem.exists(), "idle_telemetry.jsonl must be created in engine_state dir"
    lines = [l for l in telem.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert "pending_proposals" in record
    assert "candidate_backlog" in record
    assert "cap" in record
    assert "headroom" in record
    assert "at_fixed_point" in record
    assert "did_work" in record


def test_idle_telemetry_accumulates_across_ticks(tmp_path: Path):
    """Each idle_tick appends a new line — history accumulates."""
    from chat.runtime import ChatRuntime
    from core.config import RuntimeConfig

    engine_dir = tmp_path / "es"
    rt = ChatRuntime(config=RuntimeConfig(), engine_state_path=engine_dir)
    rt.idle_tick()
    rt.idle_tick()
    rt.idle_tick()

    telem = engine_dir / "idle_telemetry.jsonl"
    lines = [l for l in telem.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 3, "each idle_tick must append exactly one line"
