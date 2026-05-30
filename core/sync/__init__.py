"""Edge/cloud sync contracts for CORE.

This package is intentionally pure at import time: no object-store client,
no network dependency, and no hot-path integration.
"""

from core.sync.artifacts import (
    ARTIFACT_AUTHORITY,
    ArtifactAuthority,
    ArtifactType,
    authority_for,
)

__all__ = [
    "ARTIFACT_AUTHORITY",
    "ArtifactAuthority",
    "ArtifactType",
    "authority_for",
]
