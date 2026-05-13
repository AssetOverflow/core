"""
Readback rules for the Hebrew depth pack.

Hebrew readback produces grammatical Biblical Hebrew surface realizations
from field state. This is a depth-pack operation: it is not invoked
by default, only when the model explicitly targets Hebrew articulation.

Hebrew-specific readback requirements:
  - Verb selection must respect binyan: the field target and agent
    semantics together determine which binyan is appropriate.
  - Aspect selection is not optional: qatal, yiqtol, and wayyiqtol
    carry distinct temporal and narrative semantics.
  - Nikud (vowel points) must be produced, not left unpointed.
    Unpointed output is not a valid surface realization for this pack.
  - Construct chains must be assembled correctly: head in construct
    state, genitive following, no article on the construct head.
  - The implicit copula must be handled: in nominal clauses, haya
    is omitted in the present tense unless emphasis requires it.

Current status:
  Blocked on FieldState and SurfaceRealization types.
"""

from __future__ import annotations


def readback(field_state: object, intent: object = None) -> object:
    """
    Produce a grammatical Hebrew surface realization from a field state.

    Blocked on: FieldState and SurfaceRealization types.
    When implemented: must produce fully pointed (nikud) Hebrew output.
    """
    raise NotImplementedError(
        "he:readback — FieldState and SurfaceRealization types not yet "
        "finalized. When implemented: output must be fully pointed Hebrew "
        "with correct binyan, aspect, and construct-chain handling."
    )
