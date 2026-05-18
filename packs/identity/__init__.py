"""Identity packs — on-disk, content-addressed IdentityManifolds.

See ``docs/identity_packs.md`` for the pack format, loader contract, and
authoring guide.  See ``docs/decisions/ADR-0027-identity-packs.md`` for
the decision record.
"""

from packs.identity.loader import (
    IdentityPackError,
    available_packs,
    load_identity_manifold,
)

__all__ = ["IdentityPackError", "available_packs", "load_identity_manifold"]
