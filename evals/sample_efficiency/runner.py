"""sample-efficiency eval lane runner — Phase 4 (quantitative curve).

For each concept:
  1. Sweep k = 0..len(curriculum). For each k, run a fresh pipeline,
     teach the first k corrections, then probe.
  2. Record cumulative token-hit count, vault hits, trace hash.
  3. Repeat once for replay-determinism check.

Output is a per-concept curve plus aggregate efficiency statistics.

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


def _count_hits(text: str, expected: list[str]) -> int:
    if not text:
        return 0
    toks = _tokens(text)
    return sum(1 for tok in expected if tok.lower() in toks)


def _run_snapshot(
    curriculum: list[str],
    k: int,
    probe: str,
    seed: str,
) -> dict[str, Any]:
    """Teach first k corrections on a fresh pipeline, then probe.

    The seed prompt (a question about the concept, e.g. "What is wisdom?")
    runs first so that subsequent corrections have a prior_surface to bind
    to — the teaching loop drops corrections that arrive on turn 0.
    """
    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)
    try:
        pipeline.run(seed, max_tokens=8)
    except ValueError:
        pass
    for premise in curriculum[:k]:
        try:
            pipeline.run(premise, max_tokens=8)
        except ValueError:
            continue
    try:
        r = pipeline.run(probe, max_tokens=8)
    except ValueError:
        return {
            "surface_blob": "",
            "vault_hits": 0,
            "trace_hash": "",
        }
    blob = " ".join([r.surface or "", r.articulation_surface or "", r.walk_surface or ""])
    return {
        "surface_blob": blob,
        "vault_hits": int(r.vault_hits),
        "trace_hash": r.trace_hash,
    }


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    concept: str = case["concept"]
    curriculum: list[str] = list(case.get("curriculum", []))
    probe: str = case["probe"]
    expected_tokens: list[str] = list(case.get("expected_tokens", []))
    seed: str = case.get("seed") or probe

    n = len(curriculum)
    n_expected = len(expected_tokens)
    snapshots: list[dict[str, Any]] = []
    replay_matches = 0
    replay_total = 0

    for k in range(n + 1):
        first = _run_snapshot(curriculum, k, probe, seed)
        second = _run_snapshot(curriculum, k, probe, seed)
        replay_total += 1
        if first["trace_hash"] and first["trace_hash"] == second["trace_hash"]:
            replay_matches += 1
        hits = _count_hits(first["surface_blob"], expected_tokens)
        snapshots.append({
            "k": k,
            "cumulative_token_hit_count": hits,
            "fraction": (hits / n_expected) if n_expected else 0.0,
            "vault_hits": first["vault_hits"],
            "trace_hash": first["trace_hash"],
            "trace_hash_replay": second["trace_hash"],
            "replay_match": first["trace_hash"] == second["trace_hash"],
        })

    # Curve summary statistics.
    corrections_to_first_hit: int | None = None
    corrections_to_saturation: int | None = None
    for snap in snapshots:
        if corrections_to_first_hit is None and snap["cumulative_token_hit_count"] >= 1:
            corrections_to_first_hit = snap["k"]
        if (
            corrections_to_saturation is None
            and n_expected > 0
            and snap["cumulative_token_hit_count"] >= n_expected
        ):
            corrections_to_saturation = snap["k"]

    final_hits = snapshots[-1]["cumulative_token_hit_count"] if snapshots else 0
    saturation_score = (final_hits / n_expected) if n_expected else 0.0
    replay_rate = (replay_matches / replay_total) if replay_total else 0.0

    return {
        "concept": concept,
        "curriculum_length": n,
        "expected_token_count": n_expected,
        "snapshots": snapshots,
        "corrections_to_first_hit": corrections_to_first_hit,
        "corrections_to_saturation": corrections_to_saturation,
        "saturation_score": round(saturation_score, 4),
        "replay_determinism": round(replay_rate, 4),
        "passed": replay_rate >= 0.95,
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

    hit_concepts = [d for d in case_details if d["corrections_to_first_hit"] is not None]
    sat_concepts = [d for d in case_details if d["corrections_to_saturation"] is not None]

    def _mean(vals: list[int]) -> float | None:
        if not vals:
            return None
        return round(sum(vals) / len(vals), 4)

    mean_first_hit = _mean([d["corrections_to_first_hit"] for d in hit_concepts])
    mean_saturation = _mean([d["corrections_to_saturation"] for d in sat_concepts])
    saturation_rate = round(len(sat_concepts) / total, 4) if total else 0.0
    hit_rate = round(len(hit_concepts) / total, 4) if total else 0.0
    mean_saturation_score = (
        round(sum(d["saturation_score"] for d in case_details) / total, 4) if total else 0.0
    )
    replay_rate = (
        round(sum(d["replay_determinism"] for d in case_details) / total, 4) if total else 0.0
    )

    metrics: dict[str, Any] = {
        "mean_corrections_to_first_hit": mean_first_hit,
        "mean_corrections_to_saturation": mean_saturation,
        "first_hit_rate": hit_rate,
        "saturation_rate": saturation_rate,
        "mean_saturation_score": mean_saturation_score,
        "replay_determinism": replay_rate,
        "concept_count": total,
        # Phase 4 discipline: quantitative, not pass/fail beyond the structural
        # replay-determinism gate.  overall_pass is reported but is the gate
        # only on reproducibility, not on the curve itself.
        "overall_pass": replay_rate >= 0.95,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
