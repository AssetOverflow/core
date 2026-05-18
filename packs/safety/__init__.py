"""Safety-pack loader.

Reads the single shipping safety pack and returns its boundary set for
composition into the runtime ``IdentityManifold``.  Safety packs are
**not** swappable: there is exactly one safety pack per installation,
loaded unconditionally.

The loader fails closed.  Missing file, malformed JSON, empty
``boundary_ids``, or — in production mode — unverified self-seal all
cause ``SafetyPackError`` and prevent ``ChatRuntime`` startup.

See ``docs/decisions/ADR-0029-safety-packs.md``.
"""

from packs.safety.loader import (
    DEFAULT_SAFETY_PACK,
    SafetyPack,
    SafetyPackError,
    load_safety_pack,
)

__all__ = [
    "DEFAULT_SAFETY_PACK",
    "SafetyPack",
    "SafetyPackError",
    "load_safety_pack",
]
