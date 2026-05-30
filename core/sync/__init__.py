"""Edge/cloud sync contracts for CORE.

This package is intentionally pure at import time: no object-store client,
no network dependency, and no hot-path integration.
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
    "SyncManifest",
    "authority_for",
    "parse_manifest",
    "validate_manifest",
]
