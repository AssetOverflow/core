"""Speculative-subject cache lifecycle (Finding 5, audit 2026-05-20).

Pre-fix ``CognitiveTurnPipeline._speculative_subjects`` was an unbounded
``set[str]`` that only grew over a session.  Two correctness gaps:

  * A subject promoted to ``EpistemicStatus.COHERENT`` via the teaching
    review loop kept appearing with the "(speculative, not yet reviewed)"
    marker forever.
  * Long teaching sessions widened the per-turn substring scan inside
    ``_should_mark_speculative`` without bound.

These tests pin the lifecycle so the fix cannot silently regress.
"""

from __future__ import annotations

from collections import OrderedDict

import pytest

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline
from core.cognition.pipeline import _MAX_SPECULATIVE_SUBJECTS


@pytest.fixture()
def pipeline() -> CognitiveTurnPipeline:
    return CognitiveTurnPipeline(runtime=ChatRuntime())


def test_storage_is_bounded_ordereddict(pipeline: CognitiveTurnPipeline) -> None:
    assert isinstance(pipeline._speculative_subjects, OrderedDict)
    assert _MAX_SPECULATIVE_SUBJECTS == 64


def test_remember_inserts_and_normalizes(pipeline: CognitiveTurnPipeline) -> None:
    pipeline._remember_speculative_subject("  TRUTH  ")
    assert "truth" in pipeline._speculative_subjects
    pipeline._remember_speculative_subject("")
    pipeline._remember_speculative_subject("   ")
    # Empty / whitespace inputs are silently dropped
    assert list(pipeline._speculative_subjects) == ["truth"]


def test_remember_refreshes_lru_position(pipeline: CognitiveTurnPipeline) -> None:
    pipeline._remember_speculative_subject("alpha")
    pipeline._remember_speculative_subject("beta")
    pipeline._remember_speculative_subject("alpha")
    # alpha was re-touched after beta, so alpha is now the MRU entry
    assert list(pipeline._speculative_subjects) == ["beta", "alpha"]


def test_cache_caps_at_max(pipeline: CognitiveTurnPipeline) -> None:
    for i in range(_MAX_SPECULATIVE_SUBJECTS + 10):
        pipeline._remember_speculative_subject(f"subj{i:03d}")
    assert len(pipeline._speculative_subjects) == _MAX_SPECULATIVE_SUBJECTS
    # Oldest 10 entries (subj000..subj009) evicted; newest survive
    keys = list(pipeline._speculative_subjects)
    assert "subj000" not in keys
    assert "subj009" not in keys
    assert "subj010" in keys
    assert keys[-1] == f"subj{_MAX_SPECULATIVE_SUBJECTS + 9:03d}"


def test_forget_removes(pipeline: CognitiveTurnPipeline) -> None:
    pipeline._remember_speculative_subject("truth")
    pipeline._remember_speculative_subject("light")
    pipeline._forget_speculative_subject("Truth")  # case-insensitive
    assert "truth" not in pipeline._speculative_subjects
    assert "light" in pipeline._speculative_subjects


def test_forget_missing_is_noop(pipeline: CognitiveTurnPipeline) -> None:
    pipeline._remember_speculative_subject("truth")
    pipeline._forget_speculative_subject("never-added")
    pipeline._forget_speculative_subject("")
    assert list(pipeline._speculative_subjects) == ["truth"]


def test_should_mark_speculative_still_iterates_correctly(
    pipeline: CognitiveTurnPipeline,
) -> None:
    """The marker decision still triggers on stored subjects."""
    pipeline._remember_speculative_subject("wisdom")
    assert pipeline._should_mark_speculative(
        text="Tell me about wisdom",
        surface="Wisdom is the application of knowledge.",
    )
    pipeline._forget_speculative_subject("wisdom")
    assert not pipeline._should_mark_speculative(
        text="Tell me about wisdom",
        surface="Wisdom is the application of knowledge.",
    )
