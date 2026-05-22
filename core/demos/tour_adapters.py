"""ADR-0098 adapters for the register / anchor-lens / orthogonality tours.

These three tour demos share a canonical shape: each returns a dict
with a top-level ``all_claims_supported`` plus per-scene
sub-dictionaries whose ``*_supported`` keys carry per-claim verdicts.
The adapters below translate that shape into a typed
:class:`DemoResult` without changing demo behavior.

The audit-tour adapter is separate (``audit_tour_adapter.py``) because
its scene layout predates the canonical ``*_supported`` convention.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from core._safe_display import safe_pack_id
from core.demos.contract import (
    CLAIM_CONTRACT_VERSION,
    Claim,
    DemoContractError,
    DemoResult,
    canonical_json,
)


def _extract_claims(
    raw: dict[str, Any], *, fallback_id: str
) -> tuple[Claim, ...]:
    """Walk ``raw`` for boolean ``*_supported`` keys and emit claims.

    The register / anchor-lens / orthogonality tours encode each
    falsifiable claim as a boolean at the leaf of their nested scene
    dicts. We collect them in a stable sorted order so the resulting
    claim list is deterministic.
    """
    claims: list[Claim] = []

    def visit(prefix: str, node: Any) -> None:
        if isinstance(node, Mapping):
            for key in sorted(node.keys()):
                visit(f"{prefix}.{key}" if prefix else key, node[key])
        elif isinstance(node, bool) and prefix.endswith("_supported"):
            claim_id = prefix.replace(".", "__")
            statement = prefix.replace("_", " ").replace(".", ": ")
            claims.append(
                Claim(
                    claim_id=claim_id,
                    statement=statement,
                    supported=node,
                    evidence_locator=prefix,
                )
            )

    visit("", raw)
    if not claims:
        # Fall back to the top-level ``all_claims_supported`` verdict so
        # tours that omit per-scene ``*_supported`` keys still surface
        # at least one claim.
        top = raw.get("all_claims_supported")
        if isinstance(top, bool):
            claims.append(
                Claim(
                    claim_id=f"{fallback_id}_all_claims_supported",
                    statement=f"{fallback_id}: all claims supported",
                    supported=top,
                    evidence_locator="all_claims_supported",
                )
            )
    return tuple(claims)


def _result_from_raw(
    raw: dict[str, Any], *, demo_id: str, output_dir: Path
) -> DemoResult:
    claims = _extract_claims(raw, fallback_id=demo_id)
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

    sha = hashlib.sha256(payload_bytes).hexdigest()
    evidence = {c.claim_id: f"sha256:{sha[:16]}" for c in claims}
    trace_features = {
        "all_claims_supported": (
            "true" if bool(raw.get("all_claims_supported", False)) else "false"
        ),
        "report_sha256": sha,
    }

    return DemoResult(
        demo_id=demo_id,
        claim_contract_version=CLAIM_CONTRACT_VERSION,
        claims=claims,
        evidence=evidence,
        all_claims_supported=bool(raw.get("all_claims_supported", False))
        and all(c.supported for c in claims),
        json_path=json_path,
        trace_features=trace_features,
    )


def _build_adapter(
    *, demo_id: str, runner: Callable[..., dict[str, Any]]
) -> Callable[..., DemoResult]:
    def _run(*, output_dir: Path, seed: int | None = None) -> DemoResult:
        _ = safe_pack_id(demo_id)
        if seed is not None:
            raise DemoContractError(
                f"{demo_id!r} is fully deterministic and does not accept a seed"
            )
        raw = runner(emit_json=True)
        return _result_from_raw(raw, demo_id=demo_id, output_dir=output_dir)

    return _run


@dataclass(frozen=True, slots=True)
class RegisterTourDemo:
    """Adapter for ADR-0072 register tour."""

    demo_id: str = "register-tour"
    claim_contract_version: int = CLAIM_CONTRACT_VERSION

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult:
        from evals.register_tour.run_tour import run_tour

        return _build_adapter(demo_id=self.demo_id, runner=run_tour)(
            output_dir=output_dir, seed=seed
        )


@dataclass(frozen=True, slots=True)
class AnchorLensTourDemo:
    """Adapter for ADR-0073d anchor-lens tour."""

    demo_id: str = "anchor-lens-tour"
    claim_contract_version: int = CLAIM_CONTRACT_VERSION

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult:
        from evals.anchor_lens_tour.run_tour import run_tour

        return _build_adapter(demo_id=self.demo_id, runner=run_tour)(
            output_dir=output_dir, seed=seed
        )


@dataclass(frozen=True, slots=True)
class OrthogonalityTourDemo:
    """Adapter for ADR-0074 orthogonality tour."""

    demo_id: str = "orthogonality-tour"
    claim_contract_version: int = CLAIM_CONTRACT_VERSION

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult:
        from evals.orthogonality_tour.run_tour import run_tour

        return _build_adapter(demo_id=self.demo_id, runner=run_tour)(
            output_dir=output_dir, seed=seed
        )
