"""Phase 4 — end-to-end ``last_plan_metrics`` runtime wiring.

Mirrors ``tests/test_plan_contemplation_runtime.py`` for the
quantitative companion.  Pins:

  * Disabled by default — ``last_plan_metrics`` stays ``None`` even
    when the planner engages.
  * Enabled — metrics are populated whenever the planner engages.
  * BRIEF prompts (fast-path) yield ``None`` metrics.
  * Metrics do not leak across turns.
  * Same prompt → byte-equal ``as_dict()`` (determinism).
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


# ---------------------------------------------------------------------------
# Disabled by default
# ---------------------------------------------------------------------------


def test_metrics_none_when_contemplation_disabled() -> None:
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=False))
    rt.chat("What is truth, and why does it matter?")
    assert rt.last_plan_metrics is None


# ---------------------------------------------------------------------------
# Enabled — multi-move plan populates structured metrics
# ---------------------------------------------------------------------------


def test_compound_prompt_yields_expected_shape() -> None:
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat("What is truth, and why does it matter?")
    m = rt.last_plan_metrics
    assert m is not None
    # Compound prompt routes through two sub-plans plus a bridge.
    assert m.move_count >= 4
    assert m.fact_bearing_count >= 4
    # Plan re-uses the truth subject across multiple moves; should
    # therefore expose pronominalization opportunities.
    assert m.pronominalization_opportunities >= 1
    # Diversity ratios resolve to real numbers (no None) on a
    # multi-move plan with >= 1 fact-bearing move.
    assert m.predicate_diversity_ratio is not None
    assert 0.0 < m.predicate_diversity_ratio <= 1.0
    assert m.subject_focus_ratio is not None
    assert 0.0 <= m.subject_focus_ratio <= 1.0


# ---------------------------------------------------------------------------
# BRIEF prompts (fast-path) yield no metrics
# ---------------------------------------------------------------------------


def test_brief_prompt_yields_no_metrics() -> None:
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat("What is knowledge?")
    assert rt.last_plan_metrics is None


# ---------------------------------------------------------------------------
# Metrics do not leak across turns
# ---------------------------------------------------------------------------


def test_metrics_reset_between_turns() -> None:
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat("What is truth, and why does it matter?")
    assert rt.last_plan_metrics is not None  # sanity
    rt.chat("What is knowledge?")  # BRIEF — should clear
    assert rt.last_plan_metrics is None


# ---------------------------------------------------------------------------
# Determinism across two runs
# ---------------------------------------------------------------------------


def test_metrics_byte_equal_across_runs() -> None:
    rt1 = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt2 = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt1.chat("Tell me about memory.")
    rt2.chat("Tell me about memory.")
    m1 = rt1.last_plan_metrics
    m2 = rt2.last_plan_metrics
    assert m1 is not None and m2 is not None
    assert m1.as_dict() == m2.as_dict()


# ---------------------------------------------------------------------------
# Findings and metrics co-populate cleanly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "Tell me about memory.",
        "Explain truth.",
        "What is truth, and why does it matter?",
    ],
)
def test_findings_and_metrics_populate_together(prompt: str) -> None:
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat(prompt)
    metrics = rt.last_plan_metrics
    # Whenever metrics is populated, the planner engaged; findings
    # is at least an empty tuple (never None on engaged turns).
    assert metrics is not None
    assert isinstance(rt.last_plan_findings, tuple)
    # And the metrics' fact_bearing_count is non-zero on every
    # engaged turn.
    assert metrics.fact_bearing_count >= 1
