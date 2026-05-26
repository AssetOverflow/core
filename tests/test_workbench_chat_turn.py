from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from workbench import api as workbench_api
from workbench.api import WorkbenchApi
from workbench.schemas import ChatTurnResult, TurnVerdict


def _request(body: dict | bytes):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    return WorkbenchApi().handle("POST", "/chat/turn", raw)


def _snapshot(root: Path) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    if not root.exists():
        return snap
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.relative_to(root).parts:
            snap[path.relative_to(root).as_posix()] = path.read_bytes()
    return snap


def _restore_snapshot(root: Path, snap: dict[str, bytes]) -> None:
    if root.exists():
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file() and path.relative_to(root).as_posix() not in snap:
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


def test_chat_turn_happy_path_real_prompt() -> None:
    response = _request({"prompt": "What is truth?"})

    assert response.status == 200
    data = response.payload["data"]
    assert data["prompt"] == "What is truth?"
    assert data["surface"]
    assert data["grounding_source"] in {"pack", "teaching", "vault", "partial", "oov", "none"}
    assert data["mutation_mode"] == "runtime_turn"
    assert isinstance(data["checkpoint_emitted"], bool)
    assert isinstance(data["turn_cost_ms"], int)
    assert "walk_surface" in data and "articulation_surface" in data


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"prompt": "   "}, 400, "bad_request"),
        ({}, 400, "bad_request"),
        (b'{"prompt":"' + (b"x" * (64 * 1024 + 1)) + b'"}', 413, "read_error"),
    ],
)
def test_chat_turn_validation(body: dict | bytes, status: int, code: str) -> None:
    response = _request(body)

    assert response.status == status
    assert response.payload["error"]["code"] == code


def test_chat_turn_requests_are_serialized(monkeypatch) -> None:
    events: list[tuple[str, str, float]] = []

    def fake_run(prompt: str) -> ChatTurnResult:
        events.append((prompt, "start", time.perf_counter()))
        time.sleep(0.05)
        events.append((prompt, "end", time.perf_counter()))
        return ChatTurnResult(
            prompt=prompt,
            surface=f"surface {prompt}",
            articulation_surface="articulation",
            walk_surface="walk",
            grounding_source="pack",
            epistemic_state="decoded",
            normative_clearance="cleared",
            normative_detail="",
            trace_hash=None,
            refusal_emitted=False,
            hedge_injected=False,
            mutation_mode="runtime_turn",
            identity_verdict=None,
            safety_verdict=TurnVerdict(outcome="cleared", runtime_detail=""),
            ethics_verdict=TurnVerdict(outcome="cleared", runtime_detail=""),
            proposal_candidates=[],
            turn_cost_ms=0,
            checkpoint_emitted=True,
        )

    monkeypatch.setattr(workbench_api, "_run_chat_turn", fake_run)
    responses = []

    def call(prompt: str) -> None:
        responses.append(_request({"prompt": prompt}))

    first = threading.Thread(target=call, args=("first",))
    second = threading.Thread(target=call, args=("second",))
    first.start()
    second.start()
    first.join(timeout=2)
    second.join(timeout=2)

    assert [response.status for response in responses] == [200, 200]
    starts = [event for event in events if event[1] == "start"]
    ends = [event for event in events if event[1] == "end"]
    assert len(starts) == 2 and len(ends) == 2
    assert starts[1][2] >= ends[0][2]


def test_chat_turn_preserves_teaching_and_pack_bytes() -> None:
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
        response = _request({"prompt": "What is truth?"})
    finally:
        _restore_snapshot(engine_state, engine_state_before)

    assert response.status == 200
    assert {name: _snapshot(path) for name, path in guarded.items()} == before


def test_chat_turn_reports_runtime_turn_mutation_mode() -> None:
    response = _request({"prompt": "What is truth?"})

    assert response.status == 200
    assert response.payload["data"]["mutation_mode"] == "runtime_turn"


def test_chat_turn_refusal_path_reports_suppression() -> None:
    response = _request({"prompt": "Tina makes $18.00 an hour."})

    assert response.status == 200
    data = response.payload["data"]
    assert data["refusal_emitted"] is True
    assert data["normative_clearance"] == "suppressed"
    assert data["surface"].startswith("I don't know")


def test_surface_and_walk_surface_are_distinct_contract_fields() -> None:
    response = _request({"prompt": "What is truth?"})

    assert response.status == 200
    data = response.payload["data"]
    assert "surface" in data
    assert "walk_surface" in data
    assert data["surface"] != data["walk_surface"]
