#!/usr/bin/env python3
"""Report ProblemFrame binding and organ-contract adequacy without solving."""
from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_contracts, recommended_migration_target


def assess_case(case: Mapping[str, Any], *, current_verdict: str | None = None) -> dict[str, Any]:
    text = str(case.get("question") or case.get("problem") or case.get("problem_text") or "")
    case_id = str(case.get("case_id") or case.get("id") or "unknown")
    frame = build_problem_frame(text)
    contracts = assess_contracts(frame)
    blockers_by_organ = {
        item.candidate_organ: sorted({*item.missing_bindings, *item.unresolved_hazards})
        for item in contracts
        if not item.runnable
    }
    return {
        "case_id": case_id,
        "current_verdict": current_verdict,
        "frame_built": True,
        "scalar_count": len(frame.quantities),
        "unit_count": len(frame.units),
        "entity_mention_count": sum(m.kind in {"entity", "actor", "object"} for m in frame.mentions),
        "quantity_binding_count": sum(b.binding_type == "quantity_entity" for b in frame.bindings),
        "process_relation_count": len(frame.bound_relations),
        "bound_question_target_present": bool(frame.bound_question_target and frame.bound_question_target.grounded),
        "candidate_organ_contracts": [item.candidate_organ for item in contracts],
        "runnable_contracts": [item.candidate_organ for item in contracts if item.runnable],
        "missing_binding_taxonomy": sorted({gap for item in contracts for gap in item.missing_bindings}),
        "unresolved_hazards": sorted({gap for item in contracts for gap in item.unresolved_hazards}),
        "blockers_by_organ": blockers_by_organ,
        "blocker_combinations_by_organ": {
            organ: "+".join(blockers) if blockers else "__runnable__"
            for organ, blockers in blockers_by_organ.items()
        },
        "recommended_next_migration_target": recommended_migration_target(contracts),
    }


def build_report(cases: Iterable[Mapping[str, Any]], *, verdicts: Mapping[str, str] | None = None) -> dict[str, Any]:
    verdicts = verdicts or {}
    per_case = [
        assess_case(case, current_verdict=verdicts.get(str(case.get("case_id") or case.get("id") or "unknown")))
        for case in cases
    ]
    blockers_by_organ: dict[str, dict[str, int]] = {}
    blocker_combinations_by_organ: dict[str, dict[str, int]] = {}
    for row in per_case:
        for organ, blockers in row["blockers_by_organ"].items():
            organ_counts = blockers_by_organ.setdefault(organ, {})
            for blocker in blockers:
                organ_counts[blocker] = organ_counts.get(blocker, 0) + 1
            combo = row["blocker_combinations_by_organ"][organ]
            combo_counts = blocker_combinations_by_organ.setdefault(organ, {})
            combo_counts[combo] = combo_counts.get(combo, 0) + 1
    return {
        "schema_version": 1,
        "case_count": len(per_case),
        "counts": {
            "frame_built": sum(row["frame_built"] for row in per_case),
            "scalar_present": sum(row["scalar_count"] > 0 for row in per_case),
            "unit_present": sum(row["unit_count"] > 0 for row in per_case),
            "entity_mention_present": sum(row["entity_mention_count"] > 0 for row in per_case),
            "quantity_binding_present": sum(row["quantity_binding_count"] > 0 for row in per_case),
            "process_relation_present": sum(row["process_relation_count"] > 0 for row in per_case),
            "bound_question_target_present": sum(row["bound_question_target_present"] for row in per_case),
            "contract_candidate_count": sum(len(row["candidate_organ_contracts"]) for row in per_case),
            "contract_runnable_count": sum(len(row["runnable_contracts"]) for row in per_case),
        },
        "blockers_by_organ": blockers_by_organ,
        "blocker_combinations_by_organ": blocker_combinations_by_organ,
        "per_case": per_case,
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    cases = _load_jsonl(args.cases)
    if args.limit is not None:
        cases = cases[:args.limit]
    print(json.dumps(build_report(cases), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
