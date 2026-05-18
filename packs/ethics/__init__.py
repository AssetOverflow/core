"""Ethics packs — ADR-0033.

Domain-specific ethical commitments composed into the runtime manifold
alongside identity (swappable) and safety (always-loaded).  Ethics
packs are swappable like identity packs but contribute *commitments*
(propositional pledges) rather than *value axes* (geometric directions)
or *boundaries* (universal red lines).

See ``docs/decisions/ADR-0033-ethics-packs.md``.
"""

from packs.ethics.check import (
    EthicsCheck,
    EthicsCheckResult,
    EthicsContext,
    EthicsPredicate,
    EthicsVerdict,
)
from packs.ethics.loader import (
    DEFAULT_ETHICS_PACK,
    EthicsPack,
    EthicsPackError,
    available_packs,
    load_ethics_pack,
)

__all__ = [
    "DEFAULT_ETHICS_PACK",
    "EthicsCheck",
    "EthicsCheckResult",
    "EthicsContext",
    "EthicsPack",
    "EthicsPackError",
    "EthicsPredicate",
    "EthicsVerdict",
    "available_packs",
    "load_ethics_pack",
]
