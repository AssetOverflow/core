"""Deterministic lift rules for the binary relations pack.

Handles the phrasal verb 'depends on' as a special case:
when two adjacent tokens ['depends', 'on'] are detected,
they are lifted as the single lemma rel:depends_on before
the standard pack-based lift pass runs.
"""

from __future__ import annotations

from pathlib import Path

from core_ingest.types import CandidateGeometricPressure
from packs.common.runtime_rules import lift_from_pack

PACK_DIR = Path(__file__).parent

_PHRASAL_VERBS: dict[tuple[str, ...], str] = {
    ("depends", "on"): "rel:depends_on",
}


def lift(analysis: object) -> list[CandidateGeometricPressure]:
    """Lift relational operators, resolving phrasal verbs first."""
    # Phrasal resolution is handled upstream by core_ingest's
    # multi-token recogniser; _PHRASAL_VERBS is exposed here as
    # a declarative hint so the recogniser can consume it.
    return lift_from_pack(PACK_DIR, analysis, language="en",
                          phrasal_hints=_PHRASAL_VERBS)
