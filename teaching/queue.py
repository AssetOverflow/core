"""ADR-0161 Step 1 — Read-only queue projection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from teaching.proposals import ProposalLog, ReviewState


@dataclass(frozen=True, slots=True)
class QueueItem:
    proposal_id: str
    source_kind: str
    source_id: str | None
    proposed_chain: dict[str, Any]
    replay_evidence: dict[str, Any] | None
    state: ReviewState
    review_history: tuple[dict[str, Any], ...]
    contemplation_report_path: str | None
    age_proposals: int


@lru_cache(maxsize=1)
def _load_contemplation_mapping(runs_dir: Path, runs_dir_mtime: float) -> dict[str, str]:
    """Cache the mapping of proposal_id to JSON file path under runs_dir.

    Keyed on runs_dir and its modification time (mtime) for invalidation.
    """
    mapping: dict[str, str] = {}
    if runs_dir.exists() and runs_dir.is_dir():
        for path in runs_dir.glob("*.json"):
            if not path.is_file():
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            if not isinstance(data, dict):
                continue

            pids: set[str] = set()
            top_pid = data.get("proposal_id")
            if isinstance(top_pid, str):
                pids.add(top_pid)

            scenes = data.get("scenes")
            if isinstance(scenes, list):
                for scene in scenes:
                    if isinstance(scene, dict):
                        detail = scene.get("detail")
                        if isinstance(detail, dict):
                            scene_pid = detail.get("proposal_id")
                            if isinstance(scene_pid, str):
                                pids.add(scene_pid)

            for pid in pids:
                mapping[pid] = str(path.resolve())
    return mapping


def derive_queue(
    log: ProposalLog,
    contemplation_runs_dir: Path,
) -> tuple[QueueItem, ...]:
    """Derive a read-only queue projection from the ProposalLog.

    Order: FIFO by first-pending-event order in the log.
    """
    events = log.events()
    proposals_data: dict[str, dict[str, Any]] = {}
    created_order: list[str] = []

    for ev in events:
        kind = ev.get("event")
        if kind == "created":
            p = ev.get("proposal") or {}
            pid = p.get("proposal_id")
            if not pid:
                continue
            if pid not in proposals_data:
                created_order.append(pid)
                source_dict = p.get("source") or {}
                source_kind = source_dict.get("kind", "")
                source_id = source_dict.get("source_id")
                # Normalize empty string to None
                if source_id == "":
                    source_id = None

                proposals_data[pid] = {
                    "proposal_id": pid,
                    "source_kind": source_kind,
                    "source_id": source_id,
                    "proposed_chain": p.get("proposed_chain"),
                    "replay_evidence": p.get("replay_evidence"),
                    "state": p.get("review_state", "pending"),
                    "review_history": [],
                }
        elif kind == "replay":
            pid = ev.get("proposal_id")
            if pid in proposals_data:
                proposals_data[pid]["replay_evidence"] = ev.get("replay_evidence")
        elif kind == "transition":
            pid = ev.get("proposal_id")
            if pid in proposals_data:
                proposals_data[pid]["state"] = ev.get("to")
                # Append transition event to review_history
                proposals_data[pid]["review_history"].append(dict(ev))

    # Retrieve cached mapping using runs_dir mtime
    try:
        mtime = contemplation_runs_dir.stat().st_mtime
    except OSError:
        mtime = 0.0

    contemplation_mapping = _load_contemplation_mapping(contemplation_runs_dir, mtime)

    # Build the final tuple of QueueItem
    items: list[QueueItem] = []
    for i, pid in enumerate(created_order):
        data = proposals_data[pid]
        state = data["state"]

        if state == "pending":
            # Per ADR-0161 §4, age is subsequent proposals appended regardless of state.
            age_proposals = len(created_order) - 1 - i
        else:
            age_proposals = 0

        item = QueueItem(
            proposal_id=pid,
            source_kind=data["source_kind"],
            source_id=data["source_id"],
            proposed_chain=data["proposed_chain"],
            replay_evidence=data["replay_evidence"],
            state=state,
            review_history=tuple(data["review_history"]),
            contemplation_report_path=contemplation_mapping.get(pid),
            age_proposals=age_proposals,
        )
        items.append(item)

    return tuple(items)


def find_queue_item(
    log: ProposalLog,
    proposal_id: str,
    contemplation_runs_dir: Path,
) -> QueueItem | None:
    """Find a specific queue item by exact ID or unique prefix."""
    items = derive_queue(log, contemplation_runs_dir)
    for item in items:
        if item.proposal_id == proposal_id:
            return item

    matches = [item for item in items if item.proposal_id.startswith(proposal_id)]
    if len(matches) == 1:
        return matches[0]
    return None
