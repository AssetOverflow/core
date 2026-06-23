from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workbench.construction_endpoint import (
    construction_evidence_response,
    construction_turn_id_from_path,
)


@dataclass(frozen=True, slots=True)
class _Entry:
    turn_id: int


class _Journal:
    def __init__(self, entries: dict[int, Any]) -> None:
        self._entries = entries

    def get_entry(self, turn_id: int) -> Any:
        try:
            return self._entries[turn_id]
        except KeyError:
            raise FileNotFoundError(str(turn_id)) from None


def test_construction_turn_id_from_path_matches_only_construction_route() -> None:
    assert construction_turn_id_from_path("/trace/7/construction") == "7"
    assert construction_turn_id_from_path("/trace/7/pipeline") is None
    assert construction_turn_id_from_path("/trace/7") is None
    assert construction_turn_id_from_path("/trace//construction") is None


def test_construction_evidence_response_returns_missing_evidence_for_legacy_turn() -> None:
    response = construction_evidence_response(_Journal({7: _Entry(turn_id=7)}), "7")

    assert response.status == 200
    assert response.payload["ok"] is True
    data = response.payload["data"]
    assert data["schema_version"] == "construction_evidence_v1"
    assert data["turn_id"] == 7
    assert data["status"] == "missing_evidence"
    assert data["diagnostic_only"] is True
    assert data["serving_allowed"] is False


def test_construction_evidence_response_returns_404_for_bad_turn_id() -> None:
    response = construction_evidence_response(_Journal({}), "not-an-int")

    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"
    assert "not-an-int" in response.payload["error"]["message"]


def test_construction_evidence_response_returns_404_for_missing_turn() -> None:
    response = construction_evidence_response(_Journal({}), "8")

    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"
    assert "8" in response.payload["error"]["message"]
