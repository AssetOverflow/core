from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from core.contemplation.miners.contradiction_detection import (
    mine_contradiction_detection_report,
)
from core.contemplation.miners.frontier_compare import mine_frontier_compare_report
from core.contemplation.schema import (
    ContemplationFinding,
    ContemplationRun,
    format_contemplation_finding_jsonl,
)
from core.contemplation.snapshot import ContemplationSubstrate
from teaching.discovery_sink import DiscoveryCandidateSink


def _config_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _emit_findings(
    findings: Iterable[ContemplationFinding],
    sink: DiscoveryCandidateSink | None,
) -> None:
    """Stream each finding through the shared sink protocol when set.

    No-op when *sink* is ``None`` — preserves the existing "build a
    ``ContemplationRun`` blob" path for callers that want a single
    in-memory result.

    When a sink is supplied, each finding is emitted as one canonical
    JSONL line via :func:`format_contemplation_finding_jsonl`.  This
    is the unification point with the discovery candidate stream
    (ADR-0055 Phase B sinks): both flow through the same
    ``DiscoveryCandidateSink`` protocol, both land in append-only
    monthly JSONL files when paired with
    :class:`teaching.discovery_sink.DiscoveryMonthlyFileSink`.

    Sink errors are NOT swallowed — see ADR-0055 fail-fast contract.
    """
    if sink is None:
        return
    for finding in findings:
        sink.emit(format_contemplation_finding_jsonl(finding))


def contemplate_frontier_reports(
    report_paths: Iterable[str | Path],
    *,
    pack_ids: Iterable[str] = (),
    notes: Iterable[str] = (),
    sink: DiscoveryCandidateSink | None = None,
) -> ContemplationRun:
    """Run ADR-0080 Phase 1 over explicit frontier-compare reports.

    The runner is read-only.  It does not discover files implicitly, does not
    mutate packs, does not write teaching examples, and does not promote any
    finding beyond SPECULATIVE.

    When *sink* is supplied each finding is also emitted as one
    canonical JSONL line via the shared
    :class:`teaching.discovery_sink.DiscoveryCandidateSink` protocol,
    so contemplation findings flow into the same append-only stream
    discovery candidates use.
    """

    paths = tuple(Path(p) for p in report_paths)
    substrate = ContemplationSubstrate.from_report_paths(
        paths,
        pack_ids=tuple(pack_ids),
        notes=tuple(notes),
    )
    findings: list[ContemplationFinding] = []
    for path in paths:
        findings.extend(
            mine_frontier_compare_report(
                path,
                substrate_hash=substrate.substrate_hash,
            )
        )
    _emit_findings(findings, sink)
    config_hash = _config_hash(
        {
            "runner": "contemplate_frontier_reports",
            "report_paths": [str(p) for p in paths],
            "pack_ids": tuple(sorted(set(pack_ids))),
            "notes": tuple(notes),
        }
    )
    return ContemplationRun(
        substrate_hash=substrate.substrate_hash,
        config_hash=config_hash,
        findings=tuple(findings),
    )


def run_contemplation(
    report_paths: Iterable[str | Path] | None = None,
    *,
    pack_ids: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> ContemplationRun:
    """Run ADR-0080 Phase 1 over frontier-compare reports.

    This is the stable operator-facing entry point for Phase 1.  If no
    explicit paths are supplied it reads the checked-in
    ``evals/frontier_compare/results/*.json`` reports in deterministic
    path order.  It never writes packs, teaching examples, proposal logs,
    or discovery sinks.
    """
    if report_paths is None:
        root = Path(__file__).resolve().parents[2]
        paths = tuple(sorted(root.glob("evals/frontier_compare/results/*.json")))
    else:
        paths = tuple(Path(p) for p in report_paths)
    return contemplate_frontier_reports(
        paths,
        pack_ids=pack_ids,
        notes=notes,
        sink=None,
    )


def contemplate_contradiction_reports(
    report_paths: Iterable[str | Path],
    *,
    pack_ids: Iterable[str] = (),
    notes: Iterable[str] = (),
    sink: DiscoveryCandidateSink | None = None,
) -> ContemplationRun:
    """Run ADR-0080 Phase 1 over explicit contradiction-detection reports.

    Mirrors :func:`contemplate_frontier_reports` for the
    ``evals/contradiction_detection`` lane.  Same read-only guarantees,
    same SPECULATIVE-only finding contract, separate runner so the
    config hash records which lane was contemplated.
    """

    paths = tuple(Path(p) for p in report_paths)
    substrate = ContemplationSubstrate.from_report_paths(
        paths,
        pack_ids=tuple(pack_ids),
        notes=tuple(notes),
    )
    findings: list[ContemplationFinding] = []
    for path in paths:
        findings.extend(
            mine_contradiction_detection_report(
                path,
                substrate_hash=substrate.substrate_hash,
            )
        )
    _emit_findings(findings, sink)
    config_hash = _config_hash(
        {
            "runner": "contemplate_contradiction_reports",
            "report_paths": [str(p) for p in paths],
            "pack_ids": tuple(sorted(set(pack_ids))),
            "notes": tuple(notes),
        }
    )
    return ContemplationRun(
        substrate_hash=substrate.substrate_hash,
        config_hash=config_hash,
        findings=tuple(findings),
    )


def write_contemplation_run(run: ContemplationRun, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(run.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "contemplate_contradiction_reports",
    "contemplate_frontier_reports",
    "run_contemplation",
    "write_contemplation_run",
]
