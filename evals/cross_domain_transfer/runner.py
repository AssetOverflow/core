"""cross-domain-transfer eval lane runner.

For each case: teach an R-chain in subdomain A, teach the same R-chain
in subdomain B (so B premises are in vault), probe the B-domain head,
score whether the B-domain endpoint appears in the response.

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


def _run_sequence(
    domain_a_premises: list[str],
    domain_b_premises: list[str],
    probe: str,
) -> dict[str, Any]:
    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)
    a_proposals = 0
    b_proposals = 0
    for p in domain_a_premises:
        try:
            r = pipeline.run(p, max_tokens=8)
        except ValueError:
            continue
        if r.pack_mutation_proposal is not None:
            a_proposals += 1
    for p in domain_b_premises:
        try:
            r = pipeline.run(p, max_tokens=8)
        except ValueError:
            continue
        if r.pack_mutation_proposal is not None:
            b_proposals += 1
    try:
        probe_result = pipeline.run(probe, max_tokens=8)
    except ValueError:
        return {
            "surface": "", "articulation_surface": "", "walk_surface": "",
            "trace_hash": "", "vault_hits": 0,
            "a_proposals": a_proposals, "b_proposals": b_proposals,
        }
    return {
        "surface": probe_result.surface or "",
        "articulation_surface": probe_result.articulation_surface or "",
        "walk_surface": probe_result.walk_surface or "",
        "trace_hash": probe_result.trace_hash,
        "vault_hits": int(probe_result.vault_hits),
        "a_proposals": a_proposals,
        "b_proposals": b_proposals,
    }


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    a_premises: list[str] = list(case.get("domain_a_premises", []))
    b_premises: list[str] = list(case.get("domain_b_premises", []))
    probe: str = case["probe"]
    endpoint_tokens: list[str] = list(case.get("expected_endpoint_tokens", []))
    expected_a = int(case.get("expected_a_proposals", len(a_premises) // 2))
    expected_b = int(case.get("expected_b_proposals", len(b_premises) // 2))

    first = _run_sequence(a_premises, b_premises, probe)
    second = _run_sequence(a_premises, b_premises, probe)

    surface_blob = " ".join([
        first["surface"], first["articulation_surface"], first["walk_surface"]
    ])
    endpoint_hit = _hit(surface_blob, endpoint_tokens)
    a_stored = first["a_proposals"] >= expected_a
    b_stored = first["b_proposals"] >= expected_b
    replay_pass = (
        bool(first["trace_hash"])
        and first["trace_hash"] == second["trace_hash"]
        and first["vault_hits"] == second["vault_hits"]
        and first["a_proposals"] == second["a_proposals"]
        and first["b_proposals"] == second["b_proposals"]
    )

    passed = endpoint_hit and a_stored and b_stored and replay_pass

    return {
        "id": case.get("id", ""),
        "pattern": case.get("pattern", ""),
        "endpoint_tokens": endpoint_tokens,
        "vault_hits": first["vault_hits"],
        "trace_hash": first["trace_hash"],
        "trace_hash_replay": second["trace_hash"],
        "a_proposals": first["a_proposals"],
        "b_proposals": first["b_proposals"],
        "expected_a": expected_a,
        "expected_b": expected_b,
        "transfer_endpoint_hit": endpoint_hit,
        "domain_a_stored_pass": a_stored,
        "domain_b_stored_pass": b_stored,
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

    transfer = sum(1 for d in case_details if d["transfer_endpoint_hit"]) / total
    a_stored = sum(1 for d in case_details if d["domain_a_stored_pass"]) / total
    b_stored = sum(1 for d in case_details if d["domain_b_stored_pass"]) / total
    replay = sum(1 for d in case_details if d["replay_pass"]) / total
    overall = sum(1 for d in case_details if d["passed"]) / total

    overall_pass = (
        transfer >= 0.50
        and a_stored >= 0.95
        and b_stored >= 0.95
        and replay >= 0.95
    )

    metrics: dict[str, Any] = {
        "transfer_endpoint_recall_rate": round(transfer, 4),
        "domain_a_stored_rate": round(a_stored, 4),
        "domain_b_stored_rate": round(b_stored, 4),
        "replay_determinism": round(replay, 4),
        "all_pass_rate": round(overall, 4),
        "case_count": total,
        "overall_pass": overall_pass,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
