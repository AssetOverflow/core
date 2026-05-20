from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.contemplation.__main__ import main
from core.contemplation.miners.frontier_compare import mine_frontier_compare_report
from core.contemplation.runner import contemplate_frontier_reports, write_contemplation_run
from core.contemplation.schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    FindingKind,
)
from core.contemplation.snapshot import ContemplationSubstrate
from teaching.epistemic import EpistemicStatus


def _sample_frontier_report(path: Path) -> None:
    payload = {
        "benchmark_family": "frontier_compare_wave1",
        "model": "core",
        "mode": "native",
        "summary": {"suite_count": 1, "case_count": 2, "primary_score": 0.5, "passed": False},
        "suites": [
            {
                "suite": "truth_lock",
                "case_count": 2,
                "primary_score": 0.5,
                "passed": False,
                "cases": [
                    {
                        "suite": "truth_lock",
                        "case_id": "known_truth",
                        "prompt": "What is truth?",
                        "passed": True,
                        "score": 1.0,
                        "elapsed_ms": 1.0,
                        "details": {},
                        "failures": [],
                    },
                    {
                        "suite": "truth_lock",
                        "case_id": "unknown_relation",
                        "prompt": "Why does xylomorphic matter?",
                        "passed": False,
                        "score": 0.0,
                        "elapsed_ms": 1.0,
                        "details": {},
                        "failures": ["unexpected_grounding_source:vault"],
                    },
                ],
            }
        ],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_contemplation_finding_rejects_non_speculative_status() -> None:
    evidence = ContemplationEvidenceRef(
        source_type="test",
        source_id="unit",
        pointer="case=1",
    )

    with pytest.raises(ValueError, match="SPECULATIVE"):
        ContemplationFinding(
            kind=FindingKind.BENCHMARK_CASE,
            subject="suite/case",
            predicate="failed_case",
            object="prompt",
            evidence_refs=(evidence,),
            proposed_action="review failure",
            substrate_hash="substrate",
            epistemic_status=EpistemicStatus.COHERENT,
        )


def test_contemplation_finding_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence"):
        ContemplationFinding(
            kind=FindingKind.BENCHMARK_CASE,
            subject="suite/case",
            predicate="failed_case",
            object="prompt",
            evidence_refs=(),
            proposed_action="review failure",
            substrate_hash="substrate",
        )


def test_frontier_report_miner_emits_failed_cases_only(tmp_path: Path) -> None:
    report = tmp_path / "frontier_wave1.json"
    _sample_frontier_report(report)
    substrate = ContemplationSubstrate.from_report_paths((report,))

    findings = mine_frontier_compare_report(report, substrate_hash=substrate.substrate_hash)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.kind is FindingKind.BENCHMARK_CASE
    assert finding.subject == "truth_lock/unknown_relation"
    assert finding.predicate == "failed_case"
    assert finding.object == "Why does xylomorphic matter?"
    assert finding.epistemic_status is EpistemicStatus.SPECULATIVE
    assert finding.evidence_refs[0].summary == "unexpected_grounding_source:vault"


def test_contemplation_runner_is_replay_deterministic(tmp_path: Path) -> None:
    report = tmp_path / "frontier_wave1.json"
    _sample_frontier_report(report)

    first = contemplate_frontier_reports((report,), pack_ids=("en_core_cognition_v1",))
    second = contemplate_frontier_reports((report,), pack_ids=("en_core_cognition_v1",))

    assert first.run_id == second.run_id
    assert first.as_dict() == second.as_dict()
    assert all(
        finding.epistemic_status is EpistemicStatus.SPECULATIVE
        for finding in first.findings
    )


def test_contemplation_runner_does_not_mutate_pack_tree(tmp_path: Path) -> None:
    report = tmp_path / "frontier_wave1.json"
    _sample_frontier_report(report)
    pack_root = Path("language_packs")
    before = sorted(
        (p.relative_to(pack_root).as_posix(), p.stat().st_mtime_ns, p.stat().st_size)
        for p in pack_root.rglob("*")
        if p.is_file()
    )

    contemplate_frontier_reports((report,))

    after = sorted(
        (p.relative_to(pack_root).as_posix(), p.stat().st_mtime_ns, p.stat().st_size)
        for p in pack_root.rglob("*")
        if p.is_file()
    )
    assert before == after


def test_contemplation_write_and_cli(tmp_path: Path, capsys) -> None:
    source_report = tmp_path / "frontier_wave1.json"
    output_report = tmp_path / "contemplation.json"
    _sample_frontier_report(source_report)

    run = contemplate_frontier_reports((source_report,))
    write_contemplation_run(run, output_report)
    written = json.loads(output_report.read_text(encoding="utf-8"))
    assert written["run_id"] == run.run_id
    assert written["finding_count"] == 1

    code = main([str(source_report), "--report", str(output_report)])
    out = capsys.readouterr().out
    printed = json.loads(out)
    assert code == 0
    assert printed["finding_count"] == 1
    assert json.loads(output_report.read_text(encoding="utf-8")) == printed
