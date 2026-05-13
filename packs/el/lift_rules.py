"""
Lift rules for the Koine Greek depth pack.

Responsibility: receive a LinguisticAnalysis from the el pack analyzer
and return a CandidatePressureBatch.

Koine Greek-specific lift requirements:
  - Tense-aspect: Greek tense encodes both time and aspect. The imperfect
    of eimi (en) lifts into existence.state.continuous, not existence.state.
    The aorist would lift into existence.event. These are not interchangeable.
  - Article system: the presence or absence of the article on a predicate
    nominative is semantically load-bearing (Colwell construction).
    Anarthrous predicate nominatives must lift with a qualitative tag.
  - Voice: middle voice is not passive. Middle voice lifts carry a
    reflexive or self-involving semantic that must be preserved.
  - Pros with accusative: lifts into relation.presence-toward,
    not relation.accompaniment. The preposition selects the sense.

Current status:
  Blocked on LinguisticAnalysis contract (el pack specific: must carry
  full tense-aspect-voice-mood bundle and article resolution).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core_ingest.pressure import CandidateGeometricPressure


def lift(analysis: object) -> list["CandidateGeometricPressure"]:
    """
    Lift a Greek LinguisticAnalysis into CandidateGeometricPressure packets.

    Blocked on: el pack LinguisticAnalysis contract — must carry
    tense-aspect-voice-mood bundle and article resolution (arthrous/anarthrous)
    before this can be implemented correctly.
    """
    raise NotImplementedError(
        "el:lift — LinguisticAnalysis contract for Koine Greek not yet finalized. "
        "Must carry tense, aspect, voice, mood, and article resolution."
    )
