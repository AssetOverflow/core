"""ADR-0175 §3 — human-set required-reliability ceilings (θ).

``θ`` is the per-class, per-action reliability an action *demands* before it is
licensed. These are the **human autonomy dial**, distinct from the global
estimator skepticism :data:`core.reliability_gate.floor.WILSON_Z`.

Invariant #4 — the engine never raises its own ceiling. Enforced structurally:
:class:`Ceilings` is frozen (no in-place mutation), and "raising a ceiling" via
:meth:`with_override` returns a NEW instance — an explicit reconstruction that
models a human editing config, never engine self-authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, Mapping


class Action(Enum):
    """The blast-radius of what a passed gate licenses (ADR-0175 §3)."""

    PRACTICE = "practice"  # sealed; θ = 0 -> always attempt
    PROPOSE = "propose"  # emit a ratifiable proposal
    SERVE = "serve"  # touch a served answer


# Global default ceilings. PRACTICE = 0.0 (sealed practice always attempts).
_DEFAULTS: Final[Mapping[Action, float]] = {
    Action.PRACTICE: 0.0,
    Action.PROPOSE: 0.85,
    Action.SERVE: 0.99,
}


@dataclass(frozen=True, slots=True)
class Ceilings:
    """Immutable θ table: global defaults + explicit per-(class, action) overrides."""

    overrides: tuple[tuple[str, Action, float], ...] = ()

    def required(self, class_name: str, action: Action) -> float:
        """θ for this class+action — an override if present, else the global default."""
        for cls, act, theta in self.overrides:
            if cls == class_name and act == action:
                return theta
        return _DEFAULTS[action]

    def with_override(self, class_name: str, action: Action, theta: float) -> "Ceilings":
        """Return a NEW Ceilings with this ceiling set (immutable; not in-place).

        θ must be in ``[0.0, 1.0)`` — a ceiling of 1.0 is unreachable by the
        floor (no finite record proves perfection), so it is rejected as a
        configuration error rather than silently making an action impossible.
        """
        if not (0.0 <= theta < 1.0):
            raise ValueError("θ must be in [0.0, 1.0)")
        kept = tuple(
            o for o in self.overrides if not (o[0] == class_name and o[1] == action)
        )
        return Ceilings(kept + ((class_name, action, theta),))

    @classmethod
    def default(cls) -> "Ceilings":
        """The global-default ceilings with no per-class overrides."""
        return cls()
