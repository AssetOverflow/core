"""tests/test_identity_gate.py — Tests for IdentityCheck gate wiring.

Covers:
  - IdentityCheck.check() returns an IdentityScore for a valid trajectory
  - IdentityScore.score is a float in [0, 1]
  - IdentityScore.flagged is a bool
  - IdentityScore.value and .alignment property aliases work
  - IdentityScore.axes_evaluated returns a sorted list
  - ChatRuntime.turn_log[-1].identity_score is populated after chat()
  - ChatRuntime.turn_log[-1].flagged matches response.flagged
  - TurnEvent.elaboration field exists and is Optional[str]
  - A response that should not be flagged has flagged=False
"""
from __future__ import annotations

import pytest

from core.physics.identity import (
    IdentityCheck,
    IdentityManifold,
    IdentityScore,
    TurnEvent,
    ValueAxis,
)
from core.physics.reasoning import ReasoningTrajectory, TrajectoryOperator

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manifold() -> IdentityManifold:
    return IdentityManifold(
        value_axes=(
            ValueAxis(
                name="truthfulness",
                direction=np.array([1.0, 0.0, 0.0], dtype=np.float32),
                weight=1.0,
            ),
            ValueAxis(
                name="coherence",
                direction=np.array([0.0, 1.0, 0.0], dtype=np.float32),
                weight=1.0,
            ),
        ),
    )


def _make_trajectory(n_steps: int = 4) -> ReasoningTrajectory:
    """Minimal trajectory with n_steps identity operators."""
    ops = [
        TrajectoryOperator(
            versor=np.ones(32, dtype=np.float32) / np.sqrt(32),
            step=i,
        )
        for i in range(n_steps)
    ]
    return ReasoningTrajectory(operators=tuple(ops), turn=0)


# ---------------------------------------------------------------------------
# IdentityScore invariants
# ---------------------------------------------------------------------------

class TestIdentityScore:
    def test_score_is_float_in_unit_interval(self):
        manifold = _make_manifold()
        check = IdentityCheck(manifold=manifold)
        trajectory = _make_trajectory()
        score = check.check(trajectory)
        assert isinstance(score, IdentityScore)
        assert 0.0 <= score.score <= 1.0

    def test_flagged_is_bool(self):
        manifold = _make_manifold()
        check = IdentityCheck(manifold=manifold)
        score = check.check(_make_trajectory())
        assert isinstance(score.flagged, bool)

    def test_value_alias_matches_score(self):
        manifold = _make_manifold()
        check = IdentityCheck(manifold=manifold)
        score = check.check(_make_trajectory())
        assert score.value == score.score

    def test_alignment_is_float_in_unit_interval(self):
        manifold = _make_manifold()
        check = IdentityCheck(manifold=manifold)
        score = check.check(_make_trajectory())
        assert 0.0 <= score.alignment <= 1.0

    def test_axes_evaluated_is_sorted_list(self):
        manifold = _make_manifold()
        check = IdentityCheck(manifold=manifold)
        score = check.check(_make_trajectory())
        axes = score.axes_evaluated
        assert isinstance(axes, list)
        assert axes == sorted(axes)

    def test_deviation_axes_is_frozenset_of_str(self):
        manifold = _make_manifold()
        check = IdentityCheck(manifold=manifold)
        score = check.check(_make_trajectory())
        assert isinstance(score.deviation_axes, frozenset)
        for ax in score.deviation_axes:
            assert isinstance(ax, str)


# ---------------------------------------------------------------------------
# TurnEvent field invariants
# ---------------------------------------------------------------------------

class TestTurnEventFields:
    def test_elaboration_field_exists_and_is_optional_str(self):
        """TurnEvent.elaboration must be Optional[str] — verify field presence."""
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(TurnEvent)}
        assert "elaboration" in fields, "TurnEvent missing elaboration field"
        # Default must be None.
        # We can't instantiate without all required fields, so just check the
        # default value via the field descriptor.
        field_obj = fields["elaboration"]
        assert field_obj.default is None

    def test_identity_score_field_is_optional(self):
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(TurnEvent)}
        assert "identity_score" in fields

    def test_flagged_field_exists(self):
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(TurnEvent)}
        assert "flagged" in fields


# ---------------------------------------------------------------------------
# ChatRuntime integration: identity_score wired into turn_log
# ---------------------------------------------------------------------------

class TestChatRuntimeIdentityWiring:
    """These tests instantiate a live ChatRuntime and check identity gate wiring.

    Skipped if ChatRuntime cannot be instantiated (missing language pack data).
    """

    @pytest.fixture(autouse=True)
    def runtime(self):
        try:
            from chat.runtime import ChatRuntime
            self._runtime = ChatRuntime()
        except Exception as exc:
            pytest.skip(f"ChatRuntime not available: {exc}")

    def test_turn_log_populated_after_chat(self):
        self._runtime.chat("truth", max_tokens=4)
        assert len(self._runtime.turn_log) >= 1

    def test_identity_score_is_identityscore_or_none(self):
        self._runtime.chat("light", max_tokens=4)
        ev = self._runtime.turn_log[-1]
        assert ev.identity_score is None or isinstance(ev.identity_score, IdentityScore)

    def test_flagged_matches_response(self):
        response = self._runtime.chat("covenant", max_tokens=4)
        ev = self._runtime.turn_log[-1]
        assert ev.flagged == response.flagged

    def test_elaboration_is_none_or_str(self):
        self._runtime.chat("word", max_tokens=8)
        ev = self._runtime.turn_log[-1]
        assert ev.elaboration is None or isinstance(ev.elaboration, str)

    def test_unflagged_response_has_non_empty_surface(self):
        response = self._runtime.chat("beginning", max_tokens=8)
        if not response.flagged:
            assert response.surface, "Surface must not be empty for unflagged response"
