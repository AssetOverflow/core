from __future__ import annotations

import numpy as np

from sensorium.environment import build_fixture_observation_frame


def test_fixture_observation_frame_is_mixed_modality_and_deterministic():
    f1 = build_fixture_observation_frame(monotonic_tick=7, source_clock="test-clock")
    f2 = build_fixture_observation_frame(monotonic_tick=7, source_clock="test-clock")
    assert f1.frame_id == f2.frame_id
    assert f1.environment_sha256 == f2.environment_sha256
    assert f1.trace_hash == f2.trace_hash
    assert {unit.pack_id for unit in f1.units} == {
        "audio_core_v1",
        "sensorimotor_core_v1",
        "vision_core_v1",
    }
    for unit in f1.units:
        assert unit.versor.shape == (32,)
        assert unit.versor.dtype == np.float32
        assert unit.versor_condition < 1e-6


def test_fixture_observation_frame_tick_changes_identity_not_unit_set():
    f1 = build_fixture_observation_frame(monotonic_tick=7)
    f2 = build_fixture_observation_frame(monotonic_tick=8)
    assert f1.trace_hash != f2.trace_hash
    assert [unit.merge_key for unit in f1.units] == [unit.merge_key for unit in f2.units]
