"""Narrow sealed-practice evidence endpoint seam for Workbench.

The helper is read-only and projects only persisted practice evidence through
`practice_evidence_from_journal_entry`. It never runs geometric search, replay,
operator execution, or trace sealing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workbench.practice_evidence import practice_evidence_from_journal_entry
from workbench.schemas import error, ok


@dataclass(frozen=True, slots=True)
class PracticeEndpointResponse:
    status: int
    payload: dict[str, Any]


def practice_evidence_response(
    journal: Any,
    raw_turn_id: str,
) -> PracticeEndpointResponse:
    """Return JSON-envelope payload for `/trace/<turn_id>/practice`."""

    try:
        turn_id = int(raw_turn_id)
    except ValueError:
        return PracticeEndpointResponse(
            404,
            error("not_found", f"trace practice not found: {raw_turn_id}"),
        )

    try:
        entry = journal.get_entry(turn_id)
    except FileNotFoundError:
        return PracticeEndpointResponse(
            404,
            error("not_found", f"trace practice not found: {turn_id}"),
        )

    return PracticeEndpointResponse(
        200,
        ok(practice_evidence_from_journal_entry(entry)),
    )


def practice_turn_id_from_path(path: str) -> str | None:
    """Extract raw turn id from `/trace/<turn_id>/practice`."""

    if not (path.startswith("/trace/") and path.endswith("/practice")):
        return None
    raw = path.removeprefix("/trace/").removesuffix("/practice").strip("/")
    return raw or None
