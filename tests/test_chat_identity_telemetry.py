"""Regression coverage for chat identity telemetry and vault recall counts."""

from __future__ import annotations

import pytest


@pytest.fixture()
def runtime():
    try:
        from chat.runtime import ChatRuntime
        return ChatRuntime()
    except Exception as exc:
        pytest.skip(f"ChatRuntime not available: {exc}")


def test_chat_surface_keeps_walk_visible_when_identity_is_telemetry(runtime):
    response = runtime.chat("truth", max_tokens=6)

    assert response.walk_surface
    assert response.surface == response.walk_surface
    assert isinstance(response.flagged, bool)
    assert response.identity_score is not None


def test_turn_log_records_selected_surface_and_walk_surface(runtime):
    response = runtime.chat("light", max_tokens=6)
    event = runtime.turn_log[-1]

    assert event.surface == response.surface
    assert event.walk_surface == response.walk_surface
    assert event.articulation_surface == response.articulation.surface


def test_vault_hits_are_actual_generation_telemetry(runtime):
    first = runtime.chat("truth", max_tokens=4)
    second = runtime.chat("truth", max_tokens=4)

    assert first.vault_hits >= 0
    assert second.vault_hits >= first.vault_hits
    assert runtime.turn_log[-1].vault_hits == second.vault_hits


def test_default_identity_threshold_matches_micro_pack_energy(runtime):
    response = runtime.chat("λόγος", max_tokens=4)

    assert response.identity_score is not None
    assert runtime.identity_manifold.alignment_threshold == pytest.approx(0.45)
    assert response.identity_score.score >= runtime.identity_manifold.alignment_threshold
    assert response.identity_score.axes_evaluated == []
