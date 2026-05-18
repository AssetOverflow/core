"""ADR-0039 — unified per-turn verdict bundle.

Three orthogonal verdict surfaces fire on every turn:

* ``IdentityScore`` — geometric alignment against the manifold.
* ``SafetyVerdict`` — universal-floor boundary predicates.
* ``EthicsVerdict`` — deployment-commitment predicates.

Plus two remediation flags captured by the runtime:

* ``refusal_emitted`` — typed refusal replaced the surface this turn.
* ``hedge_injected`` — manifold's hedge phrase was prepended.

The bundle is a convenience aggregate.  The individual fields remain
on ``ChatResponse`` and ``TurnEvent`` for back-compat with callers
written against ADR-0035 / ADR-0036; the bundle is the new single
accessor for downstream telemetry and audit consumers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TurnVerdicts:
    """Single-turn verdict bundle.

    Fields are typed as ``object`` to avoid coupling this module's
    consumers to the concrete packs.* and core.physics.identity
    types at import time.  Callers that need the concrete shape
    downcast at use site — same discipline ``TurnEvent`` uses.

    The two remediation flags are derived from the surface that was
    actually emitted:

    * ``refusal_emitted=True`` iff the response surface is a typed
      refusal (ADR-0036 / ADR-0037).
    * ``hedge_injected=True`` iff a hedge phrase was prepended this
      turn (ADR-0038).

    The two are mutually exclusive: refusal supersedes hedge.
    """

    identity_score: object
    safety_verdict: object
    ethics_verdict: object
    refusal_emitted: bool
    hedge_injected: bool
