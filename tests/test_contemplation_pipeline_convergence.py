"""Tests for the contemplation→teaching pipeline convergence refactor.

Pins three properties:

  1. ContemplationFinding emission flows through the SHARED sink
     protocol from teaching/discovery_sink.py — not a parallel
     bespoke sink.
  2. The contradiction_detection miner survives and works under the
     unified sink pattern (preserves the work from the closed #56
     while routing it through the corrected boundary).
  3. The boundary doc in core/contemplation/schema.py is intact —
     EvidencePointer (teaching) and ContemplationEvidenceRef (core)
     stay separate by design, not by oversight.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.contemplation.miners.contradiction_detection import (
    mine_contradiction_detection_report,
)
from core.contemplation.runner import (
    contemplate_contradiction_reports,
    contemplate_frontier_reports,
)
from core.contemplation.schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    FindingKind,
    format_contemplation_finding_jsonl,
)
from core.contemplation.snapshot import ContemplationSubstrate
from teaching.discovery_sink import (
    DiscoveryBufferSink,
    DiscoveryCandidateSink,
    DiscoveryMonthlyFileSink,
)
from teaching.epistemic import EpistemicStatus


# ---------------------------------------------------------------------------
# Fixtures: real-shape sample reports for both lanes
# ---------------------------------------------------------------------------


def _frontier_report(path: Path) -> None:
    payload = {
        "benchmark_family": "frontier_compare_wave1",
        "suites": [
            {
                "suite": "truth_lock",
                "cases": [
                    {
                        "suite": "truth_lock",
                        "case_id": "known_truth",
                        "prompt": "What is truth?",
                        "passed": True,
                        "failures": [],
                    },
                    {
                        "suite": "truth_lock",
                        "case_id": "unknown_relation",
                        "prompt": "Why does xylomorphic matter?",
                        "passed": False,
                        "failures": ["unexpected_grounding_source:vault"],
                    },
                ],
            }
        ],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _contradiction_report(path: Path) -> None:
    payload = {
        "lane": "contradiction_detection",
        "split": "public",
        "version": "v1",
        "cases": [
            {
                "id": "CON-PUB-001",
                "kind": "paired_contradiction",
                "passed": True,
                "flagged": True,
                "contested": False,
                "versor_delta": 3.28677e-07,
                "versor_spike": True,
            },
            {
                "id": "CON-PUB-002",
                "kind": "paired_contradiction",
                "passed": False,
                "flagged": False,
                "contested": False,
                "versor_delta": 0.0,
                "versor_spike": False,
            },
            {
                "id": "CON-PUB-005",
                "kind": "paired_consistent",
                "passed": False,
                "flagged": True,
                "contested": False,
                "versor_delta": 3.24412e-07,
                "versor_spike": True,
            },
        ],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Shared sink protocol — the actual integration claim
# ---------------------------------------------------------------------------


def test_sink_is_typed_as_discovery_candidate_sink() -> None:
    """DiscoveryBufferSink must satisfy DiscoveryCandidateSink — that is
    the shared protocol both pipelines now feed.

    A static structural check, but if someone widens the protocol in
    teaching/discovery_sink.py without adapting the contemplation
    emitter, this test surfaces the regression at the type level.
    """
    sink: DiscoveryCandidateSink = DiscoveryBufferSink()
    assert hasattr(sink, "emit")
    sink.emit("{}")
    assert sink.lines == ["{}"]


def test_frontier_runner_emits_findings_to_shared_sink(tmp_path: Path) -> None:
    report = tmp_path / "frontier.json"
    _frontier_report(report)
    sink = DiscoveryBufferSink()

    run = contemplate_frontier_reports((report,), sink=sink)

    # One emission per finding, no extra noise (passing cases don't emit).
    assert len(sink.lines) == 1
    assert len(run.findings) == 1
    # The emitted line round-trips to the same payload as the run blob.
    emitted = json.loads(sink.lines[0])
    assert emitted == run.findings[0].as_dict()


def test_contradiction_runner_emits_findings_to_shared_sink(tmp_path: Path) -> None:
    report = tmp_path / "contradiction.json"
    _contradiction_report(report)
    sink = DiscoveryBufferSink()

    run = contemplate_contradiction_reports((report,), sink=sink)

    # Two failed cases (1 missed, 1 false-flag); passing case suppressed.
    assert len(sink.lines) == 2
    assert len(run.findings) == 2
    predicates = {json.loads(line)["predicate"] for line in sink.lines}
    assert predicates == {"missed_contradiction", "false_contradiction_flag"}


def test_sink_is_optional_no_op_when_absent(tmp_path: Path) -> None:
    """Existing in-memory ContemplationRun behavior is preserved when
    no sink is supplied — guarantees the refactor is non-breaking."""
    report = tmp_path / "contradiction.json"
    _contradiction_report(report)

    run = contemplate_contradiction_reports((report,))  # no sink kwarg

    assert len(run.findings) == 2
    assert all(
        f.epistemic_status is EpistemicStatus.SPECULATIVE for f in run.findings
    )


def test_emission_is_jsonl_canonical(tmp_path: Path) -> None:
    """The JSONL line shape must match the discovery_sink convention:
    one canonical-JSON line per finding, sorted keys, no newline,
    deterministic across runs."""
    report = tmp_path / "contradiction.json"
    _contradiction_report(report)
    sink_a = DiscoveryBufferSink()
    sink_b = DiscoveryBufferSink()

    contemplate_contradiction_reports((report,), sink=sink_a)
    contemplate_contradiction_reports((report,), sink=sink_b)

    assert sink_a.lines == sink_b.lines
    for line in sink_a.lines:
        assert "\n" not in line
        # Canonical JSON: re-encoding with same options reproduces the line.
        parsed = json.loads(line)
        roundtrip = json.dumps(
            parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        assert line == roundtrip


def test_monthly_file_sink_persists_contemplation_findings(
    tmp_path: Path,
) -> None:
    """End-to-end: contemplation findings land in the SAME monthly JSONL
    layout discovery candidates use — <root>/<YYYY>/<YYYY-MM>.jsonl."""
    report = tmp_path / "contradiction.json"
    _contradiction_report(report)
    sink_root = tmp_path / "discovery_log"

    with DiscoveryMonthlyFileSink(sink_root) as sink:
        run = contemplate_contradiction_reports((report,), sink=sink)
    assert len(run.findings) == 2

    # Find the monthly file the sink created.
    written = sorted(sink_root.rglob("*.jsonl"))
    assert len(written) == 1, f"expected one monthly file, got {written}"
    lines = [
        line
        for line in written[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 2
    # Layout matches discovery candidate convention <YYYY>/<YYYY-MM>.jsonl.
    rel = written[0].relative_to(sink_root)
    assert len(rel.parts) == 2  # YYYY / YYYY-MM.jsonl
    assert rel.parts[1].endswith(".jsonl")


def test_sink_emission_does_not_alter_run_blob(tmp_path: Path) -> None:
    """Emitting to a sink and building the ContemplationRun blob must
    produce IDENTICAL findings — the sink path is additional output,
    not a parallel transformation."""
    report = tmp_path / "frontier.json"
    _frontier_report(report)

    run_no_sink = contemplate_frontier_reports((report,))
    sink = DiscoveryBufferSink()
    run_with_sink = contemplate_frontier_reports((report,), sink=sink)

    assert run_no_sink.run_id == run_with_sink.run_id
    assert run_no_sink.as_dict() == run_with_sink.as_dict()


# ---------------------------------------------------------------------------
# 2. Contradiction miner — preserved from closed #56, now under the
#    unified sink contract
# ---------------------------------------------------------------------------


def test_contradiction_miner_predicate_split(tmp_path: Path) -> None:
    report = tmp_path / "contradiction.json"
    _contradiction_report(report)
    substrate = ContemplationSubstrate.from_report_paths((report,))

    findings = mine_contradiction_detection_report(
        report, substrate_hash=substrate.substrate_hash
    )
    by_predicate = {f.predicate: f for f in findings}
    assert set(by_predicate.keys()) == {
        "missed_contradiction",
        "false_contradiction_flag",
    }
    # Repair-action asymmetry: tightening (missed) vs loosening (false flag).
    assert "tighten" in by_predicate["missed_contradiction"].proposed_action
    assert "loosen" in by_predicate["false_contradiction_flag"].proposed_action
    # All findings emit FindingKind.CONTRADICTION (not BENCHMARK_CASE) —
    # the lane is semantically targeted.
    for finding in findings:
        assert finding.kind is FindingKind.CONTRADICTION


def test_contradiction_config_hash_differs_from_frontier(tmp_path: Path) -> None:
    """Lane choice must remain load-bearing in config_hash so replay
    can distinguish which lane was contemplated.  Regression guard
    against a future refactor that accidentally unifies the runners."""
    report = tmp_path / "shared.json"
    _contradiction_report(report)
    a = contemplate_contradiction_reports((report,))
    b = contemplate_frontier_reports((report,))
    assert a.config_hash != b.config_hash


# ---------------------------------------------------------------------------
# 3. Boundary doc — the deliberate non-merger of evidence types
# ---------------------------------------------------------------------------


def test_boundary_doc_present_in_schema_module() -> None:
    """The BOUNDARY note in core/contemplation/schema.py is the
    durable record of why EvidencePointer and ContemplationEvidenceRef
    stay separate.  Pinning its presence prevents a future contributor
    from silently deleting the boundary rationale."""
    schema_text = Path("core/contemplation/schema.py").read_text(encoding="utf-8")
    assert "BOUNDARY" in schema_text
    assert "EvidencePointer" in schema_text
    assert "vault_coherent" in schema_text


def test_contemplation_evidence_ref_rejects_empty_fields() -> None:
    """The existing schema invariants must survive the refactor."""
    with pytest.raises(ValueError, match="source_type"):
        ContemplationEvidenceRef(source_type="", source_id="x", pointer="y")
    with pytest.raises(ValueError, match="source_id"):
        ContemplationEvidenceRef(source_type="x", source_id="", pointer="y")
    with pytest.raises(ValueError, match="pointer"):
        ContemplationEvidenceRef(source_type="x", source_id="y", pointer="")


def test_format_contemplation_finding_jsonl_is_deterministic() -> None:
    finding = ContemplationFinding(
        kind=FindingKind.CONTRADICTION,
        subject="lane/case_001",
        predicate="missed_contradiction",
        object=None,
        evidence_refs=(
            ContemplationEvidenceRef(
                source_type="t", source_id="i", pointer="p", summary="s"
            ),
        ),
        proposed_action="review",
        substrate_hash="abc123",
    )
    a = format_contemplation_finding_jsonl(finding)
    b = format_contemplation_finding_jsonl(finding)
    assert a == b
    # Round-trips through json.loads/dumps with same options.
    parsed = json.loads(a)
    assert (
        json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        == a
    )
