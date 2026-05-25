from __future__ import annotations

from collections.abc import Sequence

from .envelope import CtpEnvelope


class ReplayViolation(ValueError):
    """Raised when a CTP event or chain cannot be replay-verified."""


def verify_event(event: CtpEnvelope) -> None:
    try:
        event.validate()
    except ValueError as exc:
        raise ReplayViolation(str(exc)) from exc


def verify_chain(events: Sequence[CtpEnvelope]) -> None:
    previous_id = ""
    previous_sequence = -1
    for idx, event in enumerate(events):
        verify_event(event)
        if event.sequence < previous_sequence:
            raise ReplayViolation("CTP event sequence regressed")
        if idx > 0 and event.causation_id and event.causation_id != previous_id:
            raise ReplayViolation(
                f"CTP causation break at index {idx}: expected {previous_id}, got {event.causation_id}"
            )
        previous_id = event.message_id or event.computed_message_id()
        previous_sequence = event.sequence
