"""
Lift rules for the English base pack.

Responsibility: receive a LinguisticAnalysis produced by the en pack normalizer
and analyzer, and return a CandidatePressureBatch — a list of
CandidateGeometricPressure packets ready for the IngestCompiler.

Design constraints:
  - Deterministic: identical input always produces identical output.
  - Lemma-first: lift targets are resolved through lemma_id → sense_id,
    not through surface-form heuristics.
  - Shared field target: every field_target must be a recognized CORE
    field primitive. No private semantic space.
  - This file must not import or invoke any external model or API.
    Lift is a deterministic, structure-driven operation.

Current status:
  The normalize() and analyze() interfaces are not yet fully specified
  for the en pack. Lift is blocked until those contracts are finalized
  and the LinguisticAnalysis type is stable.

  Raise NotImplementedError at the exact boundary that is not yet designed
  rather than producing silent or approximate output.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core_ingest.pressure import CandidateGeometricPressure


def lift(analysis: object) -> list["CandidateGeometricPressure"]:
    """
    Lift a LinguisticAnalysis from the en pack into a list of
    CandidateGeometricPressure packets.

    Blocked on: finalization of the LinguisticAnalysis contract
    and the CandidateGeometricPressure construction interface.
    """
    raise NotImplementedError(
        "en:lift — LinguisticAnalysis contract not yet finalized. "
        "Implement after analyze() and CandidateGeometricPressure "
        "construction interface are locked."
    )
