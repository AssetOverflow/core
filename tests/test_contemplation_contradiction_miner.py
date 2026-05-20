from __future__ import annotations

import json
from pathlib import Path

from core.contemplation.__main__ import main
from core.contemplation.miners.contradiction_detection import (
    mine_contradiction_detection_report,
)
from core.contemplation.runner import (
    contemplate_contradiction_reports,
    write_contemplation_run,
)
from core.contemplation.schema import FindingKind
from core.contemplation.snapshot import ContemplationSubstrate
from teaching.epistemic import EpistemicStatus


_MISSED_CASE = {
    "id": "CON-PUB-002",
    "kind": "paired_contradiction",
    "passed": False,
    "flagged": False,
    "contested": False,
    "first_versor_condition": 0.0,
    "second_versor_condition": 0.0,
    "second_epistemic_status": "speculative",
    "versor_delta": 0.0,
    "versor_spike": False,
}

_FALSE_FLAG_CASE = {
    "id": "CON-PUB-005",
    "kind": "paired_consistent",
    "passed": False,
    "flagged": True,
    "contested": False,
    "first_versor_condition": 2.31891e-07,
    "second_versor_condition": 5.56303e-07,
    "second_epistemic_status": "speculative",
    "versor_delta": 3.24412e-07,
    "versor_spike": True,
}

_PASSED_CASE = {
    "id": "CON-PUB-001",
    "kind": "paired_contradiction",
    "passed": True,
    "flagged": True,
    "contested": False,
    "versor_delta": 3.28677e-07,
    "versor_spike": True,
}


def _sample_contradiction_report(path: Path) -> None:
    payload = {
        "lane": "contradiction_detection",
        "split": "public",
        "version": "v1",
        "timestamp": "2026-05-17T13:36:45.591040+00:00",
        "metrics": {"overall_pass": False},
        "cases": [_PASSED_CASE, _MISSED_CASE, _FALSE_FLAG_CASE],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_contradiction_miner_emits_one_finding_per_failure_mode(tmp_path: Path) -> None:
    report = tmp_path / "contradiction_public.json"
    _sample_contradiction_report(report)
    substrate = ContemplationSubstrate.from_report_paths((report,))

    findings = mine_contradiction_detection_report(
        report, substrate_hash=substrate.substrate_hash
    )

    # Passed case must not produce a finding; the two failure modes do.
    assert len(findings) == 2
    predicates = {f.predicate for f in findings}
    assert predicates == {"missed_contradiction", "false_contradiction_flag"}
    for finding in findings:
        assert finding.kind is FindingKind.CONTRADICTION
        assert finding.epistemic_status is EpistemicStatus.SPECULATIVE
        assert finding.subject.startswith("contradiction_detection/")
        # Evidence summary carries the case kind + signal columns so a
        # reviewer can act without re-running the lane.
        summary = finding.evidence_refs[0].summary
        assert "kind=" in summary
        assert "versor_delta=" in summary


def test_contradiction_miner_distinguishes_repair_action(tmp_path: Path) -> None:
    report = tmp_path / "contradiction_public.json"
    _sample_contradiction_report(report)
    substrate = ContemplationSubstrate.from_report_paths((report,))

    findings = mine_contradiction_detection_report(
        report, substrate_hash=substrate.substrate_hash
    )
    by_predicate = {f.predicate: f for f in findings}

    # Different failure modes call for different operator action — the
    # predicate split is load-bearing.  Pin the asymmetry so a future
    # refactor can't quietly collapse them.
    assert (
        by_predicate["missed_contradiction"].proposed_action
        != by_predicate["false_contradiction_flag"].proposed_action
    )
    assert "tighten" in by_predicate["missed_contradiction"].proposed_action
    assert "loosen" in by_predicate["false_contradiction_flag"].proposed_action


def test_contradiction_runner_is_replay_deterministic(tmp_path: Path) -> None:
    report = tmp_path / "contradiction_public.json"
    _sample_contradiction_report(report)

    first = contemplate_contradiction_reports(
        (report,), pack_ids=("en_core_cognition_v1",)
    )
    second = contemplate_contradiction_reports(
        (report,), pack_ids=("en_core_cognition_v1",)
    )

    assert first.run_id == second.run_id
    assert first.as_dict() == second.as_dict()
    assert all(
        f.epistemic_status is EpistemicStatus.SPECULATIVE for f in first.findings
    )


def test_contradiction_runner_config_hash_differs_from_frontier(tmp_path: Path) -> None:
    """Lane choice must be load-bearing in config_hash.

    If the two runners produced identical config_hash for the same
    input paths, replay would be unable to distinguish lanes — a
    silent collision the SPECULATIVE invariant cannot detect on its
    own.
    """
    from core.contemplation.runner import contemplate_frontier_reports

    report = tmp_path / "contradiction_public.json"
    _sample_contradiction_report(report)

    contradiction = contemplate_contradiction_reports((report,))
    frontier = contemplate_frontier_reports((report,))
    assert contradiction.config_hash != frontier.config_hash


def test_contradiction_runner_does_not_mutate_pack_tree(tmp_path: Path) -> None:
    report = tmp_path / "contradiction_public.json"
    _sample_contradiction_report(report)
    pack_root = Path("language_packs")
    before = sorted(
        (p.relative_to(pack_root).as_posix(), p.stat().st_mtime_ns, p.stat().st_size)
        for p in pack_root.rglob("*")
        if p.is_file()
    )

    contemplate_contradiction_reports((report,))

    after = sorted(
        (p.relative_to(pack_root).as_posix(), p.stat().st_mtime_ns, p.stat().st_size)
        for p in pack_root.rglob("*")
        if p.is_file()
    )
    assert before == after


def test_contradiction_cli_routes_through_lane_flag(
    tmp_path: Path, capsys
) -> None:
    source_report = tmp_path / "contradiction_public.json"
    output_report = tmp_path / "contemplation.json"
    _sample_contradiction_report(source_report)

    code = main(
        [
            str(source_report),
            "--lane",
            "contradiction_detection",
            "--report",
            str(output_report),
        ]
    )
    out = capsys.readouterr().out
    printed = json.loads(out)
    assert code == 0
    assert printed["finding_count"] == 2
    assert json.loads(output_report.read_text(encoding="utf-8")) == printed


def test_contradiction_runner_handles_real_report() -> None:
    """Smoke test against a real shipped lane artifact.

    Guards against the miner drifting away from the actual report
    schema the lane writes.  If this test breaks, either the lane
    output shape changed or the miner did.
    """
    report = Path("evals/contradiction_detection/results/v1_public_20260517T133645Z.json")
    if not report.exists():
        return  # artifact not present in this checkout; skip silently
    run = contemplate_contradiction_reports((report,))
    # Real artifact has at least one failing case (lane is not yet at
    # ``overall_pass=True``); finding count must reflect that.
    assert run.findings, "real lane report has failures but miner found none"
    assert all(
        f.epistemic_status is EpistemicStatus.SPECULATIVE for f in run.findings
    )
    # Write path round-trips deterministically.
    written = tmp_round_trip(run)
    assert written["run_id"] == run.run_id


def tmp_round_trip(run) -> dict:
    """Helper: write + read a run JSON in a temp file."""
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        path = Path(fh.name)
    try:
        write_contemplation_run(run, path)
        return json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)
