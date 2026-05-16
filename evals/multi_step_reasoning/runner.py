"""multi-step-reasoning eval lane runner.

For each case: teach a 3- to 5-hop chain, probe the head, score
whether the final-hop entity appears in the response surface.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals.parallel import run_cases_parallel


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


_TOKEN_BOUND = re.compile(r"\b([a-z][a-z'\-]*)\b")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_BOUND.findall((text or "").lower()))


def _hit(text: str, candidates: list[str]) -> bool:
    if not text:
        return False
    toks = _tokens(text)
    return any(c.lower() in toks for c in candidates)


def _run_sequence(premises: list[str], probe: str) -> dict[str, Any]:
    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)
    proposals = 0
    for premise in premises:
        try:
            r = pipeline.run(premise, max_tokens=8)
        except ValueError:
            continue
        if r.pack_mutation_proposal is not None:
            proposals += 1
    try:
        probe_result = pipeline.run(probe, max_tokens=8)
    except ValueError:
        return {
            "surface": "", "articulation_surface": "", "walk_surface": "",
            "trace_hash": "", "vault_hits": 0, "proposals": proposals,
        }
    return {
        "surface": probe_result.surface or "",
        "articulation_surface": probe_result.articulation_surface or "",
        "walk_surface": probe_result.walk_surface or "",
        "trace_hash": probe_result.trace_hash,
        "vault_hits": int(probe_result.vault_hits),
        "proposals": proposals,
    }


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    premises: list[str] = list(case.get("premises", []))
    probe: str = case["probe"]
    endpoint_tokens: list[str] = list(case.get("expected_endpoint_tokens", []))
    intermediates: list[str] = list(case.get("intermediate_tokens", []))
    expected_proposals = int(case.get("expected_proposals", len(premises) // 2))

    first = _run_sequence(premises, probe)
    second = _run_sequence(premises, probe)

    surface_blob = " ".join([
        first["surface"], first["articulation_surface"], first["walk_surface"]
    ])
    endpoint_hit = _hit(surface_blob, endpoint_tokens)
    intermediate_hit = _hit(surface_blob, intermediates)
    premises_stored = first["proposals"] >= expected_proposals
    replay_pass = (
        bool(first["trace_hash"])
        and first["trace_hash"] == second["trace_hash"]
        and first["vault_hits"] == second["vault_hits"]
        and first["proposals"] == second["proposals"]
    )

    passed = endpoint_hit and premises_stored and replay_pass

    return {
        "id": case.get("id", ""),
        "pattern": case.get("pattern", ""),
        "hops": int(case.get("hops", 0)),
        "endpoint_tokens": endpoint_tokens,
        "vault_hits": first["vault_hits"],
        "trace_hash": first["trace_hash"],
        "trace_hash_replay": second["trace_hash"],
        "proposals": first["proposals"],
        "expected_proposals": expected_proposals,
        "endpoint_hit": endpoint_hit,
        "intermediate_hit": intermediate_hit,
        "premises_stored_pass": premises_stored,
        "replay_pass": replay_pass,
        "passed": passed,
    }


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> LaneReport:
    if not cases:
        return LaneReport(metrics={}, case_details=[])
    _ = config

    case_details = run_cases_parallel(cases, _run_case, workers=workers)
    total = len(case_details)

    endpoint = sum(1 for d in case_details if d["endpoint_hit"]) / total
    intermediate = sum(1 for d in case_details if d["intermediate_hit"]) / total
    stored = sum(1 for d in case_details if d["premises_stored_pass"]) / total
    replay = sum(1 for d in case_details if d["replay_pass"]) / total
    overall = sum(1 for d in case_details if d["passed"]) / total

    overall_pass = endpoint >= 0.50 and stored >= 0.95 and replay >= 0.95

    metrics: dict[str, Any] = {
        "chain_endpoint_recall_rate": round(endpoint, 4),
        "intermediate_hop_visible_rate": round(intermediate, 4),
        "premises_stored_rate": round(stored, 4),
        "replay_determinism": round(replay, 4),
        "all_pass_rate": round(overall, 4),
        "case_count": total,
        "overall_pass": overall_pass,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
