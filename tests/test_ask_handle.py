"""Focused tests for the carried-handle ASK acquisition seam.

These tests intentionally avoid ``chat.runtime`` and never call the off-serving
producer (``pass_manager.contemplate`` / ``deliver_ask`` / ``render_question``).
Artifacts are hand-written in the exact producer shape (the same payload
convention as ``tests/test_ask_serving_integration.py``) with the producer's
content-address recipe applied directly — the seam must resolve a *pre-existing*
artifact, so the tests construct the pre-existing state, not the producer call.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import os
from pathlib import Path

from core.config import RuntimeConfig
from core.epistemic_disclosure.ask_handle import (
    AskArtifactHandle,
    AskHandleResolution,
    acquire_served_ask_from_handle,
    resolve_served_ask_handle,
)
from core.epistemic_disclosure.disposition import ServedDisposition

_SEAM_PATH = (
    Path(__file__).resolve().parents[1] / "core" / "epistemic_disclosure" / "ask_handle.py"
)


def _valid_payload(text: str = "How many crates are left?") -> dict:
    return {
        "status": "question_only",
        "blocking_reason": "missing_total_count",
        "owner_organ": "r2_constraint",
        "question": {
            "text": text,
            "reason": "missing_total_count",
            "slot_name": "total_count",
            "expected_unit_or_type": "count_int",
            "binding_target": "collective_unit_total",
        },
        "answer_binding": None,
        "requires_review": True,
        "served": False,
    }


def _content_hash(payload: dict) -> str:
    """The producer's content address: sha256 over blocking_reason:slot_name:text."""
    slot_name = payload["question"].get("slot_name") or ""
    digest = f"{payload['blocking_reason']}:{slot_name}:{payload['question']['text']}"
    return hashlib.sha256(digest.encode("utf-8")).hexdigest()


def _write_addressed_artifact(root: Path, payload: dict) -> tuple[Path, str]:
    """Write *payload* at its producer content-addressed path; return (path, hash)."""
    digest = _content_hash(payload)
    path = root / f"{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path, digest


def _handle(path: Path, digest: str, proposal_path: Path | None = None) -> AskArtifactHandle:
    return AskArtifactHandle(
        question_path=str(path),
        content_hash=digest,
        proposal_path=str(proposal_path) if proposal_path is not None else None,
    )


# --- gate-first behavior -----------------------------------------------------


def test_gate_disabled_rejects_without_filesystem_access(tmp_path: Path, monkeypatch) -> None:
    payload = _valid_payload()
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)

    def boom(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("the seam must not touch the filesystem while the gate is dark")

    monkeypatch.setattr(Path, "is_file", boom)
    monkeypatch.setattr(Path, "read_text", boom)

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=False), _handle(path, digest)
    )

    assert isinstance(resolution, AskHandleResolution)
    assert resolution.resolved is False
    assert resolution.reason == "gate_disabled"
    assert resolution.candidate is None


def test_gate_disabled_fallback_surface_is_unchanged(tmp_path: Path) -> None:
    payload = _valid_payload()
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)

    acquired = acquire_served_ask_from_handle(
        RuntimeConfig(ask_serving_enabled=False),
        handle=_handle(path, digest),
        fallback_surface="I don't know — insufficient grounding for that yet.",
    )

    assert acquired.acquired is False
    assert acquired.provider_called is False
    assert acquired.decision.served is False
    assert acquired.decision.surface == "I don't know — insufficient grounding for that yet."
    assert acquired.decision.disposition is ServedDisposition.REFUSE


def test_default_config_is_dark(tmp_path: Path) -> None:
    payload = _valid_payload()
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)

    resolution = resolve_served_ask_handle(RuntimeConfig(), _handle(path, digest))

    assert resolution.resolved is False
    assert resolution.reason == "gate_disabled"


# --- valid resolution through the existing serving stack ---------------------


def test_valid_handle_resolves_to_acquisition_compatible_candidate(tmp_path: Path) -> None:
    payload = _valid_payload("How many crates are left?")
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), _handle(path, digest)
    )

    assert resolution.resolved is True
    assert resolution.reason == "resolved"
    assert resolution.candidate is not None
    assert resolution.candidate.terminal == "QUESTION_NEEDED"
    assert resolution.candidate.question_path == str(path)
    assert resolution.candidate.proposal_path is None


def test_valid_handle_serves_through_existing_stack(tmp_path: Path) -> None:
    payload = _valid_payload("How many crates are left?")
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)

    acquired = acquire_served_ask_from_handle(
        RuntimeConfig(ask_serving_enabled=True),
        handle=_handle(path, digest),
        fallback_surface="fallback",
    )

    assert acquired.acquired is True
    assert acquired.decision.served is True
    assert acquired.decision.terminal == "QUESTION_NEEDED"
    assert acquired.decision.surface == "How many crates are left?"
    assert acquired.decision.disposition is ServedDisposition.ASK


def test_resolved_candidate_carries_no_question_prose(tmp_path: Path) -> None:
    payload = _valid_payload("How many crates are left?")
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), _handle(path, digest)
    )

    assert resolution.candidate is not None
    candidate_fields = dataclasses.asdict(resolution.candidate)
    assert "How many crates are left?" not in {
        v for v in candidate_fields.values() if isinstance(v, str)
    }


# --- fail-closed rejections ---------------------------------------------------


def test_handle_to_proposal_artifact_fails_closed(tmp_path: Path) -> None:
    proposal_payload = {
        "status": "proposal_only",
        "family": "missing_category_pair",
        "requires_review": True,
        "mounted": False,
    }
    path = tmp_path / "proposals" / "p.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal_payload), encoding="utf-8")
    digest = hashlib.sha256(b"not-a-question-address").hexdigest()
    addressed = path.parent / f"{digest}.json"
    addressed.write_text(json.dumps(proposal_payload), encoding="utf-8")

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), _handle(addressed, digest)
    )

    # A proposal artifact has no Q1-D content-address fields → malformed body.
    assert resolution.resolved is False
    assert resolution.reason == "malformed_artifact"

    acquired = acquire_served_ask_from_handle(
        RuntimeConfig(ask_serving_enabled=True),
        handle=_handle(addressed, digest),
        fallback_surface="fallback",
    )
    assert acquired.decision.served is False
    assert acquired.decision.surface == "fallback"


def test_missing_artifact_fails_closed(tmp_path: Path) -> None:
    digest = _content_hash(_valid_payload())
    missing = tmp_path / "questions" / f"{digest}.json"

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), _handle(missing, digest)
    )

    assert resolution.resolved is False
    assert resolution.reason == "missing_artifact"


def test_malformed_json_fails_closed(tmp_path: Path) -> None:
    digest = _content_hash(_valid_payload())
    path = tmp_path / "questions" / f"{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad json", encoding="utf-8")

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), _handle(path, digest)
    )

    assert resolution.resolved is False
    assert resolution.reason == "malformed_artifact"


def test_valid_json_with_invalid_q1d_fields_fails_closed_via_adapter(tmp_path: Path) -> None:
    """Identity checks pass (the hash covers blocking_reason/slot/text only) but
    the adapter's Q1-D policy still rejects — proving delegation, not duplication."""
    for corruption in ("served", "requires_review"):
        payload = _valid_payload()
        payload[corruption] = not payload[corruption]
        path, digest = _write_addressed_artifact(tmp_path / f"questions_{corruption}", payload)

        resolution = resolve_served_ask_handle(
            RuntimeConfig(ask_serving_enabled=True), _handle(path, digest)
        )
        assert resolution.resolved is True  # identity intact

        acquired = acquire_served_ask_from_handle(
            RuntimeConfig(ask_serving_enabled=True),
            handle=_handle(path, digest),
            fallback_surface="fallback",
        )
        assert acquired.decision.served is False
        assert acquired.decision.surface == "fallback"


def test_question_path_equal_to_proposal_path_fails_closed(tmp_path: Path) -> None:
    payload = _valid_payload()
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), _handle(path, digest, proposal_path=path)
    )

    assert resolution.resolved is False
    assert resolution.reason == "path_collision"


def test_relative_proposal_path_same_file_as_absolute_question_path_fails_closed(
    tmp_path: Path,
) -> None:
    """A relative ``proposal_path`` and an absolute ``question_path`` that name the
    same file must collide and fail closed — the check compares canonical paths,
    not raw string spellings, so differing spellings of one file cannot slip past.
    """
    payload = _valid_payload()
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)
    assert path.is_absolute()

    # A genuinely relative spelling (from cwd) of the very same artifact file.
    relative_proposal = Path(os.path.relpath(path, Path.cwd()))
    assert not relative_proposal.is_absolute()
    assert relative_proposal.resolve(strict=False) == path.resolve(strict=False)
    assert str(relative_proposal) != str(path)

    handle = AskArtifactHandle(
        question_path=str(path),
        content_hash=digest,
        proposal_path=str(relative_proposal),
    )
    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), handle
    )

    assert resolution.resolved is False
    assert resolution.reason == "path_collision"


def test_stale_or_replaced_artifact_fails_closed(tmp_path: Path) -> None:
    """The file at the handle's path no longer re-hashes to the handle's address."""
    original = _valid_payload("How many crates are left?")
    path, digest = _write_addressed_artifact(tmp_path / "questions", original)

    replaced = _valid_payload("How many boxes were shipped?")
    path.write_text(json.dumps(replaced, indent=2, sort_keys=True), encoding="utf-8")

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), _handle(path, digest)
    )

    assert resolution.resolved is False
    assert resolution.reason == "content_hash_mismatch"


def test_handle_filename_must_be_content_addressed(tmp_path: Path) -> None:
    payload = _valid_payload()
    digest = _content_hash(payload)
    path = tmp_path / "questions" / "q.json"  # not the producer's addressed name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    resolution = resolve_served_ask_handle(
        RuntimeConfig(ask_serving_enabled=True), _handle(path, digest)
    )

    assert resolution.resolved is False
    assert resolution.reason == "handle_address_mismatch"


def test_structurally_invalid_handles_fail_closed(tmp_path: Path) -> None:
    config = RuntimeConfig(ask_serving_enabled=True)
    payload = _valid_payload()
    path, digest = _write_addressed_artifact(tmp_path / "questions", payload)

    assert resolve_served_ask_handle(config, None).reason == "missing_handle"
    assert (
        resolve_served_ask_handle(config, AskArtifactHandle("", digest)).reason
        == "malformed_handle"
    )
    assert (
        resolve_served_ask_handle(config, AskArtifactHandle("   ", digest)).reason
        == "malformed_handle"
    )
    assert (
        resolve_served_ask_handle(
            config, AskArtifactHandle(str(path), "not-a-sha256")
        ).reason
        == "malformed_handle"
    )
    assert (
        resolve_served_ask_handle(
            config, AskArtifactHandle(str(path), digest.upper())
        ).reason
        == "malformed_handle"
    )


# --- no-scan / boundary proofs -------------------------------------------------


def test_seam_cannot_discover_artifacts_without_exact_handle(tmp_path: Path) -> None:
    """A valid artifact sitting in the sink is unreachable without its exact
    content-addressed handle — there is no discovery path."""
    payload = _valid_payload()
    _write_addressed_artifact(tmp_path / "questions", payload)

    wrong_digest = hashlib.sha256(b"some-other-question").hexdigest()
    wrong = AskArtifactHandle(
        question_path=str(tmp_path / "questions" / f"{wrong_digest}.json"),
        content_hash=wrong_digest,
    )

    resolution = resolve_served_ask_handle(RuntimeConfig(ask_serving_enabled=True), wrong)

    assert resolution.resolved is False
    assert resolution.reason == "missing_artifact"


def test_seam_module_contains_no_sink_scanning_primitives() -> None:
    tree = ast.parse(_SEAM_PATH.read_text(encoding="utf-8"), filename=str(_SEAM_PATH))
    forbidden_attrs = {"glob", "rglob", "iterdir", "walk", "scandir", "listdir"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs, f"sink scan primitive: {node.attr}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_attrs


def test_seam_module_does_not_import_runtime_producer_or_renderer() -> None:
    source = _SEAM_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_SEAM_PATH))

    forbidden_modules = (
        "chat",
        "chat.runtime",
        "chat.ask_runtime",
        "generate.contemplation",
        "generate.contemplation.pass_manager",
        "generate.contemplation.findings",
        "core.epistemic_questions.render",
        "core.epistemic_questions.delivery",
    )
    forbidden_calls = {"contemplate", "deliver_ask", "render_question", "emit_question"}

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for forbidden in forbidden_modules:
                assert node.module != forbidden
                assert not node.module.startswith(forbidden + ".")
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_modules:
                    assert alias.name != forbidden
                    assert not alias.name.startswith(forbidden + ".")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls


def test_seam_module_constructs_no_question_prose() -> None:
    source = _SEAM_PATH.read_text(encoding="utf-8")
    for forbidden_template in ("How many", "What ", "Which ", "Please provide"):
        assert forbidden_template not in source
