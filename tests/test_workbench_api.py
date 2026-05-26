from __future__ import annotations

import json

import pytest

from workbench.api import WorkbenchApi
from workbench import server


def _request(method: str, path: str, body: dict | None = None):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    return WorkbenchApi().handle(method, path, raw)


def test_health_route_returns_ok() -> None:
    response = _request("GET", "/health")

    assert response.status == 200
    assert response.payload["ok"] is True
    assert response.payload["data"] == {"status": "ok"}
    assert response.payload["generated_at"]


def test_runtime_status_is_read_only_shape() -> None:
    response = _request("GET", "/runtime/status")

    assert response.status == 200
    data = response.payload["data"]
    assert data["mutation_mode"] == "read_only"
    assert "git_revision" in data
    assert "engine_state_present" in data


def test_artifact_path_traversal_is_rejected() -> None:
    response = _request("GET", "/artifacts/../../pyproject.toml")

    assert response.status == 400
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "bad_request"


def test_artifacts_list_uses_envelope() -> None:
    response = _request("GET", "/artifacts?limit=5")

    assert response.status == 200
    assert response.payload["ok"] is True
    assert isinstance(response.payload["data"]["items"], list)


def test_known_artifact_detail_round_trip() -> None:
    response = _request("GET", "/artifacts/evals/contemplation_quality/contract.md")

    assert response.status == 200
    assert response.payload["data"]["path"] == "evals/contemplation_quality/contract.md"
    assert response.payload["data"]["digest"].startswith("sha256:")


def test_proposals_list_is_read_only_envelope() -> None:
    response = _request("GET", "/proposals")

    assert response.status == 200
    assert response.payload["ok"] is True
    assert "items" in response.payload["data"]


def test_missing_proposal_returns_404() -> None:
    response = _request("GET", "/proposals/not-a-real-proposal")

    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"


def test_eval_lanes_route_returns_items() -> None:
    response = _request("GET", "/evals")

    assert response.status == 200
    assert response.payload["ok"] is True
    assert isinstance(response.payload["data"]["lanes"], list)


def test_eval_lane_detail_returns_read_only_flag() -> None:
    response = _request("GET", "/evals/contemplation_quality")

    assert response.status == 200
    assert response.payload["data"]["lane"] == "contemplation_quality"
    assert response.payload["data"]["read_only"] is True


def test_eval_run_rejects_unsafe_lane() -> None:
    response = _request(
        "POST",
        "/evals/run",
        {"lane": "cognition", "version": "v1", "split": "public"},
    )

    assert response.status == 400
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "bad_request"
    assert "not workbench-safe" in response.payload["error"]["message"]


def test_eval_run_rejects_holdout() -> None:
    response = _request(
        "POST",
        "/evals/run",
        {"lane": "contemplation_quality", "version": "v1", "split": "holdout"},
    )

    assert response.status == 400
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "bad_request"


def test_unknown_trace_returns_404_not_placeholder_success() -> None:
    response = _request("GET", "/trace/not-a-real-turn")

    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"


def test_chat_and_replay_are_explicitly_unsupported_in_w026() -> None:
    chat = _request("POST", "/chat/turn", {"prompt": "What is truth?"})
    replay = _request("GET", "/replay/evals/cognition/results/example.json")

    assert chat.status == 501
    assert chat.payload["error"]["code"] == "unsupported"
    assert replay.status == 501
    assert replay.payload["error"]["code"] == "unsupported"


def test_server_rejects_nonlocal_bind_without_explicit_flag(monkeypatch) -> None:
    called = False

    def fake_serve(*, host: str, port: int) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(server, "serve", fake_serve)

    with pytest.raises(SystemExit):
        server.main(["--host", "0.0.0.0"])

    assert called is False


def test_server_allows_nonlocal_bind_with_explicit_flag(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_serve(*, host: str, port: int) -> None:
        seen["host"] = host
        seen["port"] = port

    monkeypatch.setattr(server, "serve", fake_serve)

    assert server.main(["--host", "0.0.0.0", "--port", "9000", "--allow-nonlocal-bind"]) is None
    assert seen == {"host": "0.0.0.0", "port": 9000}
