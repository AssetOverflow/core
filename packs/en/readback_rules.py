"""
Readback rules for the English base pack.

Responsibility: receive a resolved field state (or a field state fragment
with a stated communicative intent) and produce a grammatical English
surface realization.

Design constraints:
  - Readback is pack-local. This file does not reach into he or el rules.
  - Grammatical agreement is fully handled here: number, tense, mood.
  - Ambiguity resolution is deterministic: when multiple lemmas could
    express the same field target, rank and constraint matching decide.
  - This file must not invoke any external model or API.

Current status:
  Readback requires the FieldState type and the SurfaceRealization
  return type to be stable. Both are blocked on the field primitive
  specification work in the core field layer.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def readback(field_state: object, intent: object = None) -> object:
    """
    Produce a grammatical English surface realization from a field state.

    Blocked on: FieldState type and SurfaceRealization interface.
    """
    raise NotImplementedError(
        "en:readback — FieldState and SurfaceRealization types not yet "
        "finalized. Implement after the core field primitive layer is locked."
    )
