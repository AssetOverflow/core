from __future__ import annotations

import json
import socket
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from workbench import readers
from workbench.api import WorkbenchApi
from workbench import server
from workbench.server import WorkbenchRequestHandler


def _request(method: str, path: str, body: dict | None = None):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    return WorkbenchApi().handle(method, path, raw)


def _without_generated_at(payload: dict) -> dict:
    out = dict(payload)
    out.pop("generated_at", None)
    return out


def _snapshot(root: Path) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    if not root.exists():
        return snap
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or rel.suffix in {".pyc", ".pyo"}:
            continue
        snap[rel.as_posix()] = path.read_bytes()
    return snap


def _restore_snapshot(root: Path, snap: dict[str, bytes]) -> None:
    if root.exists():
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                if rel not in snap:
                    path.unlink()
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
    for rel, content in snap.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def test_health_route_returns_ok() -> None:
    response = _request("GET", "/health")

    assert response.status == 200
    assert response.payload["ok"] is True
    assert response.payload["data"] == {"status": "ok"}
    assert response.payload["generated_at"]


def test_generated_at_is_only_route_payload_nondeterminism() -> None:
    first = _request("GET", "/health").payload
    second = _request("GET", "/health").payload

    assert _without_generated_at(first) == _without_generated_at(second)


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


def test_well_formed_missing_artifact_returns_404() -> None:
    response = _request("GET", "/artifacts/evals/does-not-exist.json")

    assert response.status == 404
    assert response.payload["error"]["code"] == "not_found"


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


def test_artifact_size_guard_returns_413(monkeypatch) -> None:
    monkeypatch.setattr(readers, "MAX_ARTIFACT_BYTES", 1)

    response = _request("GET", "/artifacts/evals/contemplation_quality/contract.md")

    assert response.status == 413
    assert response.payload["error"]["code"] == "read_error"


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


def test_logos_pack_routes_return_real_read_only_models() -> None:
    listing = _request("GET", "/logos/packs")

    assert listing.status == 200
    assert [item["pack_id"] for item in listing.payload["data"]["items"]] == [
        "grc_logos_cognition_v1",
        "grc_logos_micro_v1",
        "he_core_cognition_v1",
        "he_logos_micro_v1",
    ]

    overview = _request("GET", "/logos/packs/he_logos_micro_v1")
    assert overview.status == 200
    assert overview.payload["data"]["pack_id"] == "he_logos_micro_v1"
    assert overview.payload["data"]["holonomy_case_count"] == 0

    contents = _request("GET", "/logos/packs/he_logos_micro_v1/contents")
    assert contents.status == 200
    assert contents.payload["data"]["holonomy_cases"] == []
    assert contents.payload["data"]["lexicon"][0]["entry_id"] == "he-001"

    safety = _request("GET", "/logos/packs/he_logos_micro_v1/safety")
    assert safety.status == 200
    assert safety.payload["data"]["missing_holonomy_refs"] == "unknown"
    assert safety.payload["data"]["verdict"] == "unknown"

    alignment = _request("GET", "/logos/packs/he_logos_micro_v1/alignment")
    assert alignment.status == 200
    assert alignment.payload["data"]["items"][0]["edge_id"]
    assert alignment.payload["data"]["items"][0]["invalid_target"] is False


def test_logos_routes_fail_closed_for_unsafe_or_non_logos_ids() -> None:
    unsafe = _request("GET", "/logos/packs/../../pyproject.toml")
    assert unsafe.status == 404
    assert unsafe.payload["error"]["code"] == "not_found"

    non_logos = _request("GET", "/logos/packs/en_core_relations_v3")
    assert non_logos.status == 404
    assert non_logos.payload["error"]["code"] == "not_found"

    mutation = _request("POST", "/logos/packs/he_logos_micro_v1")
    assert mutation.status == 404
    assert mutation.payload["error"]["code"] == "not_found"


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


def test_eval_run_rejects_unknown_version_without_path_leak() -> None:
    response = _request(
        "POST",
        "/evals/run",
        {"lane": "contemplation_quality", "version": "v999", "split": "public"},
    )

    assert response.status == 400
    assert response.payload["error"]["code"] == "bad_request"
    assert "unsupported eval version" in response.payload["error"]["message"]
    assert "cases.jsonl" not in response.payload["error"]["message"]


def test_unknown_trace_returns_404_not_placeholder_success() -> None:
    response = _request("GET", "/trace/not-a-real-turn")

    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"


def test_replay_path_style_ids_refuse_not_found() -> None:
    # Wave R3 wired GET /replay/{turn_id} (tests/test_workbench_replay.py owns
    # its obligations); the W-026 path-style artifact id is not a turn id and
    # must refuse cleanly rather than 500 or fabricate a comparison.
    replay = _request("GET", "/replay/evals/cognition/results/example.json")

    assert replay.status == 404
    assert replay.payload["error"]["code"] == "not_found"


def test_unexpected_dispatch_error_stays_json(monkeypatch) -> None:
    def fail_runtime_status():
        raise TypeError("boom")

    monkeypatch.setattr(readers, "runtime_status", fail_runtime_status)

    response = _request("GET", "/runtime/status")

    assert response.status == 500
    assert response.payload["ok"] is False
    assert response.payload["generated_at"]
    assert response.payload["error"]["code"] == "runtime_unavailable"


def test_full_w026_route_table_preserves_teaching_and_pack_bytes() -> None:
    """W-026 read-only invariant.

    The Workbench API must not mutate teaching corpora or pack data. Normal
    runtime checkpoints under engine_state/ are governed by ADR-0146/0150/0159
    and are restored after this test to keep the worktree clean.
    """
    repo_root = Path(__file__).resolve().parent.parent
    guarded = {
        "teaching": repo_root / "teaching",
        "packs": repo_root / "packs",
        "language_packs/data": repo_root / "language_packs" / "data",
    }
    before = {name: _snapshot(path) for name, path in guarded.items()}
    engine_state = repo_root / "engine_state"
    engine_state_before = _snapshot(engine_state)

    try:
        calls = [
            ("GET", "/health", None),
            ("GET", "/runtime/status", None),
            ("GET", "/artifacts?limit=5", None),
            ("GET", "/artifacts/evals/contemplation_quality/contract.md", None),
            ("GET", "/proposals", None),
            ("GET", "/evals", None),
            ("GET", "/evals/contemplation_quality", None),
            ("GET", "/logos/packs", None),
            ("GET", "/logos/packs/he_logos_micro_v1", None),
            ("GET", "/logos/packs/he_logos_micro_v1/contents", None),
            ("GET", "/logos/packs/he_logos_micro_v1/safety", None),
            ("GET", "/logos/packs/he_logos_micro_v1/alignment", None),
            (
                "POST",
                "/evals/run",
                {"lane": "contemplation_quality", "version": "v1", "split": "public"},
            ),
            ("POST", "/chat/turn", {"prompt": "What is truth?"}),
        ]
        responses = [_request(method, path, body) for method, path, body in calls]
    finally:
        _restore_snapshot(engine_state, engine_state_before)

    assert all(response.status == 200 for response in responses)
    after = {name: _snapshot(path) for name, path in guarded.items()}
    assert before == after


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


def test_local_cors_origin_helper_accepts_vite_fallback_ports() -> None:
    assert (
        server._local_origin_or_default("http://127.0.0.1:5175")  # noqa: SLF001
        == "http://127.0.0.1:5175"
    )
    assert (
        server._local_origin_or_default("http://localhost:5174")  # noqa: SLF001
        == "http://localhost:5174"
    )
    assert (
        server._local_origin_or_default("https://example.com")  # noqa: SLF001
        == "http://127.0.0.1:5173"
    )


def test_server_echoes_valid_local_cors_origin_for_vite_fallback_port() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall(
                b"GET /health HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Origin: http://127.0.0.1:5175\r\n"
                b"Connection: close\r\n\r\n"
            )
            chunks: list[bytes] = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert b"HTTP/1.0 200" in data or b"HTTP/1.1 200" in data
    assert b"Access-Control-Allow-Origin: http://127.0.0.1:5175" in data


def test_invalid_content_length_does_not_crash_server() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall(
                b"POST /evals/run HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Length: -1\r\n"
                b"Connection: close\r\n\r\n"
            )
            data = sock.recv(4096)
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert b"HTTP/1.0 400" in data or b"HTTP/1.1 400" in data
    assert b"application/json" in data


def test_trace_construction_route() -> None:
    # 1. Verify invalid turn ID returns 404
    response = _request("GET", "/trace/not-an-int/construction")
    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"

    # 2. Verify missing turn ID returns 404
    response = _request("GET", "/trace/999999/construction")
    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"

    # 3. Create a turn to ensure there is at least one turn
    _request("POST", "/chat/turn", {"prompt": "What is truth?"})

    # 4. Get active turns
    turns_resp = _request("GET", "/trace/turns?limit=5")
    assert turns_resp.status == 200
    items = turns_resp.payload["data"]["items"]
    assert len(items) > 0
    turn_id = items[0]["turn_id"]

    # 5. Query construction endpoint for the existing turn
    response = _request("GET", f"/trace/{turn_id}/construction")
    assert response.status == 200
    assert response.payload["ok"] is True
    data = response.payload["data"]
    assert data["schema_version"] == "construction_evidence_v1"
    assert data["turn_id"] == turn_id
    assert data["status"] == "missing_evidence"
    assert data["diagnostic_only"] is True
    assert data["serving_allowed"] is False
