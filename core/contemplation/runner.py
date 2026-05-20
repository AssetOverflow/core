from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from core.contemplation.miners.frontier_compare import mine_frontier_compare_report
from core.contemplation.schema import ContemplationFinding, ContemplationRun
from core.contemplation.snapshot import ContemplationSubstrate


def _config_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def contemplate_frontier_reports(
    report_paths: Iterable[str | Path],
    *,
    pack_ids: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> ContemplationRun:
    """Run ADR-0080 Phase 1 over explicit frontier-compare reports.

    The runner is read-only.  It does not discover files implicitly, does not
    mutate packs, does not write teaching examples, and does not promote any
    finding beyond SPECULATIVE.
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


def write_contemplation_run(run: ContemplationRun, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(run.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = ["contemplate_frontier_reports", "write_contemplation_run"]
