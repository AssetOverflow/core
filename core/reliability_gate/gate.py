"""ADR-0175 §3 — the deterministic attempt/refuse gate.

``license_for`` decides whether an action is permitted for a class:

    measured_reliability(class) / θ_required(action, class) ≥ 1

Equivalently ``measured ≥ required`` (and ``required == 0`` -> always licensed),
which avoids a divide-by-zero on the sealed-practice ceiling. The ratio is kept
as an inspectable field. Pure and deterministic: never mutates or emits the
``Ceilings`` it is given (invariant #4), identical inputs -> identical decision
(invariant #3).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.reliability_gate.ceilings import Action, Ceilings
from core.reliability_gate.ledger import ClassTally

# Which earned number gates an action.
_CHECKERS: frozenset[str] = frozenset({"reliability", "t2_precision"})


@dataclass(frozen=True, slots=True)
class LicenseDecision:
    """Inspectable result of the gate. Carries the numbers behind the verdict."""

    class_name: str
    action: Action
    checker: str
    measured: float
    required: float
    ratio: float  # measured / required; +inf when required == 0
    licensed: bool


def license_for(
    tally: ClassTally,
    action: Action,
    ceilings: Ceilings,
    *,
    checker: str = "reliability",
) -> LicenseDecision:
    """Decide whether ``action`` is licensed for ``tally``'s class.

    ``checker`` selects the earned number that gates this action:
    ``"reliability"`` (commitment precision) or ``"t2_precision"`` (Tier-2
    self-verification trust, used for widening past gold).
    """
    if checker not in _CHECKERS:
        raise ValueError(f"unknown checker {checker!r}; expected one of {sorted(_CHECKERS)}")
    measured = tally.reliability if checker == "reliability" else tally.t2_precision
    required = ceilings.required(tally.class_name, action)

    if required <= 0.0:
        licensed = True
        ratio = float("inf")
    else:
        # measured / required ≥ 1  ⟺  measured ≥ required (both pre-rounded to 1e-9)
        licensed = round(measured, 9) >= round(required, 9)
        ratio = round(measured / required, 9)

    return LicenseDecision(
        class_name=tally.class_name,
        action=action,
        checker=checker,
        measured=measured,
        required=required,
        ratio=ratio,
        licensed=licensed,
    )
