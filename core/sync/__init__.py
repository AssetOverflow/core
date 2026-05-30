"""Edge/cloud sync contracts for CORE.

This package is intentionally pure at import time: no concrete object-store
client, no network dependency, and no hot-path integration.  Concrete S3 support
is optional and lazy-imports provider SDKs only when constructed.
"""

from core.sync.activation import ActivationDecision, ActivationLedger, ActivationRecord
from core.sync.artifacts import (
    ARTIFACT_AUTHORITY,
    ArtifactAuthority,
    ArtifactType,
    authority_for,
)
from core.sync.journal import (
    JournalDecision,
    JournalDirection,
    JournalEntry,
    JournalStatus,
    LocalSyncJournal,
)
from core.sync.manifest import ManifestCheck, SyncManifest, parse_manifest, validate_manifest
from core.sync.object_store import ObjectMetadata, ObjectNotFoundError, ObjectStore, ObjectStoreError
from core.sync.s3_store import S3ObjectStore

__all__ = [
    "ARTIFACT_AUTHORITY",
    "ActivationDecision",
    "ActivationLedger",
    "ActivationRecord",
    "ArtifactAuthority",
    "ArtifactType",
    "JournalDecision",
    "JournalDirection",
    "JournalEntry",
    "JournalStatus",
    "LocalSyncJournal",
    "ManifestCheck",
    "ObjectMetadata",
    "ObjectNotFoundError",
    "ObjectStore",
    "ObjectStoreError",
    "S3ObjectStore",
    "SyncManifest",
    "authority_for",
    "parse_manifest",
    "validate_manifest",
]
