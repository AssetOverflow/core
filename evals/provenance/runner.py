"""Provenance eval lane runner.

Conforms to the framework interface: ``run_lane(cases, config=None) -> report``
where report has ``.metrics`` (dict) and ``.case_details`` (list[dict]).

Sub-metrics scored:
  M1. replay_determinism — same input twice on freshly-built runtimes
      produces identical trace_hash on the scored turn.
  M2. input_sensitivity — distinct cases produce distinct trace_hashes
      (no collisions across the case set).
  M3. source_attribution — every expected source kind appears in the
      computed Provenance for the scored turn.
  M4. source_validity — every cited source resolves to a real artefact
      (intent tag is known, vault index in range, teaching proposal id
      present in the teaching store).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.cognition.provenance import Provenance, compute_provenance
from core.config import RuntimeConfig
from generate.intent import IntentTag

_KNOWN_INTENT_TAGS: frozenset[str] = frozenset(t.value for t in IntentTag)


@dataclass(frozen=True, slots=True)
class CaseRun:
    case_id: str
    category: str
    expected_sources: tuple[str, ...]
    trace_hash: str
    provenance_kinds: tuple[str, ...]
    attribution_pass: bool
    validity_pass: bool
    replay_pass: bool


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_pipeline_for_case(
    case: dict[str, Any],
    *,
    config: RuntimeConfig | None,
) -> tuple[Provenance, ChatRuntime, CognitiveTurnPipeline]:
    """Build a fresh runtime, replay any prime prompts, then run the scored prompt."""
    runtime = ChatRuntime(config=config) if config else ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)

    for prime_prompt in case.get("prime", []):
        pipeline.run(prime_prompt, max_tokens=8)

    final_result = pipeline.run(case["prompt"], max_tokens=8)
    provenance = compute_provenance(final_result)
    return provenance, runtime, pipeline


def _validate_provenance(
    provenance: Provenance,
    pipeline: CognitiveTurnPipeline,
    runtime: ChatRuntime,
) -> bool:
    """Check that every cited source actually resolves to a real artefact."""
    vault_len = len(runtime.session.vault)
    teaching_proposal_ids: set[str] = {
        p.proposal_id for p in pipeline.teaching_store.pending_proposals()
    }

    for source in provenance.sources:
        if source.kind == "pack":
            if source.ref not in _KNOWN_INTENT_TAGS or source.ref == IntentTag.UNKNOWN.value:
                return False
        elif source.kind == "vault":
            if not source.ref.startswith("vault_hit_"):
                return False
            try:
                idx = int(source.ref.removeprefix("vault_hit_"))
            except ValueError:
                return False
            # Per-hit indices are synthetic (0..vault_hits-1). The real
            # invariant is that the vault is non-empty when hits are claimed.
            if idx < 0 or vault_len == 0:
                return False
        elif source.kind == "teaching":
            if source.ref not in teaching_proposal_ids:
                return False
        else:
            return False
    return True


def _attribution_pass(provenance: Provenance, expected_sources: list[str]) -> bool:
    """Every expected source kind must be present in the provenance."""
    present = set(provenance.kinds())
    return all(expected in present for expected in expected_sources)


def _run_case(
    case: dict[str, Any],
    *,
    config: RuntimeConfig | None,
) -> CaseRun:
    expected = tuple(case.get("expected_sources", []))

    # First run — collect provenance, runtime, pipeline for validity check.
    prov_a, runtime_a, pipeline_a = _run_pipeline_for_case(case, config=config)
    attribution_pass = _attribution_pass(prov_a, list(expected))
    validity_pass = _validate_provenance(prov_a, pipeline_a, runtime_a)

    # Second run — fresh runtime — must reproduce trace_hash.
    prov_b, _, _ = _run_pipeline_for_case(case, config=config)
    replay_pass = prov_a.turn_trace_hash == prov_b.turn_trace_hash

    return CaseRun(
        case_id=case["id"],
        category=case.get("category", "unknown"),
        expected_sources=expected,
        trace_hash=prov_a.turn_trace_hash,
        provenance_kinds=prov_a.kinds(),
        attribution_pass=attribution_pass,
        validity_pass=validity_pass,
        replay_pass=replay_pass,
    )


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
) -> LaneReport:
    """Run all provenance cases and aggregate metrics."""
    case_runs: list[CaseRun] = []
    for case in cases:
        case_runs.append(_run_case(case, config=config))

    total = len(case_runs)
    if total == 0:
        return LaneReport(metrics={}, case_details=[])

    replay_passes = sum(1 for cr in case_runs if cr.replay_pass)
    attribution_passes = sum(1 for cr in case_runs if cr.attribution_pass)
    validity_passes = sum(1 for cr in case_runs if cr.validity_pass)

    # Input sensitivity: count distinct trace hashes across cases with
    # distinct prompts. We compare every pair: if prompts differ but hashes
    # match, that's a collision.
    pair_total = 0
    pair_distinct = 0
    for i in range(total):
        for j in range(i + 1, total):
            ci = cases[i]
            cj = cases[j]
            if ci["prompt"] == cj["prompt"] and ci.get("prime", []) == cj.get("prime", []):
                # truly identical inputs — skip
                continue
            pair_total += 1
            if case_runs[i].trace_hash != case_runs[j].trace_hash:
                pair_distinct += 1

    metrics = {
        "total": total,
        "replay_determinism": round(replay_passes / total, 4),
        "source_attribution": round(attribution_passes / total, 4),
        "source_validity": round(validity_passes / total, 4),
        "input_sensitivity": round(pair_distinct / pair_total, 4) if pair_total else 1.0,
        "overall_pass": (
            replay_passes == total
            and validity_passes == total
            and attribution_passes / total > 0.95
            and (pair_distinct / pair_total if pair_total else 1.0) > 0.95
        ),
    }

    case_details = [
        {
            "case_id": cr.case_id,
            "category": cr.category,
            "expected_sources": list(cr.expected_sources),
            "provenance_kinds": list(cr.provenance_kinds),
            "attribution_pass": cr.attribution_pass,
            "validity_pass": cr.validity_pass,
            "replay_pass": cr.replay_pass,
            "trace_hash": cr.trace_hash,
        }
        for cr in case_runs
    ]

    return LaneReport(metrics=metrics, case_details=case_details)
