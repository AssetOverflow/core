"""ADR-0055 Phase A — corpus audit for the reviewed teaching chains.

Re-parses ``teaching/cognition_chains/cognition_chains_v1.jsonl`` with
the same gates as ``chat.teaching_grounding._corpus_index`` (schema,
intent whitelist, pack-consistency, supersession), but **keeps the
drop reasons** so an operator can inspect silent corpus shrinkage —
e.g. a pack swap that left a chain referencing a missing lemma, or
a supersession chain that retired older entries.

Pure-function, non-mutating, deterministic.  Output is order-stable
(input line order) so it is safe to wire into CI and diff against
prior runs.

This module is **read-only**.  It must never write to the corpus,
to the pack, or to any runtime state.  Trust-boundary: the
``raw_line`` field surfaces the verbatim JSONL line; callers that
log this should route through ``core._safe_display.safe_display``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chat.pack_grounding import _pack_index
from chat.teaching_grounding import (
    _CORPUS_PATH,
    _VALID_INTENTS,
    TEACHING_CORPUS_ID,
)
from teaching.provenance import Provenance, parse_provenance


@dataclass(frozen=True, slots=True)
class DroppedChain:
    """One JSONL line that did not enter the active corpus."""

    line_no: int
    reason: str
    raw_line: str
    chain_id: str | None = None


@dataclass(frozen=True, slots=True)
class LoadedChain:
    """One JSONL line that entered the active corpus."""

    line_no: int
    chain_id: str
    subject: str
    intent: str
    connective: str
    object: str
    provenance: Provenance
    superseded_by: str | None


@dataclass(frozen=True, slots=True)
class AuditReport:
    corpus_id: str
    corpus_path: str
    lines_on_disk: int
    lines_loaded: int
    loaded: tuple[LoadedChain, ...] = field(default_factory=tuple)
    dropped: tuple[DroppedChain, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "corpus_id": self.corpus_id,
            "corpus_path": self.corpus_path,
            "lines_on_disk": self.lines_on_disk,
            "lines_loaded": self.lines_loaded,
            "loaded": [
                {
                    "line_no": c.line_no,
                    "chain_id": c.chain_id,
                    "subject": c.subject,
                    "intent": c.intent,
                    "connective": c.connective,
                    "object": c.object,
                    "provenance": {
                        "adr_id": c.provenance.adr_id,
                        "source": c.provenance.source,
                        "review_date": c.provenance.review_date,
                        "raw": c.provenance.raw,
                    },
                    "superseded_by": c.superseded_by,
                }
                for c in self.loaded
            ],
            "dropped": [
                {
                    "line_no": d.line_no,
                    "reason": d.reason,
                    "chain_id": d.chain_id,
                    "raw_line": d.raw_line,
                }
                for d in self.dropped
            ],
        }


def _read_entries(path: Path) -> list[tuple[int, str, dict | None]]:
    """Read JSONL lines as ``(line_no, raw, parsed_or_none)`` tuples.

    Line numbers are 1-based to match editor conventions.  Blank lines
    are skipped silently (they were never on the disk-loaded count
    either — they are not chains).
    """
    out: list[tuple[int, str, dict | None]] = []
    if not path.exists():
        return out
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            out.append((idx, line, None))
            continue
        out.append((idx, line, entry))
    return out


def audit_corpus(path: Path | None = None) -> AuditReport:
    """Re-parse the teaching corpus and surface load decisions.

    Returns an ``AuditReport`` with one entry per non-empty line on
    disk, classified as loaded or dropped with a deterministic reason
    string.  Pack consistency is checked against the same pack the
    runtime loads.

    Reasons (stable strings, safe to assert against in tests):
      - ``"invalid_json"``
      - ``"missing_required_field:<field>"``
      - ``"unsupported_intent:<intent>"``
      - ``"pack_missing_subject:<lemma>"``
      - ``"pack_missing_object:<lemma>"``
      - ``"superseded_by:<chain_id>"``
    """
    corpus_path = path or _CORPUS_PATH
    entries = _read_entries(corpus_path)
    pack = _pack_index()

    # First sweep — collect supersession claims from entries that
    # otherwise look well-formed enough to assert one.  An invalid
    # entry cannot supersede anything; this is intentional so a bad
    # line cannot retire a good one.
    superseded_ids: set[str] = set()
    for _line_no, _raw, entry in entries:
        if not isinstance(entry, dict):
            continue
        sup = entry.get("superseded_by")
        if isinstance(sup, str) and sup.strip():
            # The current entry claims to supersede ``sup``.
            superseded_ids.add(sup.strip())

    loaded: list[LoadedChain] = []
    dropped: list[DroppedChain] = []

    for line_no, raw, entry in entries:
        if entry is None:
            dropped.append(DroppedChain(line_no=line_no, reason="invalid_json", raw_line=raw))
            continue

        chain_id_raw = entry.get("chain_id")
        chain_id_for_audit = str(chain_id_raw) if isinstance(chain_id_raw, str) else None

        subject = (entry.get("subject") or "").strip().lower() if isinstance(entry.get("subject"), str) else ""
        intent = (entry.get("intent") or "").strip().lower() if isinstance(entry.get("intent"), str) else ""
        obj = (entry.get("object") or "").strip().lower() if isinstance(entry.get("object"), str) else ""
        connective = (entry.get("connective") or "").strip() if isinstance(entry.get("connective"), str) else ""

        if not subject:
            dropped.append(DroppedChain(
                line_no=line_no, reason="missing_required_field:subject",
                raw_line=raw, chain_id=chain_id_for_audit,
            ))
            continue
        if not intent:
            dropped.append(DroppedChain(
                line_no=line_no, reason="missing_required_field:intent",
                raw_line=raw, chain_id=chain_id_for_audit,
            ))
            continue
        if not obj:
            dropped.append(DroppedChain(
                line_no=line_no, reason="missing_required_field:object",
                raw_line=raw, chain_id=chain_id_for_audit,
            ))
            continue
        if not connective:
            dropped.append(DroppedChain(
                line_no=line_no, reason="missing_required_field:connective",
                raw_line=raw, chain_id=chain_id_for_audit,
            ))
            continue
        if intent not in _VALID_INTENTS:
            dropped.append(DroppedChain(
                line_no=line_no, reason=f"unsupported_intent:{intent}",
                raw_line=raw, chain_id=chain_id_for_audit,
            ))
            continue
        if subject not in pack:
            dropped.append(DroppedChain(
                line_no=line_no, reason=f"pack_missing_subject:{subject}",
                raw_line=raw, chain_id=chain_id_for_audit,
            ))
            continue
        if obj not in pack:
            dropped.append(DroppedChain(
                line_no=line_no, reason=f"pack_missing_object:{obj}",
                raw_line=raw, chain_id=chain_id_for_audit,
            ))
            continue

        chain_id = chain_id_for_audit or f"{subject}_{intent}"
        if chain_id in superseded_ids:
            dropped.append(DroppedChain(
                line_no=line_no, reason=f"superseded_by:{chain_id}",
                raw_line=raw, chain_id=chain_id,
            ))
            continue

        sup_raw = entry.get("superseded_by")
        sup = sup_raw.strip() if isinstance(sup_raw, str) and sup_raw.strip() else None

        loaded.append(LoadedChain(
            line_no=line_no,
            chain_id=chain_id,
            subject=subject,
            intent=intent,
            connective=connective,
            object=obj,
            provenance=parse_provenance(entry.get("provenance")),
            superseded_by=sup,
        ))

    return AuditReport(
        corpus_id=TEACHING_CORPUS_ID,
        corpus_path=str(corpus_path),
        lines_on_disk=len(entries),
        lines_loaded=len(loaded),
        loaded=tuple(loaded),
        dropped=tuple(dropped),
    )
