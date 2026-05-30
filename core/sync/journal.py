"""Local sync journal for edge/cloud artifact transfer state.

The journal is deliberately local and transport-agnostic.  It records pending
uploads/downloads and their outcomes without blocking active reasoning,
refusal, safety, or action gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class JournalDirection(str, Enum):
    """Direction of a sync journal entry."""

    UPLOAD = "upload"
    DOWNLOAD = "download"


class JournalStatus(str, Enum):
    """Lifecycle status for a sync journal entry."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """One local sync work item or outcome."""

    entry_id: str
    direction: JournalDirection
    artifact_id: str
    artifact_type: str
    status: JournalStatus = JournalStatus.PENDING
    target_uri: str | None = None
    reason: str | None = None
    attempts: int = 0


@dataclass(frozen=True, slots=True)
class JournalDecision:
    """Result of mutating the local journal."""

    accepted: bool
    reason: str
    entry: JournalEntry | None = None


@dataclass(slots=True)
class LocalSyncJournal:
    """In-memory local journal for sync work.

    A later file-backed journal can implement the same semantics.  This first
    version proves the contract: sync failures are recorded locally and never
    imply hot-path failure or active release mutation.
    """

    _entries: dict[str, JournalEntry] = field(default_factory=dict)

    def append_upload(
        self,
        *,
        entry_id: str,
        artifact_id: str,
        artifact_type: str,
        target_uri: str | None = None,
    ) -> JournalDecision:
        return self._append(
            entry_id=entry_id,
            direction=JournalDirection.UPLOAD,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            target_uri=target_uri,
        )

    def append_download(
        self,
        *,
        entry_id: str,
        artifact_id: str,
        artifact_type: str,
        target_uri: str | None = None,
    ) -> JournalDecision:
        return self._append(
            entry_id=entry_id,
            direction=JournalDirection.DOWNLOAD,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            target_uri=target_uri,
        )

    def mark_acknowledged(self, entry_id: str) -> JournalDecision:
        return self._transition(entry_id, JournalStatus.ACKNOWLEDGED, "acknowledged")

    def mark_completed(self, entry_id: str) -> JournalDecision:
        return self._transition(entry_id, JournalStatus.COMPLETED, "completed")

    def mark_rejected(self, entry_id: str, reason: str) -> JournalDecision:
        return self._transition(entry_id, JournalStatus.REJECTED, reason)

    def mark_failed(self, entry_id: str, reason: str) -> JournalDecision:
        return self._transition(entry_id, JournalStatus.FAILED, reason, increment_attempts=True)

    def retry(self, entry_id: str) -> JournalDecision:
        entry = self._entries.get(entry_id)
        if entry is None:
            return JournalDecision(False, "unknown_entry")
        if entry.status not in {JournalStatus.FAILED, JournalStatus.REJECTED}:
            return JournalDecision(False, "retry_not_needed", entry)
        retried = JournalEntry(
            entry_id=entry.entry_id,
            direction=entry.direction,
            artifact_id=entry.artifact_id,
            artifact_type=entry.artifact_type,
            status=JournalStatus.PENDING,
            target_uri=entry.target_uri,
            reason=None,
            attempts=entry.attempts,
        )
        self._entries[entry_id] = retried
        return JournalDecision(True, "pending", retried)

    def get(self, entry_id: str) -> JournalEntry | None:
        return self._entries.get(entry_id)

    def pending(self) -> tuple[JournalEntry, ...]:
        return tuple(entry for entry in self._entries.values() if entry.status is JournalStatus.PENDING)

    def entries(self) -> tuple[JournalEntry, ...]:
        return tuple(self._entries.values())

    def as_dicts(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "entry_id": entry.entry_id,
                "direction": entry.direction.value,
                "artifact_id": entry.artifact_id,
                "artifact_type": entry.artifact_type,
                "status": entry.status.value,
                "target_uri": entry.target_uri,
                "reason": entry.reason,
                "attempts": entry.attempts,
            }
            for entry in self._entries.values()
        )

    def _append(
        self,
        *,
        entry_id: str,
        direction: JournalDirection,
        artifact_id: str,
        artifact_type: str,
        target_uri: str | None,
    ) -> JournalDecision:
        if not entry_id:
            return JournalDecision(False, "missing_entry_id")
        if entry_id in self._entries:
            return JournalDecision(False, "duplicate_entry_id", self._entries[entry_id])
        entry = JournalEntry(
            entry_id=entry_id,
            direction=direction,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            target_uri=target_uri,
        )
        self._entries[entry_id] = entry
        return JournalDecision(True, "pending", entry)

    def _transition(
        self,
        entry_id: str,
        status: JournalStatus,
        reason: str,
        *,
        increment_attempts: bool = False,
    ) -> JournalDecision:
        entry = self._entries.get(entry_id)
        if entry is None:
            return JournalDecision(False, "unknown_entry")
        updated = JournalEntry(
            entry_id=entry.entry_id,
            direction=entry.direction,
            artifact_id=entry.artifact_id,
            artifact_type=entry.artifact_type,
            status=status,
            target_uri=entry.target_uri,
            reason=reason,
            attempts=entry.attempts + 1 if increment_attempts else entry.attempts,
        )
        self._entries[entry_id] = updated
        return JournalDecision(True, reason, updated)
