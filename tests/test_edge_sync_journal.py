from __future__ import annotations

from core.sync.journal import JournalDirection, JournalStatus, LocalSyncJournal


def test_append_upload_creates_pending_entry() -> None:
    journal = LocalSyncJournal()
    decision = journal.append_upload(
        entry_id="u1",
        artifact_id="trace-1",
        artifact_type="trace",
        target_uri="s3://bucket/traces/trace-1.jsonl.zst",
    )

    assert decision.accepted
    assert decision.reason == "pending"
    assert decision.entry is not None
    assert decision.entry.direction is JournalDirection.UPLOAD
    assert decision.entry.status is JournalStatus.PENDING
    assert journal.pending() == (decision.entry,)


def test_append_download_creates_pending_entry() -> None:
    journal = LocalSyncJournal()
    decision = journal.append_download(
        entry_id="d1",
        artifact_id="pack-v1",
        artifact_type="pack_release",
    )

    assert decision.accepted
    assert decision.entry is not None
    assert decision.entry.direction is JournalDirection.DOWNLOAD
    assert decision.entry.status is JournalStatus.PENDING


def test_duplicate_entry_rejects_without_overwrite() -> None:
    journal = LocalSyncJournal()
    first = journal.append_upload(entry_id="u1", artifact_id="a1", artifact_type="trace")
    second = journal.append_upload(entry_id="u1", artifact_id="a2", artifact_type="trace")

    assert first.accepted
    assert not second.accepted
    assert second.reason == "duplicate_entry_id"
    assert journal.get("u1").artifact_id == "a1"  # type: ignore[union-attr]


def test_mark_completed_preserves_entry_metadata() -> None:
    journal = LocalSyncJournal()
    journal.append_upload(entry_id="u1", artifact_id="trace-1", artifact_type="trace")
    decision = journal.mark_completed("u1")

    assert decision.accepted
    assert decision.reason == "completed"
    assert decision.entry is not None
    assert decision.entry.status is JournalStatus.COMPLETED
    assert decision.entry.artifact_id == "trace-1"
    assert journal.pending() == ()


def test_mark_failed_preserves_reason_and_increments_attempts() -> None:
    journal = LocalSyncJournal()
    journal.append_upload(entry_id="u1", artifact_id="trace-1", artifact_type="trace")
    failure = journal.mark_failed("u1", "object_store_unavailable")

    assert failure.accepted
    assert failure.entry is not None
    assert failure.entry.status is JournalStatus.FAILED
    assert failure.entry.reason == "object_store_unavailable"
    assert failure.entry.attempts == 1


def test_failed_upload_does_not_clear_journal_state() -> None:
    journal = LocalSyncJournal()
    journal.append_upload(entry_id="u1", artifact_id="trace-1", artifact_type="trace")
    journal.mark_failed("u1", "timeout")

    entry = journal.get("u1")
    assert entry is not None
    assert entry.artifact_id == "trace-1"
    assert entry.status is JournalStatus.FAILED


def test_retry_failed_entry_returns_to_pending_without_incrementing_attempts() -> None:
    journal = LocalSyncJournal()
    journal.append_upload(entry_id="u1", artifact_id="trace-1", artifact_type="trace")
    journal.mark_failed("u1", "timeout")
    retry = journal.retry("u1")

    assert retry.accepted
    assert retry.reason == "pending"
    assert retry.entry is not None
    assert retry.entry.status is JournalStatus.PENDING
    assert retry.entry.attempts == 1
    assert retry.entry.reason is None


def test_rejected_download_can_be_retried() -> None:
    journal = LocalSyncJournal()
    journal.append_download(entry_id="d1", artifact_id="pack-v1", artifact_type="pack_release")
    journal.mark_rejected("d1", "hash_mismatch")
    retry = journal.retry("d1")

    assert retry.accepted
    assert retry.entry is not None
    assert retry.entry.status is JournalStatus.PENDING
    assert retry.entry.reason is None


def test_unknown_entry_transition_rejects() -> None:
    journal = LocalSyncJournal()
    decision = journal.mark_completed("missing")

    assert not decision.accepted
    assert decision.reason == "unknown_entry"


def test_journal_serializes_to_dicts() -> None:
    journal = LocalSyncJournal()
    journal.append_upload(entry_id="u1", artifact_id="trace-1", artifact_type="trace")
    journal.mark_failed("u1", "timeout")

    payload = journal.as_dicts()
    assert payload == (
        {
            "entry_id": "u1",
            "direction": "upload",
            "artifact_id": "trace-1",
            "artifact_type": "trace",
            "status": "failed",
            "target_uri": None,
            "reason": "timeout",
            "attempts": 1,
        },
    )
