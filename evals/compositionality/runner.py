"""compositionality eval lane runner.

For each case: teach the premises, probe a (relation, entity) pair
that was never directly taught, score whether the response surface
or walk surface references the expected composed token.

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
            "surface": "",
            "walk_surface": "",
            "trace_hash": "",
            "vault_hits": 0,
            "proposals": proposals,
        }
    return {
        "surface": probe_result.surface or "",
        "articulation_surface": probe_result.articulation_surface or "",
        "walk_surface": probe_result.walk_surface or "",
        "trace_hash": probe_result.trace_hash,
        "vault_hits": int(probe_result.vault_hits),
        "proposals": proposals,
    }


def _no_taught_pair_leakage(case: dict[str, Any]) -> bool:
    """Author-time invariant: probe expectation is not a verbatim premise."""
    for expected in case.get("expected_entailment_tokens", []):
        target = str(expected).lower()
        probe = str(case.get("probe", "")).lower()
        # The leakage check is structural: the probe entity is in premises
        # (expected) but the target must not appear together with the probe
        # entity in a single premise. Heuristic: target must not appear in
        # any premise that also contains the first noun of the probe.
        # For v1 we apply a simpler check — verify the (probe_entity, target)
        # pair does not co-occur in any premise.
        probe_tokens = _tokens(probe)
        for premise in case.get("premises", []):
            ptokens = _tokens(premise)
            if target in ptokens and probe_tokens & ptokens:
                return False
    return True


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    premises: list[str] = list(case.get("premises", []))
    probe: str = case["probe"]
    entailments: list[str] = list(case.get("expected_entailment_tokens", []))
    expected_proposals = int(case.get("expected_proposals", len(premises) // 2))

    first = _run_sequence(premises, probe)
    second = _run_sequence(premises, probe)

    surface_blob = " ".join([
        first["surface"], first.get("articulation_surface", ""), first["walk_surface"]
    ])
    comp_hit = _hit(surface_blob, entailments)
    premises_stored = first["proposals"] >= expected_proposals
    replay_pass = (
        bool(first["trace_hash"])
        and first["trace_hash"] == second["trace_hash"]
        and first["vault_hits"] == second["vault_hits"]
        and first["proposals"] == second["proposals"]
    )
    leakage_clean = _no_taught_pair_leakage(case)

    passed = comp_hit and premises_stored and replay_pass

    return {
        "id": case.get("id", ""),
        "pattern": case.get("pattern", ""),
        "entailment_tokens": entailments,
        "vault_hits": first["vault_hits"],
        "trace_hash": first["trace_hash"],
        "trace_hash_replay": second["trace_hash"],
        "proposals": first["proposals"],
        "expected_proposals": expected_proposals,
        "compositional_hit": comp_hit,
        "premises_stored_pass": premises_stored,
        "replay_pass": replay_pass,
        "leakage_clean": leakage_clean,
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

    comp = sum(1 for d in case_details if d["compositional_hit"]) / total
    stored = sum(1 for d in case_details if d["premises_stored_pass"]) / total
    replay = sum(1 for d in case_details if d["replay_pass"]) / total
    overall = sum(1 for d in case_details if d["passed"]) / total
    leakage = sum(1 for d in case_details if d["leakage_clean"]) / total

    overall_pass = comp >= 0.50 and stored >= 0.95 and replay >= 0.95

    metrics: dict[str, Any] = {
        "compositional_recall_rate": round(comp, 4),
        "premises_stored_rate": round(stored, 4),
        "replay_determinism": round(replay, 4),
        "no_leakage_rate": round(leakage, 4),
        "all_pass_rate": round(overall, 4),
        "case_count": total,
        "overall_pass": overall_pass,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
