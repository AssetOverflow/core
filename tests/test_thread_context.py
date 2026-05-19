"""Phase 3.1 — session-thread context tests.

The contract these tests pin:

  - ``TurnSummary`` is frozen + carries only structured fields.
  - ``ThreadContext`` is bounded (FIFO eviction at max_turns).
  - ``push`` appends; ``snapshot`` returns the deque in insertion
    order (oldest first).
  - ``recent_for_subject`` returns the most-recent matching summary,
    skipping ungrounded tiers by default.
  - ``recent_subjects`` returns unique subjects most-recent-first.
  - ChatRuntime owns one ThreadContext; pushes a summary at
    end-of-turn for BOTH the stub path and the walk path.
  - Teaching-grounded turns carry chain_id + corpus_id in the
    summary so anaphora composers can detect same-chain reference.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from chat.thread_context import (
    MAX_THREAD_TURNS,
    ThreadContext,
    TurnSummary,
)


# ---------------------------------------------------------------------------
# TurnSummary dataclass
# ---------------------------------------------------------------------------


def test_turn_summary_is_frozen() -> None:
    s = TurnSummary(turn_index=0, intent_tag_name="cause",
                    subject="light", grounding_source="teaching",
                    chain_id="cause_light_reveals_truth",
                    corpus_id="cognition_chains_v1")
    with pytest.raises((AttributeError, TypeError)):
        s.subject = "other"  # type: ignore[misc]


def test_turn_summary_as_dict_round_trips() -> None:
    s = TurnSummary(turn_index=3, intent_tag_name="definition",
                    subject="parent", grounding_source="pack")
    blob = s.as_dict()
    assert blob["turn_index"] == 3
    assert blob["subject"] == "parent"
    assert blob["grounding_source"] == "pack"
    assert blob["chain_id"] is None
    assert blob["corpus_id"] is None


# ---------------------------------------------------------------------------
# ThreadContext bounded FIFO
# ---------------------------------------------------------------------------


def test_default_capacity() -> None:
    tc = ThreadContext()
    assert tc.max_turns == MAX_THREAD_TURNS


def test_invalid_capacity_raises() -> None:
    with pytest.raises(ValueError):
        ThreadContext(max_turns=0)
    with pytest.raises(ValueError):
        ThreadContext(max_turns=-1)


def test_push_and_snapshot_preserve_order() -> None:
    tc = ThreadContext(max_turns=4)
    for i in range(3):
        tc.push(TurnSummary(turn_index=i, intent_tag_name="cause",
                            subject=f"s{i}", grounding_source="teaching"))
    snap = tc.snapshot()
    assert [s.turn_index for s in snap] == [0, 1, 2]
    assert [s.subject for s in snap] == ["s0", "s1", "s2"]


def test_eviction_drops_oldest() -> None:
    tc = ThreadContext(max_turns=3)
    for i in range(5):
        tc.push(TurnSummary(turn_index=i, intent_tag_name="cause",
                            subject=f"s{i}", grounding_source="teaching"))
    snap = tc.snapshot()
    assert len(snap) == 3
    # 0, 1 evicted; 2, 3, 4 retained.
    assert [s.turn_index for s in snap] == [2, 3, 4]


def test_clear_resets_state() -> None:
    tc = ThreadContext(max_turns=4)
    tc.push(TurnSummary(turn_index=0, intent_tag_name="cause",
                        subject="x", grounding_source="teaching"))
    assert len(tc) == 1
    tc.clear()
    assert len(tc) == 0


# ---------------------------------------------------------------------------
# recent_for_subject
# ---------------------------------------------------------------------------


def test_recent_for_subject_returns_most_recent_match() -> None:
    tc = ThreadContext()
    tc.push(TurnSummary(turn_index=0, intent_tag_name="cause",
                        subject="light", grounding_source="teaching"))
    tc.push(TurnSummary(turn_index=1, intent_tag_name="cause",
                        subject="memory", grounding_source="teaching"))
    tc.push(TurnSummary(turn_index=2, intent_tag_name="definition",
                        subject="light", grounding_source="pack"))
    match = tc.recent_for_subject("light")
    assert match is not None
    assert match.turn_index == 2  # most recent, not the first
    assert match.intent_tag_name == "definition"


def test_recent_for_subject_skips_ungrounded_by_default() -> None:
    """OOV / partial / none turns are excluded from recency lookup
    by default — they're not strong-enough anchors for anaphora."""
    tc = ThreadContext()
    tc.push(TurnSummary(turn_index=0, intent_tag_name="cause",
                        subject="light", grounding_source="teaching"))
    tc.push(TurnSummary(turn_index=1, intent_tag_name="definition",
                        subject="light", grounding_source="oov"))
    match = tc.recent_for_subject("light")
    assert match is not None
    assert match.turn_index == 0  # teaching turn wins; oov skipped


def test_recent_for_subject_can_include_excluded_tiers() -> None:
    tc = ThreadContext()
    tc.push(TurnSummary(turn_index=0, intent_tag_name="cause",
                        subject="light", grounding_source="teaching"))
    tc.push(TurnSummary(turn_index=1, intent_tag_name="definition",
                        subject="light", grounding_source="oov"))
    match = tc.recent_for_subject("light", exclude_grounding=())
    assert match is not None
    assert match.turn_index == 1


def test_recent_for_subject_normalises_input() -> None:
    tc = ThreadContext()
    tc.push(TurnSummary(turn_index=0, intent_tag_name="cause",
                        subject="light", grounding_source="teaching"))
    for query in ("LIGHT", "Light", " light "):
        match = tc.recent_for_subject(query)
        assert match is not None


def test_recent_for_subject_returns_none_when_absent() -> None:
    tc = ThreadContext()
    assert tc.recent_for_subject("anything") is None
    tc.push(TurnSummary(turn_index=0, intent_tag_name="cause",
                        subject="x", grounding_source="teaching"))
    assert tc.recent_for_subject("y") is None


# ---------------------------------------------------------------------------
# recent_subjects
# ---------------------------------------------------------------------------


def test_recent_subjects_unique_most_recent_first() -> None:
    tc = ThreadContext()
    tc.push(TurnSummary(turn_index=0, intent_tag_name="cause",
                        subject="light", grounding_source="teaching"))
    tc.push(TurnSummary(turn_index=1, intent_tag_name="cause",
                        subject="memory", grounding_source="teaching"))
    tc.push(TurnSummary(turn_index=2, intent_tag_name="definition",
                        subject="light", grounding_source="pack"))
    subjects = tc.recent_subjects()
    assert subjects == ("light", "memory")


def test_recent_subjects_skips_empty_and_ungrounded() -> None:
    tc = ThreadContext()
    tc.push(TurnSummary(turn_index=0, intent_tag_name="",
                        subject="", grounding_source="vault"))
    tc.push(TurnSummary(turn_index=1, intent_tag_name="definition",
                        subject="photosynthesis", grounding_source="oov"))
    tc.push(TurnSummary(turn_index=2, intent_tag_name="cause",
                        subject="light", grounding_source="teaching"))
    subjects = tc.recent_subjects()
    assert subjects == ("light",)


# ---------------------------------------------------------------------------
# Runtime integration — ChatRuntime pushes after each turn
# ---------------------------------------------------------------------------


def test_runtime_pushes_summary_on_cold_start_pack_turn() -> None:
    rt = ChatRuntime()
    rt.chat("What is light?")
    snap = rt.thread_context.snapshot()
    assert len(snap) == 1
    s = snap[0]
    assert s.intent_tag_name == "definition"
    assert s.subject == "light"
    assert s.grounding_source == "pack"


def test_runtime_pushes_chain_id_for_teaching_grounded_turn() -> None:
    rt = ChatRuntime()
    rt.chat("Why does light exist?")
    s = rt.thread_context.snapshot()[0]
    assert s.grounding_source == "teaching"
    assert s.chain_id == "cause_light_reveals_truth"
    assert s.corpus_id == "cognition_chains_v1"


def test_runtime_pushes_summary_for_oov_turn() -> None:
    rt = ChatRuntime()
    rt.chat("What is photosynthesis?")
    s = rt.thread_context.snapshot()[0]
    assert s.intent_tag_name == "definition"
    assert s.subject == "photosynthesis"
    assert s.grounding_source == "oov"
    assert s.chain_id is None


def test_runtime_thread_context_grows_across_turns() -> None:
    rt = ChatRuntime()
    rt.chat("What is light?")
    rt.chat("What is parent?")
    rt.chat("What is photosynthesis?")
    snap = rt.thread_context.snapshot()
    assert len(snap) == 3
    assert snap[0].subject == "light"
    assert snap[1].subject == "parent"
    assert snap[2].subject == "photosynthesis"


def test_runtime_thread_context_indexes_match_turn_log() -> None:
    rt = ChatRuntime()
    rt.chat("What is light?")
    rt.chat("What is parent?")
    snap = rt.thread_context.snapshot()
    assert [s.turn_index for s in snap] == list(range(len(rt.turn_log)))


def test_runtime_default_capacity_evicts_old_turns() -> None:
    rt = ChatRuntime()
    for _ in range(MAX_THREAD_TURNS + 3):
        rt.chat("What is light?")
    snap = rt.thread_context.snapshot()
    assert len(snap) == MAX_THREAD_TURNS
    # Oldest retained turn_index is (total - MAX_THREAD_TURNS).
    total_turns = len(rt.turn_log)
    assert snap[0].turn_index == total_turns - MAX_THREAD_TURNS
