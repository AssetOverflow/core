"""
Lift rules for the Hebrew depth pack.

Responsibility: receive a LinguisticAnalysis from the he pack analyzer
and return a CandidatePressureBatch.

Hebrew-specific lift requirements:
  - Binyan (verb stem) must be resolved before field_target is selected.
    The same root in qal vs. hiphil may lift into different field targets.
  - Aspect (qatal/yiqtol/wayyiqtol) contributes to the pressure kind
    and temporal annotation of the candidate.
  - Construct chains must be handled as relational frames: the head
    lemma and the genitive together determine the lift target.
  - The implicit copula: when haya is absent, the copular frame is
    inferred from syntactic position, not from a present verb form.
  - bara in qal: always lifts into creation.act.ex-nihilo.
    The divine-agent constraint must be verified before this lift.

Current status:
  Blocked on LinguisticAnalysis contract (he pack specific: must carry
  binyan, aspect, and construct-chain annotations).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core_ingest.pressure import CandidateGeometricPressure


def lift(analysis: object) -> list["CandidateGeometricPressure"]:
    """
    Lift a Hebrew LinguisticAnalysis into CandidateGeometricPressure packets.

    Blocked on: he pack LinguisticAnalysis contract — must carry
    binyan, aspect, and construct-chain annotations before this
    can be implemented correctly.
    """
    raise NotImplementedError(
        "he:lift — LinguisticAnalysis contract for Hebrew not yet finalized. "
        "Must carry binyan, aspect, and construct-chain annotations."
    )
