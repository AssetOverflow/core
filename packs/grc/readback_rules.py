"""Deterministic readback rules for the Koine Greek depth pack."""

from __future__ import annotations

from packs.common.runtime_rules import SurfaceRealization, readback_from_intent


def readback(field_state: object, intent: object = None) -> SurfaceRealization:
    return readback_from_intent(field_state, intent, language="grc")
