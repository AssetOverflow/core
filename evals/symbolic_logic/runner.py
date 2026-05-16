"""Symbolic-logic eval lane runner.

Tests the structural foundations CORE provides for proposition-based
inference: premise-chain storage, replay determinism, and recallability
from the probe.

For each case the runner:
  1. Runs the premise list on a fresh CognitiveTurnPipeline,
     collecting per-turn pack_mutation_proposal counts.
  2. Runs the probe on that pipeline.
  3. Runs the whole sequence again on a *separate* fresh pipeline
     to verify trace-hash determinism.

Sub-metrics (per case):
  M1. premise_recall   — probe vault_hits >= min_vault_hits
  M2. replay_determinism — trace_hash matches across the two runs
  M3. proposal_storage — count of fired proposals == expected_proposals

See contract.md for the structural claim and gaps.md for the
architectural findings underlying v1's signal choice.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_chain(
    premises: list[str],
    probe: str,
    config: RuntimeConfig | None,
) -> tuple[int, str, int]:
    """Return (vault_hits, trace_hash, proposal_count) for one fresh run."""
    runtime = ChatRuntime(config=config) if config else ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)
    proposal_count = 0
    for premise in premises:
        try:
            r = pipeline.run(premise, max_tokens=8)
        except ValueError:
            continue
        if r.pack_mutation_proposal is not None:
            proposal_count += 1
    try:
        probe_result = pipeline.run(probe, max_tokens=8)
    except ValueError:
        return 0, "", proposal_count
    return probe_result.vault_hits, probe_result.trace_hash, proposal_count


def _run_case(case: dict[str, Any], config: RuntimeConfig | None) -> dict[str, Any]:
    premises = case.get("premises", [])
    probe = case["probe"]
    min_vault_hits = int(case.get("min_vault_hits", 1))
    expected_proposals = int(case.get("expected_proposals", 0))

    vh1, hash1, pc1 = _run_chain(premises, probe, config)
    vh2, hash2, pc2 = _run_chain(premises, probe, config)

    premise_recall_pass = vh1 >= min_vault_hits
    replay_pass = bool(hash1) and hash1 == hash2 and vh1 == vh2 and pc1 == pc2
    proposal_pass = pc1 == expected_proposals

    return {
        "id": case.get("id", ""),
        "pattern": case.get("pattern", ""),
        "vault_hits": vh1,
        "trace_hash": hash1,
        "trace_hash_replay": hash2,
        "proposal_count": pc1,
        "expected_proposals": expected_proposals,
        "min_vault_hits": min_vault_hits,
        "premise_recall_pass": premise_recall_pass,
        "replay_pass": replay_pass,
        "proposal_pass": proposal_pass,
        "passed": premise_recall_pass and replay_pass and proposal_pass,
    }


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
) -> LaneReport:
    if not cases:
        return LaneReport(metrics={}, case_details=[])

    case_details = [_run_case(c, config) for c in cases]
    total = len(case_details)

    pr = sum(1 for d in case_details if d["premise_recall_pass"]) / total
    rd = sum(1 for d in case_details if d["replay_pass"]) / total
    ps = sum(1 for d in case_details if d["proposal_pass"]) / total
    overall = sum(1 for d in case_details if d["passed"]) / total

    overall_pass = pr >= 0.80 and rd >= 0.95 and ps >= 0.80

    metrics: dict[str, Any] = {
        "premise_recall": round(pr, 4),
        "replay_determinism": round(rd, 4),
        "proposal_storage": round(ps, 4),
        "all_three_pass_rate": round(overall, 4),
        "case_count": total,
        "overall_pass": overall_pass,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
