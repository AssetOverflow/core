"""Deterministic lift rules for the English base pack."""

from __future__ import annotations

from pathlib import Path

from core_ingest.types import CandidateGeometricPressure
from packs.common.runtime_rules import lift_from_pack

PACK_DIR = Path(__file__).parent


def lift(analysis: object) -> list[CandidateGeometricPressure]:
    return lift_from_pack(PACK_DIR, analysis, language="en")
