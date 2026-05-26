from __future__ import annotations

import json
from pathlib import Path

import pytest

from workbench.readers import list_artifacts, list_proposals, read_artifact, read_proposal


@pytest.mark.parametrize(
    "artifact_id",
    [
        "../../pyproject.toml",
        "../engine_state/manifest.json",
        "/etc/passwd",
    ],
)
def test_read_artifact_rejects_path_traversal(artifact_id: str) -> None:
    with pytest.raises(ValueError):
        read_artifact(artifact_id)


def test_read_artifact_missing_file_raises_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        read_artifact("evals/does-not-exist.json")


def test_read_known_allowed_artifact_when_present() -> None:
    detail = read_artifact("evals/contemplation_quality/contract.md")

    assert detail.path == "evals/contemplation_quality/contract.md"
    assert detail.digest and detail.digest.startswith("sha256:")
    assert detail.content_type == "text"


def test_list_artifacts_hashes_without_reading_whole_files(monkeypatch) -> None:
    def fail_read_bytes(self: Path) -> bytes:
        raise AssertionError(f"list_artifacts should not call read_bytes: {self}")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    items = list_artifacts(limit=3)

    assert len(items) <= 3
    assert all(item.digest and item.digest.startswith("sha256:") for item in items)


def test_proposals_use_append_only_event_log_current_state(tmp_path: Path) -> None:
    log_path = tmp_path / "proposals.jsonl"
    proposal_id = "proposal-001"
    proposal = {
        "proposal_id": proposal_id,
        "source_candidate_id": "candidate-001",
        "proposed_chain": {
            "subject": "alpha",
            "intent": "cause",
            "connective": "causes",
            "object": "beta",
        },
        "polarity": "affirms",
        "claim_domain": "descriptive",
        "evidence": [],
        "source": {
            "kind": "contemplation",
            "source_id": "candidate-001",
            "emitted_at_revision": "abc123",
        },
        "review_state": "pending",
        "operator_note": "",
        "replay_evidence": None,
        "provenance": None,
    }
    replay = {
        "baseline": {"accuracy": 1.0},
        "candidate": {"accuracy": 1.0},
        "regressed_metrics": [],
        "replay_equivalent": True,
    }
    events = [
        {"event": "created", "proposal": proposal},
        {"event": "replay", "proposal_id": proposal_id, "replay_evidence": replay},
    ]
    log_path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )

    summaries = list_proposals(log_path=log_path)
    detail = read_proposal(proposal_id, log_path=log_path)

    assert [p.proposal_id for p in summaries] == [proposal_id]
    assert summaries[0].source_kind == "contemplation"
    assert summaries[0].replay_equivalent is True
    assert detail.proposed_chain == proposal["proposed_chain"]
    assert detail.replay_evidence == replay
