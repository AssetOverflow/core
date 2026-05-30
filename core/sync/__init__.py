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
from core.sync.manifest import ManifestCheck, SyncManifest, parse_manifest, validate_manifest

__all__ = [
    "ARTIFACT_AUTHORITY",
    "ArtifactAuthority",
    "ArtifactType",
    "ManifestCheck",
    "SyncManifest",
    "authority_for",
    "parse_manifest",
    "validate_manifest",
]
