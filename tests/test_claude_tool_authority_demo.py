from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from demos.claude_tool_authority import authority
from demos.claude_tool_authority import run_demo as demo_runner

DEMO_DIR = Path(authority.__file__).resolve().parent
FIXTURES_DIR = DEMO_DIR / "fixtures"
EXPECTED_DIR = DEMO_DIR / "expected"
PROTECTED_PATHS = [
    Path("CLAIMS.md"),
    Path("chat/runtime.py"),
    Path("docs/runtime_contracts.md"),
]


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _run_arguments(name: str) -> dict[str, object]:
    fixture = _fixture(name)
    return authority.run_authority(fixture["arguments"])


def _hash_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_schema_is_closed_recursively():
    schema = authority.load_schema()["inputSchema"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["proposer"]["additionalProperties"] is False
    assert schema["properties"]["action_request"]["additionalProperties"] is False
    assert schema["properties"]["action_request"]["properties"]["target"]["additionalProperties"] is False
    assert schema["properties"]["action_request"]["properties"]["payload"]["additionalProperties"] is False


def test_all_four_scenarios_work():
    assert _run_arguments("authorized-low-risk-local-action.json")["status"] == "authorized"
    assert _run_arguments("ask-required-action.json")["status"] == "ask"
    assert _run_arguments("refused-outside-envelope-action.json")["status"] == "refused"
    assert _run_arguments("invalid-smuggling-attempt.json")["status"] == "invalid"


def test_proposer_cannot_smuggle_licensed_action():
    response = _run_arguments("invalid-smuggling-attempt.json")
    assert response["status"] == "invalid"
    assert "licensed_action" in response["invalid_reason"]


def test_proposer_cannot_set_authorization_result():
    payload = _fixture("authorized-low-risk-local-action.json")["arguments"]
    payload["status"] = "authorized"
    response = authority.run_authority(payload)
    assert response["status"] == "invalid"
    assert "payload unexpected property 'status'" in response["invalid_reason"]


def test_fake_trace_hash_is_ignored_and_regenerated():
    payload = _fixture("authorized-low-risk-local-action.json")["arguments"]
    response = authority.run_authority(payload)
    assert response["status"] == "authorized"
    assert response["trace_summary"]["proposer_trace_hash_ignored"] is True
    assert response["trace_hash"] != payload["proposer"]["trace_hash"]


def test_unauthorized_tool_refuses():
    response = _run_arguments("refused-outside-envelope-action.json")
    assert response["status"] == "refused"
    assert response["refusal_reason"] == "unauthorized_tool"


def test_missing_confirmation_asks():
    response = _run_arguments("ask-required-action.json")
    assert response["status"] == "ask"
    assert response["decision_reason"] == "missing_explicit_confirmation"
    assert "explicit user confirmation" in response["question"]


def test_authorized_only_inside_envelope():
    response = _run_arguments("authorized-low-risk-local-action.json")
    assert response["status"] == "authorized"
    assert response["licensed_action"]["effect"] == "inert_license_only"

    payload = _fixture("authorized-low-risk-local-action.json")["arguments"]
    payload["action_request"]["target"]["path"] = "docs/runtime_contracts.md"
    refused = authority.run_authority(payload)
    assert refused["status"] == "refused"
    assert refused["refusal_reason"] == "protected_path"


def test_invalid_payload_fails_before_authority_evaluation(monkeypatch):
    def _explode(_payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError("authority evaluation ran for invalid payload")

    monkeypatch.setattr(authority, "evaluate_authority", _explode)
    response = _run_arguments("invalid-smuggling-attempt.json")
    assert response["status"] == "invalid"
    assert response["trace_summary"]["authority_evaluated"] is False


def test_double_run_outputs_byte_identical(tmp_path):
    payload = _fixture("authorized-low-risk-local-action.json")["arguments"]
    run_a = authority.run_authority(payload)
    run_b = authority.run_authority(payload)
    assert json.dumps(run_a, sort_keys=True, indent=2) == json.dumps(run_b, sort_keys=True, indent=2)


def test_expected_artifact_tampering_fails(tmp_path):
    scenario_id = "authorized-low-risk-local-action"
    original = (EXPECTED_DIR / f"{scenario_id}.json").read_text(encoding="utf-8")
    try:
        (EXPECTED_DIR / f"{scenario_id}.json").write_text(original.replace("authorized", "refused", 1), encoding="utf-8")
        argv = ["run_demo.py", "--out", str(tmp_path / "out")]
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr("sys.argv", argv)
            assert demo_runner.main() == 1
    finally:
        (EXPECTED_DIR / f"{scenario_id}.json").write_text(original, encoding="utf-8")


def test_run_demo_all_passes_against_expected(tmp_path, monkeypatch):
    out_dir = tmp_path / "demo-out"
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--out", str(out_dir)])
    assert demo_runner.main() == 0


def test_no_network_subprocess_eval_or_exec_imports_or_calls():
    forbidden_imports = {"subprocess", "socket", "requests", "httpx", "urllib", "urllib.request"}
    forbidden_calls = {"eval", "exec", "compile", "open_connection", "create_connection", "Popen", "run"}
    scanned = [
        DEMO_DIR / "__init__.py",
        DEMO_DIR / "authority.py",
        DEMO_DIR / "run_demo.py",
    ]
    for path in scanned:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_imports
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert module not in forbidden_imports
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in forbidden_calls
                elif isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in forbidden_calls


def test_protected_paths_unchanged(tmp_path, monkeypatch):
    before = {path: _hash_path(path) for path in PROTECTED_PATHS}
    out_dir = tmp_path / "demo-out"
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--out", str(out_dir)])
    assert demo_runner.main() == 0
    after = {path: _hash_path(path) for path in PROTECTED_PATHS}
    assert before == after
