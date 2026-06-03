"""ADR-0206 — Response Governance Bridge (scaffold).

The consumption bridge that lets CORE's two *built* epistemic substrates —
the ratified decode-state taxonomy (:mod:`core.epistemic_state`) and the
deterministic risk-reward gate (:mod:`core.reliability_gate`) — govern how a
response is shaped.  Today that loop has **no consumer** (see ADR-0206 §1);
this package is its first, honestly-inert beginning.

Scaffold contract (ADR-0206 §3):

- :func:`govern_response` always returns :data:`STRICT_POLICY`.  The
  stakes-weighing / license-gated widening logic is *designed* in the ADR
  and intentionally **not built**.
- :func:`shape_surface` is the IDENTITY transform at
  :attr:`ReachLevel.STRICT` — the only level emitted today — so wiring it
  into the response path is byte-identical to the pre-bridge path.

The seam is therefore **live wiring held strict by exactly one return
value** (the stub's STRICT), not dead code.  ``wrong == 0`` is preserved
because nothing widens: the math serving chokepoint
(``select_self_verified``) is untouched by this PR (deferred to its own
PR per ADR-0206 §5).
"""

from __future__ import annotations

from core.response_governance.policy import (
    ACTIVE_STATES,
    RECONCILE_STATES,
    RESERVED_STATES,
    STRICT_POLICY,
    ReachLevel,
    ReachPolicy,
    govern_response,
    shape_surface,
)

__all__ = [
    "ACTIVE_STATES",
    "RECONCILE_STATES",
    "RESERVED_STATES",
    "STRICT_POLICY",
    "ReachLevel",
    "ReachPolicy",
    "govern_response",
    "shape_surface",
]
