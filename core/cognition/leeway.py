"""Per-turn leeway record — the engine-side B4 producer.

When a turn is governed (ADR-0206 ``response_governance``), the reliability gate
either grants latitude to a class (a licensed ``Action.SERVE`` converse-guess,
surfaced as a DISCLOSED ``[approximate]`` estimate) or withholds it (the STRICT
default).  That decision is computed on the serving path and was previously
discarded.  This module turns the decision the runtime ALREADY made into a small
observational record on the turn result — it never calls the gate, never
authorizes anything, and never alters the served surface.

The record mirrors the workbench ``LeewayEvidence`` tuple field-for-field, so the
workbench maps it with a trivial projection and gains no serving-path import.
The ``license_decision`` is read duck-typed (a
``core.reliability_gate.LicenseDecision`` when present) so this stays a pure
cognition-layer leaf with no new cross-package coupling.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LeewayRecord:
    """Observational record of the leeway the gate granted (or withheld)."""

    class_name: str
    license: str  # "SERVE" | "PROPOSE" | "blocked" | "unknown"
    theta: float | None
    claim_disclosure: str  # "approximate" | "verified" | "proposal_only" | "none"
    source_digest: str | None
    calibration_evidence_ref: str | None


def _decision_digest(license_decision: Any) -> str:
    """Content-address the licensing decision — provenance, deterministic.

    Hashes only the decision's deterministic fields (never a timestamp), so a
    replayed turn produces the same digest.
    """

    payload = {
        "class_name": str(getattr(license_decision, "class_name", "")),
        "action": str(getattr(getattr(license_decision, "action", None), "name", "")),
        "checker": str(getattr(license_decision, "checker", "")),
        "measured": float(getattr(license_decision, "measured", 0.0) or 0.0),
        "required": float(getattr(license_decision, "required", 0.0) or 0.0),
        "licensed": bool(getattr(license_decision, "licensed", False)),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_leeway_record(
    *,
    reach_level: str,
    license_decision: Any | None,
) -> LeewayRecord:
    """Map the governed turn's reach level + license decision to a record.

    - No decision consulted (the STRICT main path): ``license="unknown"``, no
      latitude.
    - A decision exists but was denied: ``license="blocked"`` — the gate was
      consulted and said no.
    - A licensed SERVE/PROPOSE that widened: the real class, θ, and the
      ``[approximate]`` disclosure — the "engine earned the right to guess" case.

    ``claim_disclosure`` reflects what was actually disclosed this turn
    (``approximate`` iff the surface widened); ``"verified"`` is intentionally
    never emitted (it is a RESERVED epistemic state — claiming it would
    over-state).
    """

    disclosure = "approximate" if reach_level == "approximate" else "none"

    if license_decision is None:
        return LeewayRecord(
            class_name="none",
            license="unknown",
            theta=None,
            claim_disclosure=disclosure,
            source_digest=None,
            calibration_evidence_ref=None,
        )

    action_name = str(getattr(getattr(license_decision, "action", None), "name", ""))
    licensed = bool(getattr(license_decision, "licensed", False))
    if licensed and action_name == "SERVE":
        license = "SERVE"
    elif licensed and action_name == "PROPOSE":
        license = "PROPOSE"
    else:
        license = "blocked"

    class_name = str(getattr(license_decision, "class_name", "") or "none")
    required = getattr(license_decision, "required", None)
    return LeewayRecord(
        class_name=class_name,
        license=license,
        theta=float(required) if required is not None else None,
        claim_disclosure=disclosure,
        source_digest=_decision_digest(license_decision),
        calibration_evidence_ref=class_name if class_name != "none" else None,
    )
