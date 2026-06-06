"""Operator registry for vision_event_core_v1."""

from __future__ import annotations

from sensorium.vision.operators import VisionOperatorRegistry, VisionOperatorSpec


def _spec(op_id, etype, alias, blade, base, gains, clip=768) -> VisionOperatorSpec:
    return VisionOperatorSpec(op_id, etype, alias, blade, base, tuple(gains), clip)


DEFAULT_EVENT_OPERATOR_REGISTRY = VisionOperatorRegistry(
    {
        "event.onset": _spec(
            "vision_event.onset.v1",
            "event.onset",
            "B_EVENT_ONSET",
            6,
            36,
            [("polarity_q", 7), ("t_bin", 2), ("x_q", 1), ("y_q", 1)],
        ),
        "event.decay": _spec(
            "vision_event.decay.v1",
            "event.decay",
            "B_EVENT_DECAY",
            7,
            44,
            [("polarity_q", -7), ("t_bin", 2), ("x_q", 1), ("y_q", 1)],
        ),
        "event.motion_delta": _spec(
            "vision_event.motion_delta.v1",
            "event.motion_delta",
            "B_EVENT_MOTION",
            8,
            72,
            [("balance_q", 3), ("count_q", 5), ("t_bin", 2)],
        ),
    },
    basis_version="vision-event-basis-v1",
)


__all__ = ["DEFAULT_EVENT_OPERATOR_REGISTRY"]
