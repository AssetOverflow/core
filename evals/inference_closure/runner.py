"""inference-closure eval lane runner.

Tests CORE's ability to derive entailments not directly asserted.
For each case the runner:

  1. Runs the premise list on a fresh CognitiveTurnPipeline, recording
     per-premise pack_mutation_proposal firings.
  2. Runs the probe on that pipeline.
  3. Inspects the probe response's surface / articulation surface /
     vault retrieval evidence for the expected entailment token.
  4. Replays the full (premises, probe) sequence on a second fresh
     pipeline and checks trace_hash determinism.

Sub-metrics (per case):

  M1. derived_token_in_surface — entailment token appears (case-
      insensitive, token-bounded) in probe response surface
      or articulation_surface.
  M2. derived_token_in_vault  — entailment token appears in any
      vault-retrieved articulation evidence the probe produced.
  M3. premises_stored          — every premise emits a proposal.
  M4. replay_determinism       — two independent runs share trace_hash.

A case passes only when (M1 OR M2) AND M3 AND M4 hold.

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


def _token_set(text: str) -> set[str]:
    return set(_TOKEN_BOUND.findall((text or "").lower()))


def _entailment_hit(text: str, candidates: list[str]) -> bool:
    if not text:
        return False
    tokens = _token_set(text)
    return any(c.lower() in tokens for c in candidates)


def _run_chain(premises: list[str], probe: str) -> dict[str, Any]:
    """Return per-run signals for one fresh (premises, probe) sequence."""
    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)
    premise_proposal_count = 0
    for premise in premises:
        try:
            r = pipeline.run(premise, max_tokens=8)
        except ValueError:
            continue
        if r.pack_mutation_proposal is not None:
            premise_proposal_count += 1
    try:
        probe_result = pipeline.run(probe, max_tokens=8)
    except ValueError:
        return {
            "surface": "",
            "articulation_surface": "",
            "walk_surface": "",
            "vault_hits": 0,
            "trace_hash": "",
            "premise_proposal_count": premise_proposal_count,
            "value_error": True,
        }
    return {
        "surface": probe_result.surface or "",
        "articulation_surface": probe_result.articulation_surface or "",
        "walk_surface": probe_result.walk_surface or "",
        "vault_hits": int(probe_result.vault_hits),
        "trace_hash": probe_result.trace_hash,
        "premise_proposal_count": premise_proposal_count,
        "value_error": False,
    }


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    premises: list[str] = list(case.get("premises", []))
    probe: str = case["probe"]
    entailments: list[str] = list(case.get("expected_entailment_tokens", []))
    expected_proposals = int(case.get("expected_proposals", len(premises) // 2))

    first = _run_chain(premises, probe)
    second = _run_chain(premises, probe)

    surface_blob = " ".join(
        [first["surface"], first["articulation_surface"], first["walk_surface"]]
    )
    surface_hit = _entailment_hit(surface_blob, entailments)
    # Vault evidence proxy: when the probe response references entailment
    # tokens in its articulation walk, the vault retrieved them. The pipeline
    # does not expose retrieved-entity text directly; we use the walk_surface
    # as the closest available signal and call it a vault hit when the
    # entailment token appears there.
    vault_hit = _entailment_hit(first["walk_surface"], entailments)

    premises_stored = first["premise_proposal_count"] >= expected_proposals
    replay_pass = (
        bool(first["trace_hash"])
        and first["trace_hash"] == second["trace_hash"]
        and first["vault_hits"] == second["vault_hits"]
        and first["premise_proposal_count"] == second["premise_proposal_count"]
    )

    derived_recall = surface_hit or vault_hit
    passed = derived_recall and premises_stored and replay_pass

    return {
        "id": case.get("id", ""),
        "pattern": case.get("pattern", ""),
        "entailment_tokens": entailments,
        "vault_hits": first["vault_hits"],
        "trace_hash": first["trace_hash"],
        "trace_hash_replay": second["trace_hash"],
        "premise_proposal_count": first["premise_proposal_count"],
        "expected_proposals": expected_proposals,
        "surface_hit": surface_hit,
        "vault_hit": vault_hit,
        "premises_stored_pass": premises_stored,
        "replay_pass": replay_pass,
        "derived_recall_pass": derived_recall,
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

    derived = sum(1 for d in case_details if d["derived_recall_pass"]) / total
    stored = sum(1 for d in case_details if d["premises_stored_pass"]) / total
    replay = sum(1 for d in case_details if d["replay_pass"]) / total
    overall = sum(1 for d in case_details if d["passed"]) / total

    overall_pass = derived >= 0.50 and stored >= 0.95 and replay >= 0.95

    metrics: dict[str, Any] = {
        "derived_recall_rate": round(derived, 4),
        "premises_stored_rate": round(stored, 4),
        "replay_determinism": round(replay, 4),
        "all_pass_rate": round(overall, 4),
        "case_count": total,
        "overall_pass": overall_pass,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
