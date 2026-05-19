"""Tests for ``ChatRuntime._maybe_apply_discourse_planner``.

Pins the single-helper contract that the cold and warm runtime hooks
both call.  These tests are unit-level — they exercise the helper
directly with a real ``ChatRuntime``, without driving the full
``chat`` pipeline.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


@pytest.fixture()
def runtime_flag_off() -> ChatRuntime:
    return ChatRuntime(config=RuntimeConfig(discourse_planner=False))


@pytest.fixture()
def runtime_flag_on() -> ChatRuntime:
    return ChatRuntime(config=RuntimeConfig(discourse_planner=True))


class TestPlannerHelperGating:
    def test_flag_off_returns_none(self, runtime_flag_off: ChatRuntime) -> None:
        result = runtime_flag_off._maybe_apply_discourse_planner(
            "Tell me about truth.", "teaching"
        )
        assert result is None

    @pytest.mark.parametrize("tag", ["vault", "none", "oov", "", "unknown"])
    def test_non_grounded_source_returns_none(
        self, runtime_flag_on: ChatRuntime, tag: str
    ) -> None:
        result = runtime_flag_on._maybe_apply_discourse_planner(
            "Tell me about truth.", tag
        )
        assert result is None

    def test_empty_subject_returns_none(self, runtime_flag_on: ChatRuntime) -> None:
        # An unclassified prompt has no head-noun subject.
        result = runtime_flag_on._maybe_apply_discourse_planner("", "pack")
        assert result is None


class TestPlannerHelperEngagement:
    def test_returns_multi_clause_surface_on_grounded_subject(
        self, runtime_flag_on: ChatRuntime
    ) -> None:
        result = runtime_flag_on._maybe_apply_discourse_planner(
            "Tell me about truth.", "teaching"
        )
        assert result is not None
        surface, source = result
        # Multi-clause: at least one connective from the canonical table.
        assert "Furthermore," in surface or "In turn," in surface
        # Source is one of the two grounded labels — never "oov" or "none".
        assert source in {"pack", "teaching"}

    def test_returns_none_for_single_move_plan(
        self, runtime_flag_on: ChatRuntime
    ) -> None:
        # BRIEF mode (default for "What is X?") collapses to ANCHOR-only;
        # helper must return None so callers don't replace the byte-
        # identical single-sentence pack-grounded surface.
        result = runtime_flag_on._maybe_apply_discourse_planner(
            "What is truth?", "pack"
        )
        assert result is None

    def test_compound_prompt_engages_via_oov_bypass(
        self, runtime_flag_on: ChatRuntime
    ) -> None:
        # Compound bypass: upstream tagged the surface "oov" because
        # the flat classifier saw a polluted subject, but the compound
        # decomposition reveals a pack-resident primary subject.  The
        # helper should engage and return a grounded source tag.
        result = runtime_flag_on._maybe_apply_discourse_planner(
            "What is truth, and what is knowledge?", "oov"
        )
        assert result is not None
        surface, source = result
        assert source in {"pack", "teaching"}
        # Both subjects should appear in the rendered surface.
        assert "truth" in surface.lower()
        assert "knowledge" in surface.lower()
