"""Deterministic fixture harness for environmental observation frames."""

from __future__ import annotations

from sensorium.environment.frame import ObservationFrame, build_observation_frame

_AUDIO_FIXTURE = {"id": "env_tone", "kind": "tone", "ms": 300, "hz": 150, "sweep": 90, "amp": 0.5}
_VISION_FIXTURE = {"id": "env_corner", "kind": "corner", "size": 32}
_SENSORIMOTOR_FIXTURE = {
    "id": "env_contact",
    "pose_q": [10, -4, 3],
    "velocity_q": [2, 0, -1],
    "force_torque_q": [3, 5, 8],
    "contact_q": [1, 0, 1],
    "actuator_state_q": [7, 8],
}


def build_fixture_observation_frame(
    *,
    monotonic_tick: int = 0,
    source_clock: str = "fixture-clock",
    causal_parent_ids: tuple[str, ...] = (),
) -> ObservationFrame:
    """Build a deterministic mixed-modality ObservationFrame.

    The frame contains already-compiled afferent units only: one audio unit,
    one vision tile unit, and one sensorimotor feedback unit.
    """

    from evals.audio_sensorium.synth import synthesize as synthesize_audio
    from evals.sensorimotor_sensorium.synth import synthesize as synthesize_sensorimotor
    from evals.vision_sensorium.synth import synthesize as synthesize_vision
    from sensorium.audio.canonical import canonicalize as canonicalize_audio
    from sensorium.audio.compiler import AudioCompiler
    from sensorium.sensorimotor.compiler import SensorimotorCompiler
    from sensorium.vision import VisionCompiler, canonicalize_image
    from sensorium.vision.grid import iter_tile_signals

    audio_unit = AudioCompiler().compile_signal(
        canonicalize_audio(synthesize_audio(_AUDIO_FIXTURE), 24_000)
    )
    vision_image = canonicalize_image(synthesize_vision(_VISION_FIXTURE))
    vision_tile = iter_tile_signals(vision_image)[0]
    vision_unit = VisionCompiler().compile_tile(vision_tile)
    sensorimotor_unit = SensorimotorCompiler().compile_signal(
        synthesize_sensorimotor(_SENSORIMOTOR_FIXTURE)
    )
    return build_observation_frame(
        monotonic_tick=monotonic_tick,
        source_clock=source_clock,
        units=(audio_unit, vision_unit, sensorimotor_unit),
        causal_parent_ids=causal_parent_ids,
    )
