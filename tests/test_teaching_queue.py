"""Tests for ADR-0161 human-in-the-loop review queue read-only commands."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from core.cli import main
from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import ProposalLog, ReplayEvidence, build_proposal
from teaching.queue import derive_queue, find_queue_item


def make_candidate(candidate_id: str, subject: str, obj: str = "truth") -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain={
            "subject": subject,
            "intent": "cause",
            "connective": "reveals",
            "object": obj,
        },
        trigger="would_have_grounded",
        source_turn_trace="trace_1",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref="some_chain",
                polarity="affirms",
                epistemic_status="coherent",
            ),
        ),
    )


def run_cli(args: list[str]) -> tuple[int, str, str]:
    with patch("sys.argv", ["core"] + args), patch("sys.stdout", new_callable=StringIO) as out, patch("sys.stderr", new_callable=StringIO) as err:
        try:
            code = main()
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 0
        return code, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# derive_queue purity and determinism
# ---------------------------------------------------------------------------


def test_derive_queue_purity(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    log.record_created(p1)

    res1 = derive_queue(log)
    res2 = derive_queue(log)

    assert res1 == res2


def test_derive_queue_determinism(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)
    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    log.record_created(p1)

    res1 = derive_queue(log)
    res2 = derive_queue(log)
    assert res1 == res2


# ---------------------------------------------------------------------------
# State derivation
# ---------------------------------------------------------------------------


def test_state_derivation(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    log.record_created(p1)

    items = derive_queue(log)
    assert len(items) == 1
    assert items[0].state == "pending"

    log.record_transition(p1.proposal_id, "accepted", "review accepted")
    items = derive_queue(log)
    assert len(items) == 1
    assert items[0].state == "accepted"

    log.record_transition(p1.proposal_id, "withdrawn", "review withdrawn")
    items = derive_queue(log)
    assert len(items) == 1
    assert items[0].state == "withdrawn"


# ---------------------------------------------------------------------------
# Age proposals
# ---------------------------------------------------------------------------


def test_age_proposals(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    c2 = make_candidate("cand2", "dark")
    p2 = build_proposal(c2)
    c3 = make_candidate("cand3", "shade")
    p3 = build_proposal(c3)

    log.record_created(p1)
    log.record_created(p2)
    log.record_created(p3)

    items = derive_queue(log)
    assert len(items) == 3
    assert items[0].proposal_id == p1.proposal_id
    assert items[1].proposal_id == p2.proposal_id
    assert items[2].proposal_id == p3.proposal_id

    assert items[0].age_proposals == 2
    assert items[1].age_proposals == 1
    assert items[2].age_proposals == 0

    log.record_transition(p1.proposal_id, "accepted", "accepting first")
    items = derive_queue(log)
    assert items[0].age_proposals == 0
    assert items[1].age_proposals == 1
    assert items[2].age_proposals == 0


# ---------------------------------------------------------------------------
# Contemplation report path
# ---------------------------------------------------------------------------


def test_contemplation_report_path(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    c2 = make_candidate("cand2", "dark")
    p2 = build_proposal(c2)
    c3 = make_candidate("cand3", "shade")
    p3 = build_proposal(c3)

    log.record_created(p1)
    log.record_created(p2)
    log.record_created(p3)

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    run1_path = runs_dir / "run1.json"
    run1_path.write_text(json.dumps({
        "proposal_id": p1.proposal_id,
        "scenes": []
    }))

    run2_path = runs_dir / "run2.json"
    run2_path.write_text(json.dumps({
        "scenes": [
            {
                "scene": "S3_engine_authored_proposal",
                "detail": {
                    "proposal_id": p2.proposal_id
                }
            }
        ]
    }))

    items = derive_queue(log, contemplation_runs_dir=runs_dir)
    assert len(items) == 3

    assert items[0].proposal_id == p1.proposal_id
    assert items[0].contemplation_report_path == str(run1_path.resolve())

    assert items[1].proposal_id == p2.proposal_id
    assert items[1].contemplation_report_path == str(run2_path.resolve())

    assert items[2].proposal_id == p3.proposal_id
    assert items[2].contemplation_report_path is None


# ---------------------------------------------------------------------------
# Review history
# ---------------------------------------------------------------------------


def test_review_history(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    log.record_created(p1)

    log.record_transition(p1.proposal_id, "rejected", "regression check")
    log.record_transition(p1.proposal_id, "pending", "re-evaluated")
    log.record_transition(p1.proposal_id, "accepted", "approved")

    items = derive_queue(log)
    assert len(items) == 1
    item = items[0]

    assert len(item.review_history) == 3
    assert item.review_history[0]["to"] == "rejected"
    assert item.review_history[0]["note"] == "regression check"
    assert item.review_history[1]["to"] == "pending"
    assert item.review_history[1]["note"] == "re-evaluated"
    assert item.review_history[2]["to"] == "accepted"
    assert item.review_history[2]["note"] == "approved"


# ---------------------------------------------------------------------------
# find_queue_item
# ---------------------------------------------------------------------------


def test_find_queue_item(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    c2 = make_candidate("cand2", "dark")
    p2 = build_proposal(c2)

    log.record_created(p1)
    log.record_created(p2)

    res = find_queue_item(log, p1.proposal_id)
    assert res is not None
    assert res.proposal_id == p1.proposal_id

    prefix = p2.proposal_id[:12]
    res_prefix = find_queue_item(log, prefix)
    assert res_prefix is not None
    assert res_prefix.proposal_id == p2.proposal_id

    assert find_queue_item(log, "non_existent_id") is None

    common_prefix = p1.proposal_id[0]
    if p2.proposal_id.startswith(common_prefix):
        assert find_queue_item(log, common_prefix) is None


# ---------------------------------------------------------------------------
# CLI list and show commands
# ---------------------------------------------------------------------------


def test_cli_list_command(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)
    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    log.record_created(p1)

    log.record_replay(p1.proposal_id, ReplayEvidence(
        baseline={}, candidate={}, regressed_metrics=(), replay_equivalent=True
    ))

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    code, stdout, stderr = run_cli([
        "teaching", "queue", "list",
        "--log-path", str(log_path),
        "--contemplation-runs-dir", str(runs_dir)
    ])
    assert code == 0
    assert "proposal_id" in stdout
    assert "source_kind" in stdout
    assert "state" in stdout
    assert "age" in stdout
    assert "replay" in stdout
    assert p1.proposal_id[:12] in stdout
    assert "ok" in stdout

    code_j, stdout_j, stderr_j = run_cli([
        "teaching", "queue", "list",
        "--log-path", str(log_path),
        "--contemplation-runs-dir", str(runs_dir),
        "--json"
    ])
    assert code_j == 0
    parsed = json.loads(stdout_j)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["proposal_id"] == p1.proposal_id
    assert parsed[0]["source_kind"] == "operator"
    assert parsed[0]["state"] == "pending"
    assert parsed[0]["age_proposals"] == 0
    assert parsed[0]["replay_evidence"]["replay_equivalent"] is True


def test_cli_show_command(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    c1 = make_candidate("cand1", "light")
    p1 = build_proposal(c1)
    c2 = make_candidate("cand2", "dark")
    p2 = build_proposal(c2)

    log.record_created(p1)
    log.record_created(p2)

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    code, stdout, stderr = run_cli([
        "teaching", "queue", "show", p1.proposal_id,
        "--log-path", str(log_path),
        "--contemplation-runs-dir", str(runs_dir)
    ])
    assert code == 0
    assert f"Proposal ID: {p1.proposal_id}" in stdout
    assert "ADR References:" in stdout

    prefix = p2.proposal_id[:12]
    code_p, stdout_p, stderr_p = run_cli([
        "teaching", "queue", "show", prefix,
        "--log-path", str(log_path),
        "--contemplation-runs-dir", str(runs_dir)
    ])
    assert code_p == 0
    assert f"Proposal ID: {p2.proposal_id}" in stdout_p

    code_m, stdout_m, stderr_m = run_cli([
        "teaching", "queue", "show", "nonexistent_id",
        "--log-path", str(log_path),
        "--contemplation-runs-dir", str(runs_dir)
    ])
    assert code_m != 0
    assert "error:" in stderr_m
    assert "matches zero queue items" in stderr_m

    common_prefix = ""
    for char1, char2 in zip(p1.proposal_id, p2.proposal_id):
        if char1 == char2:
            common_prefix += char1
        else:
            break
    if common_prefix:
        code_a, stdout_a, stderr_a = run_cli([
            "teaching", "queue", "show", common_prefix,
            "--log-path", str(log_path),
            "--contemplation-runs-dir", str(runs_dir)
        ])
        assert code_a != 0
        assert "error:" in stderr_a
        assert "ambiguous" in stderr_a


# ---------------------------------------------------------------------------
# Read-only invariant
# ---------------------------------------------------------------------------


def snapshot_dir(directory: Path) -> dict[Path, bytes]:
    snapshot = {}
    if not directory.exists():
        return snapshot
    for path in directory.glob("**/*"):
        if path.is_file():
            snapshot[path] = path.read_bytes()
    return snapshot


def test_read_only_invariant():
    project_root = Path(__file__).resolve().parent.parent
    dirs = [
        project_root / "teaching" / "proposals",
        project_root / "packs",
        project_root / "engine_state",
        project_root / "contemplation" / "runs",
    ]

    before_snapshots = {}
    for d in dirs:
        before_snapshots[d] = snapshot_dir(d)

    run_cli(["teaching", "queue", "list"])
    run_cli(["teaching", "queue", "show", "nonexistent"])

    for d in dirs:
        after_snapshot = snapshot_dir(d)
        assert after_snapshot == before_snapshots[d], f"Directory {d} was mutated!"
