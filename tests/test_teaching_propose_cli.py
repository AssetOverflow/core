"""Tests for W-019: core teaching propose-miner / propose-curriculum CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.contemplation.schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    FindingKind,
)
from teaching.epistemic import EpistemicStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _good_finding(
    *,
    subject: str = "knowledge",
    predicate: str = "requires",
    object_: str | None = "evidence",
    proposed_action: str = "extend cognition pack with knowledge→evidence chain",
    substrate_hash: str = "abc123",
) -> ContemplationFinding:
    return ContemplationFinding(
        kind=FindingKind.PACK_MUTATION_CANDIDATE,
        subject=subject,
        predicate=predicate,
        object=object_,
        evidence_refs=(
            ContemplationEvidenceRef(
                source_type="articulation_observation",
                source_id="run-1",
                pointer="turn:1",
                summary="weak surface",
            ),
        ),
        proposed_action=proposed_action,
        substrate_hash=substrate_hash,
    )


def _write_findings_jsonl(tmp_path: Path, findings: list) -> Path:
    path = tmp_path / "findings.jsonl"
    lines = [json.dumps(f.as_dict(), sort_keys=True, ensure_ascii=False) for f in findings]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# _load_findings_jsonl — unit test
# ---------------------------------------------------------------------------

def test_load_findings_jsonl_round_trips(tmp_path: Path) -> None:
    from core.cli import _load_findings_jsonl
    finding = _good_finding()
    jsonl_path = _write_findings_jsonl(tmp_path, [finding])
    loaded = _load_findings_jsonl(str(jsonl_path))
    assert len(loaded) == 1
    assert loaded[0].subject == "knowledge"
    assert loaded[0].kind is FindingKind.PACK_MUTATION_CANDIDATE
    assert loaded[0].epistemic_status is EpistemicStatus.SPECULATIVE


# ---------------------------------------------------------------------------
# cmd_teaching_propose_miner
# ---------------------------------------------------------------------------

def test_propose_miner_writes_proposals_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import argparse
    from core.cli import cmd_teaching_propose_miner

    finding = _good_finding()
    jsonl_path = _write_findings_jsonl(tmp_path, [finding])

    args = argparse.Namespace(
        findings=str(jsonl_path),
        miner_id="test_miner_v1",
        revision="test-revision",
        out=None,
    )
    rc = cmd_teaching_propose_miner(args)
    assert rc == 0
    captured = capsys.readouterr()
    proposal = json.loads(captured.out.strip().splitlines()[0])
    assert "proposal_id" in proposal
    assert proposal["subject"] == "knowledge"


def test_propose_miner_writes_to_file(tmp_path: Path) -> None:
    import argparse
    from core.cli import cmd_teaching_propose_miner

    finding = _good_finding()
    jsonl_path = _write_findings_jsonl(tmp_path, [finding])
    out_path = tmp_path / "out.jsonl"

    args = argparse.Namespace(
        findings=str(jsonl_path),
        miner_id="test_miner_v1",
        revision="test-revision",
        out=str(out_path),
    )
    rc = cmd_teaching_propose_miner(args)
    assert rc == 0
    lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    proposal = json.loads(lines[0])
    assert proposal["subject"] == "knowledge"


# ---------------------------------------------------------------------------
# cmd_teaching_propose_curriculum
# ---------------------------------------------------------------------------

def test_propose_curriculum_writes_proposals_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import argparse
    from core.cli import cmd_teaching_propose_curriculum

    finding = _good_finding(subject="truth", predicate="grounds", proposed_action="ground truth chain")
    jsonl_path = _write_findings_jsonl(tmp_path, [finding])

    args = argparse.Namespace(
        findings=str(jsonl_path),
        curriculum_id="gsm8k_curriculum_v1",
        revision="test-revision",
        out=None,
    )
    rc = cmd_teaching_propose_curriculum(args)
    assert rc == 0
    captured = capsys.readouterr()
    proposal = json.loads(captured.out.strip().splitlines()[0])
    assert "proposal_id" in proposal
    assert proposal["subject"] == "truth"


def test_propose_miner_returns_nonzero_on_empty_findings(tmp_path: Path) -> None:
    import argparse
    from core.cli import cmd_teaching_propose_miner

    empty_path = tmp_path / "empty.jsonl"
    empty_path.write_text("", encoding="utf-8")

    args = argparse.Namespace(
        findings=str(empty_path),
        miner_id="test_miner_v1",
        revision="test-revision",
        out=None,
    )
    with pytest.raises(SystemExit) as exc_info:
        cmd_teaching_propose_miner(args)
    assert exc_info.value.code == 1
