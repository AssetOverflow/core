from __future__ import annotations

from workbench.schemas import RuntimeStatus, error, ok


def test_ok_envelope_contains_generated_at_and_data() -> None:
    payload = ok(RuntimeStatus(
        backend="numpy",
        git_revision="abc123",
        engine_state_present=False,
        checkpoint_revision="unknown",
        revision_warning=False,
        active_session_id=None,
    ))

    assert payload["ok"] is True
    assert isinstance(payload["generated_at"], str)
    assert payload["data"]["backend"] == "numpy"
    assert payload["data"]["mutation_mode"] == "read_only"


def test_error_envelope_contains_generated_at_and_code() -> None:
    payload = error("not_found", "missing")

    assert payload["ok"] is False
    assert isinstance(payload["generated_at"], str)
    assert payload["error"] == {"code": "not_found", "message": "missing"}
