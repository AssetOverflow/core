"""ADR-0098 adapter for ``core demo audit-tour``.

Wraps :func:`evals.audit_tour.run_tour.run_tour` and translates its
result dict into a typed :class:`DemoResult`. No demo behavior
changes; the adapter is purely structural.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
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
class AuditTourDemo:
    """Adapter for ADR-0042 audit tour."""

    demo_id: str = "audit-tour"
    claim_contract_version: int = CLAIM_CONTRACT_VERSION

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult:
        # Path sanitization via the discipline established in ADR-0051.
        _ = safe_pack_id(self.demo_id)
        # ``seed`` is part of the protocol so the showcase can request
        # deterministic variation across composed demos; audit-tour is
        # already fully deterministic and accepts only ``None``.
        if seed is not None:
            raise DemoContractError(
                f"{self.demo_id!r} is fully deterministic and does not accept a seed"
            )

        # Local import keeps audit-tour's heavy runtime cost off
        # module-load and confines the import graph.
        from evals.audit_tour.run_tour import run_tour

        raw = run_tour(emit_json=True)
        return _result_from_raw(raw, output_dir=output_dir, demo_id=self.demo_id)


def _result_from_raw(
    raw: dict[str, Any], *, output_dir: Path, demo_id: str
) -> DemoResult:
    s1 = raw["scene_1_identity_geometric"]
    s2 = raw["scene_2_safety_typed_refusal"]
    s3 = raw["scene_3_ethics_hedge_opt_in"]
    s4 = raw["scene_4_deterministic_replay"]

    claims = (
        Claim(
            claim_id="s1_identity_pack_swaps_visible",
            statement="Three identity packs produce ≥ 1 distinct hedge phrase variant.",
            supported=int(s1["distinct_hedge_phrases"]) >= 1,
            evidence_locator=(
                f"scene_1.distinct_hedge_phrases={s1['distinct_hedge_phrases']}"
            ),
        ),
        Claim(
            claim_id="s2_safety_typed_refusal",
            statement="A runtime-checkable safety violation produces a typed refusal.",
            supported=bool(s2["refusal_emitted"]),
            evidence_locator="scene_2.refusal_emitted",
        ),
        Claim(
            claim_id="s3_ethics_opt_in_deployment_fires",
            statement="Deployment ethics pack fires the opt-in remediation.",
            supported=bool(s3["deployment_fires"]),
            evidence_locator="scene_3.deployment_fires",
        ),
        Claim(
            claim_id="s3_ethics_default_silent",
            statement="Default ethics pack remains silent on the same input.",
            supported=not bool(s3["default_fires"]),
            evidence_locator="scene_3.default_fires (must be False)",
        ),
        Claim(
            claim_id="s4_replay_byte_identical",
            statement="Two fresh runtimes emit byte-identical JSONL audit lines.",
            supported=bool(s4["byte_identical"]),
            evidence_locator="scene_4.byte_identical",
        ),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{demo_id}.json"
    payload = {
        "demo_id": demo_id,
        "claim_contract_version": CLAIM_CONTRACT_VERSION,
        "raw": raw,
        "claims": [c.as_dict() for c in claims],
    }
    payload_bytes = canonical_json(payload)
    json_path.write_bytes(payload_bytes)

    evidence = {
        c.claim_id: f"sha256:{hashlib.sha256(payload_bytes).hexdigest()[:16]}"
        for c in claims
    }
    trace_features = {
        "distinct_hedge_phrases": str(s1["distinct_hedge_phrases"]),
        "byte_identical_replay": "true" if s4["byte_identical"] else "false",
        "report_sha256": hashlib.sha256(payload_bytes).hexdigest(),
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
