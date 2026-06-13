"""Append-only Workbench turn evidence journal."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from workbench.schemas import (
    ChatTurnResult,
    CognitivePipelineRecord,
    FieldEvidence,
    TraceIntegrity,
    to_data,
    utc_now,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOURNAL_DIR = REPO_ROOT / "workbench_data"
JOURNAL_FILENAME = "turn_journal.jsonl"
PROMPT_EXCERPT_CHARS = 120
SURFACE_EXCERPT_CHARS = 120


@dataclass(frozen=True, slots=True)
class TurnJournalSummary:
    turn_id: int
    timestamp: str
    prompt_excerpt: str
    surface_excerpt: str
    trace_hash: str | None
    grounding_source: str
    trace_integrity: TraceIntegrity


@dataclass(frozen=True, slots=True)
class TurnJournalEntry:
    turn_id: int
    timestamp: str
    trace_hash: str | None
    prompt: str
    surface: str
    articulation_surface: str | None
    walk_surface: str | None
    grounding_source: str
    epistemic_state: str
    normative_clearance: str
    verdicts: dict[str, Any]
    refusal_emitted: bool
    hedge_injected: bool
    proposal_candidates: list[dict[str, Any]]
    turn_cost_ms: int
    checkpoint_emitted: bool
    leeway_evidence: dict[str, Any] | None = None
    pipeline_record: CognitivePipelineRecord | dict[str, Any] | None = None
    field_evidence: FieldEvidence | dict[str, Any] | None = None
    trace_integrity: TraceIntegrity | None = None
    journal_digest: str = ""

    def __post_init__(self) -> None:
        integrity = self.trace_integrity or _trace_integrity_for_hash(self.trace_hash)
        object.__setattr__(self, "trace_integrity", integrity)

    @classmethod
    def from_chat_turn(
        cls,
        result: ChatTurnResult,
        *,
        turn_id: int,
        timestamp: str | None = None,
    ) -> "TurnJournalEntry":
        return cls(
            turn_id=turn_id,
            timestamp=timestamp or utc_now(),
            trace_hash=result.trace_hash,
            prompt=result.prompt,
            surface=result.surface,
            articulation_surface=result.articulation_surface,
            walk_surface=result.walk_surface,
            grounding_source=result.grounding_source,
            epistemic_state=result.epistemic_state,
            normative_clearance=result.normative_clearance,
            verdicts={
                "identity": to_data(result.identity_verdict),
                "safety": to_data(result.safety_verdict),
                "ethics": to_data(result.ethics_verdict),
            },
            refusal_emitted=result.refusal_emitted,
            hedge_injected=result.hedge_injected,
            proposal_candidates=[
                candidate for candidate in to_data(result.proposal_candidates)
            ],
            turn_cost_ms=result.turn_cost_ms,
            checkpoint_emitted=result.checkpoint_emitted,
            leeway_evidence=to_data(result.leeway_evidence),
            pipeline_record=to_data(result.pipeline_record),
            field_evidence=to_data(result.field_evidence),
            trace_integrity=_trace_integrity_for_hash(result.trace_hash),
        )

    def summary(self) -> TurnJournalSummary:
        return TurnJournalSummary(
            turn_id=self.turn_id,
            timestamp=self.timestamp,
            prompt_excerpt=self.prompt[:PROMPT_EXCERPT_CHARS],
            surface_excerpt=self.surface[:SURFACE_EXCERPT_CHARS],
            trace_hash=self.trace_hash,
            grounding_source=self.grounding_source,
            trace_integrity=self.trace_integrity
            or _trace_integrity_for_hash(self.trace_hash),
        )


class TurnJournal:
    """Pure JSONL append/read model for Workbench chat evidence."""

    def __init__(self, journal_dir: Path = DEFAULT_JOURNAL_DIR) -> None:
        self._journal_dir = _validate_journal_dir(journal_dir)
        self._path = self._journal_dir / JOURNAL_FILENAME
        self._lock = threading.Lock()

    @property
    def journal_dir(self) -> Path:
        return self._journal_dir

    @property
    def path(self) -> Path:
        return self._path

    def next_turn_id(self) -> int:
        entries = self._read_entries()
        if not entries:
            return 1
        return max(entry.turn_id for entry in entries) + 1

    def append(self, entry: TurnJournalEntry) -> TurnJournalEntry:
        with self._lock:
            expected = self.next_turn_id()
            if entry.turn_id != expected:
                raise ValueError(
                    f"turn_id must be next sequential id {expected}, got {entry.turn_id}"
                )
            sealed = replace(entry, journal_digest=_journal_digest(entry))
            self._journal_dir.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(_canonical_json(to_data(sealed)))
                fh.write("\n")
            return sealed

    def list_summaries(
        self, *, limit: int = 50, offset: int = 0
    ) -> list[TurnJournalSummary]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        entries = self._read_entries()
        return [entry.summary() for entry in entries[offset : offset + limit]]

    def list_entries(
        self, *, limit: int = 50, offset: int = 0
    ) -> list[TurnJournalEntry]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        entries = self._read_entries()
        return entries[offset : offset + limit]

    def get_entry(self, turn_id: int) -> TurnJournalEntry:
        for entry in self._read_entries():
            if entry.turn_id == turn_id:
                return entry
        raise FileNotFoundError(str(turn_id))

    def _read_entries(self) -> list[TurnJournalEntry]:
        if not self._path.exists():
            return []
        entries: list[TurnJournalEntry] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                payload = json.loads(line)
                entries.append(TurnJournalEntry(**payload))
        return entries


def _validate_journal_dir(journal_dir: Path) -> Path:
    resolved = journal_dir.resolve()
    if resolved.name != "workbench_data":
        raise ValueError("journal directory must be named workbench_data")
    return resolved


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _trace_integrity_for_hash(trace_hash: str | None) -> TraceIntegrity:
    return "pipeline_trace" if str(trace_hash or "").strip() else "legacy_unhashed"


def _journal_digest(entry: TurnJournalEntry) -> str:
    payload = to_data(replace(entry, journal_digest=""))
    payload.pop("journal_digest", None)
    raw = _canonical_json(payload).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
