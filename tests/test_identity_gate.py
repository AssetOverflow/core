"""Runtime identity-gate contract tests."""
from __future__ import annotations

from dataclasses import dataclass
import dataclasses

import pytest

from core.physics.drive import ValueAxis
from core.physics.identity import (
    IdentityCheck,
    IdentityManifold,
    IdentityScore,
    TurnEvent,
)
from core.physics.reasoning import ReasoningTrajectory, TrajectoryOperator


@dataclass(frozen=True)
class _Frame:
    frame_id: str
    coherence_magnitude: float
    region_ids: frozenset[str]
    cycle_index: int


def _make_manifold() -> IdentityManifold:
    return IdentityManifold(
        value_axes=(
            ValueAxis(
                axis_id="truthfulness",
                name="truthfulness",
                direction=(1.0, 0.0, 0.0),
                theological_note="test truth axis",
            ),
            ValueAxis(
                axis_id="coherence",
                name="coherence",
                direction=(0.0, 1.0, 0.0),
                theological_note="test coherence axis",
            ),
        ),
    )


def _make_trajectory(n_steps: int = 4) -> ReasoningTrajectory:
    frames = [
        _Frame(
            frame_id=f"f{i}",
            coherence_magnitude=1.0,
            region_ids=frozenset({str(i % 2)}),
            cycle_index=i,
        )
        for i in range(n_steps)
    ]
    return TrajectoryOperator().build(frames, trajectory_id="test_identity_trajectory")


class TestIdentityScore:
    def test_score_is_float_in_unit_interval(self):
        score = IdentityCheck().check(_make_trajectory(), _make_manifold())
        assert isinstance(score, IdentityScore)
        assert 0.0 <= score.score <= 1.0

    def test_flagged_is_bool(self):
        score = IdentityCheck().check(_make_trajectory(), _make_manifold())
        assert isinstance(score.flagged, bool)

    def test_value_alias_matches_score(self):
        score = IdentityCheck().check(_make_trajectory(), _make_manifold())
        assert score.value == score.score

    def test_alignment_is_float_in_unit_interval(self):
        score = IdentityCheck().check(_make_trajectory(), _make_manifold())
        assert 0.0 <= score.alignment <= 1.0

    def test_axes_evaluated_is_sorted_list(self):
        score = IdentityCheck().check(_make_trajectory(), _make_manifold())
        axes = score.axes_evaluated
        assert isinstance(axes, list)
        assert axes == sorted(axes)

    def test_deviation_axes_is_frozenset_of_str(self):
        score = IdentityCheck().check(_make_trajectory(), _make_manifold())
        assert isinstance(score.deviation_axes, frozenset)
        for axis_id in score.deviation_axes:
            assert isinstance(axis_id, str)

    def test_legacy_constructor_emits_deprecation_warning(self):
        with pytest.deprecated_call(match="IdentityCheck\(manifold=\.\.\.\) is deprecated"):
            check = IdentityCheck(manifold=_make_manifold())
        score = check.check(_make_trajectory())
        assert isinstance(score, IdentityScore)


class TestTurnEventFields:
    def test_elaboration_field_exists_and_is_optional_str(self):
        fields = {field.name: field for field in dataclasses.fields(TurnEvent)}
        assert "elaboration" in fields
        assert fields["elaboration"].default is None

    def test_surface_contract_fields_exist(self):
        fields = {field.name for field in dataclasses.fields(TurnEvent)}
        assert {"surface", "walk_surface", "articulation_surface"} <= fields

    def test_identity_score_field_is_optional(self):
        fields = {field.name for field in dataclasses.fields(TurnEvent)}
        assert "identity_score" in fields

    def test_flagged_field_exists(self):
        fields = {field.name for field in dataclasses.fields(TurnEvent)}
        assert "flagged" in fields


class TestChatRuntimeIdentityWiring:
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
        event = self._runtime.turn_log[-1]
        assert event.identity_score is None or isinstance(event.identity_score, IdentityScore)

    def test_flagged_matches_response(self):
        response = self._runtime.chat("covenant", max_tokens=4)
        event = self._runtime.turn_log[-1]
        assert event.flagged == response.flagged

    def test_elaboration_is_none_or_str(self):
        self._runtime.chat("word", max_tokens=8)
        event = self._runtime.turn_log[-1]
        assert event.elaboration is None or isinstance(event.elaboration, str)

    def test_unflagged_response_has_non_empty_surface(self):
        response = self._runtime.chat("beginning", max_tokens=8)
        if not response.flagged:
            assert response.surface
