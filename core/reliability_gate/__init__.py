"""ADR-0175 Phase 1 — reliability ledger + attempt/refuse gate substrate.

Standalone, deterministic, replay-stable. NOT wired into the serving/eval path
(invariant #1: zero serving change). NOT the `calibration/` module (that is a
grid-search hyperparameter tuner; this is the per-class reliability ledger).

Public surface:
- :func:`conservative_floor`, :data:`WILSON_Z`, :data:`N_MIN` — the pinned floor.
- :class:`ClassTally` — per-class counted ledger; reliability = commitment precision.
- :class:`Action`, :class:`Ceilings` — human-set θ ceilings (engine never mutates).
- :func:`license_for`, :class:`LicenseDecision` — the deterministic gate.
"""

from __future__ import annotations

from core.reliability_gate.ceilings import Action, Ceilings
from core.reliability_gate.floor import N_MIN, WILSON_Z, conservative_floor
from core.reliability_gate.gate import LicenseDecision, license_for
from core.reliability_gate.ledger import ClassTally
from core.reliability_gate.propose import RatifiableProposal, propose_from_ledger

__all__ = [
    "Action",
    "Ceilings",
    "ClassTally",
    "LicenseDecision",
    "N_MIN",
    "RatifiableProposal",
    "WILSON_Z",
    "conservative_floor",
    "license_for",
    "propose_from_ledger",
]
