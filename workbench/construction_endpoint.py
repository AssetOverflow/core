"""Narrow construction-evidence endpoint seam for Workbench.

This helper keeps the endpoint behavior testable without editing the large
`workbench.api` dispatch table from environments that cannot run local syntax and
route tests. The final API wiring is intentionally one line of dispatch:

    return construction_evidence_response(self._journal, raw_turn_id)

The helper itself is read-only and projects only persisted construction evidence
through `construction_evidence_from_journal_entry`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workbench.construction_evidence import construction_evidence_from_journal_entry
from workbench.schemas import error, ok


@dataclass(frozen=True, slots=True)
class ConstructionEndpointResponse:
    status: int
    payload: dict[str, Any]


def construction_evidence_response(
    journal: Any,
    raw_turn_id: str,
) -> ConstructionEndpointResponse:
    """Return JSON-envelope payload for `/trace/<turn_id>/construction`.

    The function is deliberately free of parsing/reconstruction side effects. It
    reads a journal entry and projects construction evidence when already
    persisted; legacy entries receive a typed `missing_evidence` data payload.
    """

    try:
        turn_id = int(raw_turn_id)
    except ValueError:
        return ConstructionEndpointResponse(
            404,
            error("not_found", f"trace construction not found: {raw_turn_id}"),
        )

    try:
        entry = journal.get_entry(turn_id)
    except FileNotFoundError:
        return ConstructionEndpointResponse(
            404,
            error("not_found", f"trace construction not found: {turn_id}"),
        )

    return ConstructionEndpointResponse(
        200,
        ok(construction_evidence_from_journal_entry(entry)),
    )


def construction_turn_id_from_path(path: str) -> str | None:
    """Extract raw turn id from `/trace/<turn_id>/construction`.

    Returns None for non-matching paths so the main dispatch table can remain
    explicit and order-safe.
    """

    if not (path.startswith("/trace/") and path.endswith("/construction")):
        return None
    raw = path.removeprefix("/trace/").removesuffix("/construction").strip("/")
    return raw or None
