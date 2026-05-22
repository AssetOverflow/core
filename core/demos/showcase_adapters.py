"""Showcase-only :class:`DemoCommand` adapters (ADR-0099).

Two thin adapters dedicated to the public showcase:

- :class:`FabricationControlPublicDemo` re-runs the ADR-0096 public
  split and packages the metrics as a :class:`DemoResult`. Used by
  the showcase scene 2 (honest unknown).

- :class:`MultiHopTraceDemo` runs one transitive prompt against the
  cognition pack with ``transitive_surface=True`` /
  ``composed_surface=True`` and captures the operator trace plus the
  grounded surface. Used by the showcase scene 4 (multi-hop with
  trace).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from core._safe_display import safe_pack_id
from core.demos.contract import (
    CLAIM_CONTRACT_VERSION,
    Claim,
    DemoContractError,
    DemoResult,
    canonical_json,
)


@dataclass(frozen=True, slots=True)
class FabricationControlPublicDemo:
    """ADR-0098 adapter that runs the ADR-0096 public split.

    Produces three claims: refusal_recall_met, fabrication_rate_met,
    trace_evidence_present_met. The adapter's :class:`DemoResult`
    surfaces the pinned-threshold verdicts so the showcase can compose
    them as a single "honest unknown" scene without re-implementing
    the metrics logic.
    """

    demo_id: str = "fabrication-control-public"
    claim_contract_version: int = CLAIM_CONTRACT_VERSION

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult:
        _ = safe_pack_id(self.demo_id)
        if seed is not None:
            raise DemoContractError(
                f"{self.demo_id!r} does not accept a seed"
            )
        # Local import — keeps the lane runner off module-load.
        from evals.fabrication_control.runner import _run_split

        lane_dir = Path(__file__).resolve().parent.parent.parent / "evals" / "fabrication_control"
        split_report = _run_split(lane_dir, "public")
        return _result_from_split(
            split_report, output_dir=output_dir, demo_id=self.demo_id
        )


def _result_from_split(
    split_report: dict[str, Any], *, output_dir: Path, demo_id: str
) -> DemoResult:
    metrics = split_report["metrics"]
    thresholds = split_report["thresholds"]
    threshold_eval = split_report["threshold_evaluation"]

    claims = (
        Claim(
            claim_id="refusal_recall_meets_threshold",
            statement=(
                f"refusal_recall ≥ {thresholds['refusal_recall_min']} on the "
                "fabrication-control public split."
            ),
            supported=metrics["refusal_recall"] >= thresholds["refusal_recall_min"],
            evidence_locator=f"metrics.refusal_recall={metrics['refusal_recall']}",
        ),
        Claim(
            claim_id="fabrication_rate_below_threshold",
            statement=(
                f"fabrication_rate ≤ {thresholds['fabrication_rate_max']} on "
                "the fabrication-control public split."
            ),
            supported=metrics["fabrication_rate"]
            <= thresholds["fabrication_rate_max"],
            evidence_locator=f"metrics.fabrication_rate={metrics['fabrication_rate']}",
        ),
        Claim(
            claim_id="trace_evidence_present",
            statement="Every case exposes a grounding_source trace.",
            supported=metrics["trace_evidence_present"]
            >= thresholds["trace_evidence_present_min"],
            evidence_locator=(
                f"metrics.trace_evidence_present={metrics['trace_evidence_present']}"
            ),
        ),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{demo_id}.json"
    payload = {
        "demo_id": demo_id,
        "claim_contract_version": CLAIM_CONTRACT_VERSION,
        "split_report": split_report,
        "claims": [c.as_dict() for c in claims],
    }
    payload_bytes = canonical_json(payload)
    json_path.write_bytes(payload_bytes)

    sha = hashlib.sha256(payload_bytes).hexdigest()
    evidence = {c.claim_id: f"sha256:{sha[:16]}" for c in claims}
    trace_features = {
        "refusal_recall": str(metrics["refusal_recall"]),
        "fabrication_rate": str(metrics["fabrication_rate"]),
        "cases_n": str(metrics["n"]),
        "threshold_evaluation_passed": (
            "true" if threshold_eval["passed"] else "false"
        ),
    }

    return DemoResult(
        demo_id=demo_id,
        claim_contract_version=CLAIM_CONTRACT_VERSION,
        claims=claims,
        evidence=evidence,
        all_claims_supported=all(c.supported for c in claims),
        json_path=json_path,
        trace_features=trace_features,
    )


@dataclass(frozen=True, slots=True)
class MultiHopTraceDemo:
    """ADR-0099 scene 4: multi-hop transitive surface with operator trace.

    Runs one transitive prompt against the cognition pack with
    ``transitive_surface=True`` and ``composed_surface=True`` so the
    runtime emits its chain-of-chains walk. Captures three claims:

    1. The runtime produced a grounded answer (``grounding_source =
       teaching``), not a refusal.
    2. The surface names ≥ 3 atoms (multi-hop traversal, depth ≥ 2).
    3. The result exposes a non-empty trace (operator/walk evidence).
    """

    demo_id: str = "multi-hop-trace"
    claim_contract_version: int = CLAIM_CONTRACT_VERSION
    prompt: str = "Does light reveal truth?"

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult:
        _ = safe_pack_id(self.demo_id)
        if seed is not None:
            raise DemoContractError(
                f"{self.demo_id!r} does not accept a seed"
            )
        # Local imports keep the heavy runtime stack off module load.
        from chat.runtime import ChatRuntime
        from core.config import RuntimeConfig

        config = replace(
            RuntimeConfig(),
            transitive_surface=True,
            composed_surface=True,
        )
        runtime = ChatRuntime(config=config)
        response = runtime.chat(self.prompt)

        surface = response.surface or ""
        # Count atom-tags in the surface (cognition.x style). These are
        # the multi-hop traversal waypoints — depth ≥ 2 requires ≥ 3
        # distinct atoms (subject + 2 hops).
        import re

        atoms = sorted(set(re.findall(r"\b[a-z_]+\.[a-z_]+\b", surface)))
        walk_surface = response.walk_surface or ""

        claims = (
            Claim(
                claim_id="multi_hop_grounded_answer",
                statement=(
                    f"Prompt {self.prompt!r} produces a teaching-grounded "
                    "answer rather than a refusal."
                ),
                supported=response.grounding_source == "teaching",
                evidence_locator=f"grounding_source={response.grounding_source}",
            ),
            Claim(
                claim_id="multi_hop_depth_two_or_more",
                statement=(
                    "Surface names ≥ 3 distinct atoms (depth-2 transitive walk)."
                ),
                supported=len(atoms) >= 3,
                evidence_locator=f"atoms_in_surface={len(atoms)}",
            ),
            Claim(
                claim_id="multi_hop_walk_evidence_present",
                statement="Result exposes non-empty walk evidence.",
                supported=bool(walk_surface.strip()),
                evidence_locator="walk_surface non-empty",
            ),
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{self.demo_id}.json"
        payload = {
            "demo_id": self.demo_id,
            "claim_contract_version": CLAIM_CONTRACT_VERSION,
            "prompt": self.prompt,
            "grounding_source": response.grounding_source,
            "surface": surface,
            "walk_surface": walk_surface,
            "atoms": atoms,
            "claims": [c.as_dict() for c in claims],
        }
        payload_bytes = canonical_json(payload)
        json_path.write_bytes(payload_bytes)

        sha = hashlib.sha256(payload_bytes).hexdigest()
        evidence = {c.claim_id: f"sha256:{sha[:16]}" for c in claims}
        trace_features = {
            "grounding_source": response.grounding_source,
            "atoms_count": str(len(atoms)),
            "report_sha256": sha,
        }
        return DemoResult(
            demo_id=self.demo_id,
            claim_contract_version=CLAIM_CONTRACT_VERSION,
            claims=claims,
            evidence=evidence,
            all_claims_supported=all(c.supported for c in claims),
            json_path=json_path,
            trace_features=trace_features,
        )
