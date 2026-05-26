"""W-026 CORE Workbench read-only API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from workbench.api import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_health_route_returns_ok() -> None:
    response = _client().get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "ok"


def test_runtime_status_is_read_only_shape() -> None:
    response = _client().get("/runtime/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["mutation_mode"] == "read_only"
    assert "git_revision" in data
    assert "engine_state_present" in data


def test_artifact_path_traversal_is_rejected() -> None:
    response = _client().get("/artifacts/../../pyproject.toml")
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad_request"


def test_artifact_missing_inside_allowed_root_is_not_found() -> None:
    response = _client().get("/artifacts/evals/does-not-exist.json")
    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_artifacts_list_uses_envelope() -> None:
    response = _client().get("/artifacts?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "items" in payload["data"]
    assert isinstance(payload["data"]["items"], list)


def test_proposals_list_is_read_only_envelope() -> None:
    response = _client().get("/proposals")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "items" in payload["data"]


def test_missing_proposal_returns_404() -> None:
    response = _client().get("/proposals/not-a-real-proposal")
    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_eval_lanes_route_returns_items() -> None:
    response = _client().get("/evals")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "lanes" in payload["data"]


def test_eval_run_rejects_unsafe_lane() -> None:
    response = _client().post(
        "/evals/run",
        json={"lane": "cognition", "version": "v1", "split": "public"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad_request"
    assert "not workbench-safe" in payload["error"]["message"]


def test_eval_run_rejects_holdout() -> None:
    response = _client().post(
        "/evals/run",
        json={"lane": "contemplation_quality", "version": "v1", "split": "holdout"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad_request"


def test_replay_path_traversal_is_rejected() -> None:
    response = _client().get("/replay/../../pyproject.toml")
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad_request"


def test_read_known_repo_artifact_round_trip() -> None:
    # pyproject.toml is intentionally not under allowed artifact roots; use a
    # known eval contract instead when present.
    artifact = Path("evals/contemplation_quality/contract.md")
    if not artifact.exists():
        return
    response = _client().get(f"/artifacts/{artifact.as_posix()}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["path"] == artifact.as_posix()
    assert payload["data"]["digest"]
