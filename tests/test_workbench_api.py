"""W-026 CORE Workbench read-only API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from workbench.api import create_app
from workbench.auth import hash_password

_ADMIN_EMAIL = "admin@example.test"
_ADMIN_PASSWORD = "correct-horse-battery-staple"
_SESSION_SECRET = "test-session-secret-not-for-production"


def _client(monkeypatch=None, *, configured: bool = True) -> TestClient:
    if monkeypatch is not None:
        if configured:
            monkeypatch.setenv("CORE_WORKBENCH_ADMIN_EMAIL", _ADMIN_EMAIL)
            monkeypatch.setenv(
                "CORE_WORKBENCH_ADMIN_PASSWORD_HASH",
                hash_password(_ADMIN_PASSWORD, salt=b"0123456789abcdef"),
            )
            monkeypatch.setenv("CORE_WORKBENCH_SESSION_SECRET", _SESSION_SECRET)
        else:
            monkeypatch.delenv("CORE_WORKBENCH_ADMIN_EMAIL", raising=False)
            monkeypatch.delenv("CORE_WORKBENCH_ADMIN_PASSWORD_HASH", raising=False)
            monkeypatch.delenv("CORE_WORKBENCH_SESSION_SECRET", raising=False)
    return TestClient(create_app())


def _authenticated_client(monkeypatch) -> TestClient:
    client = _client(monkeypatch)
    response = client.post(
        "/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return client


def test_health_route_returns_ok(monkeypatch) -> None:
    response = _client(monkeypatch).get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["auth_configured"] is True


def test_health_reports_unconfigured_auth(monkeypatch) -> None:
    response = _client(monkeypatch, configured=False).get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["auth_configured"] is False


def test_login_rejects_invalid_credentials(monkeypatch) -> None:
    response = _client(monkeypatch).post(
        "/auth/login",
        json={"email": _ADMIN_EMAIL, "password": "wrong"},
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "unauthorized"


def test_protected_route_requires_auth(monkeypatch) -> None:
    response = _client(monkeypatch).get("/runtime/status")
    assert response.status_code == 401
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "unauthorized"


def test_auth_me_returns_admin_email(monkeypatch) -> None:
    client = _authenticated_client(monkeypatch)
    response = client.get("/auth/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["email"] == _ADMIN_EMAIL


def test_logout_clears_session(monkeypatch) -> None:
    client = _authenticated_client(monkeypatch)
    response = client.post("/auth/logout")
    assert response.status_code == 200
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_runtime_status_is_read_only_shape(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).get("/runtime/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["mutation_mode"] == "read_only"
    assert "git_revision" in data
    assert "engine_state_present" in data


def test_artifact_path_traversal_is_rejected(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).get("/artifacts/../../pyproject.toml")
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad_request"


def test_artifact_missing_inside_allowed_root_is_not_found(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).get("/artifacts/evals/does-not-exist.json")
    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_artifacts_list_uses_envelope(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).get("/artifacts?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "items" in payload["data"]
    assert isinstance(payload["data"]["items"], list)


def test_proposals_list_is_read_only_envelope(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).get("/proposals")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "items" in payload["data"]


def test_missing_proposal_returns_404(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).get("/proposals/not-a-real-proposal")
    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_eval_lanes_route_returns_items(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).get("/evals")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "lanes" in payload["data"]


def test_eval_run_rejects_unsafe_lane(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).post(
        "/evals/run",
        json={"lane": "cognition", "version": "v1", "split": "public"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad_request"
    assert "not workbench-safe" in payload["error"]["message"]


def test_eval_run_rejects_holdout(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).post(
        "/evals/run",
        json={"lane": "contemplation_quality", "version": "v1", "split": "holdout"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad_request"


def test_replay_path_traversal_is_rejected(monkeypatch) -> None:
    response = _authenticated_client(monkeypatch).get("/replay/../../pyproject.toml")
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad_request"


def test_read_known_repo_artifact_round_trip(monkeypatch) -> None:
    artifact = Path("evals/contemplation_quality/contract.md")
    if not artifact.exists():
        return
    response = _authenticated_client(monkeypatch).get(f"/artifacts/{artifact.as_posix()}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["path"] == artifact.as_posix()
    assert payload["data"]["digest"]
