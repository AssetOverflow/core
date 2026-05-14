"""
Readback rules for the Koine Greek depth pack.

Koine Greek readback produces grammatical Biblical Greek surface realizations.
This is a depth-pack operation invoked only when the model targets Greek articulation.

Koine Greek-specific readback requirements:
  - Full inflection: case, number, gender on nouns/adjectives/articles;
    tense, voice, mood, person, number on verbs. Every word fully inflected.
  - Accent placement: Greek accents must be placed correctly.
    Unaccented output is not a valid surface realization.
  - Article resolution: the article must be present or absent based on
    the semantic role of the noun in the clause. Anarthrous predicates
    in copular constructions must remain anarthrous (Colwell).
  - Aspect selection: aorist vs. imperfect vs. perfect is not stylistic.
    Each carries distinct semantic content that must be honored.

Current status:
  Blocked on FieldState and SurfaceRealization types.
"""

from __future__ import annotations


def readback(field_state: object, intent: object = None) -> object:
    """
    Produce a grammatical Koine Greek surface realization from a field state.

    Blocked on: FieldState and SurfaceRealization types.
    When implemented: must produce fully inflected and accented Greek output
    with correct article placement and tense-aspect selection.
    """
    raise NotImplementedError(
        "el:readback — FieldState and SurfaceRealization types not yet "
        "finalized. When implemented: output must be fully inflected Koine Greek "
        "with correct accent placement, article resolution, and aspect selection."
    )
