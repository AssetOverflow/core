"""ADR-0098 adapter for ``core demo learning-loop`` (ADR-0056)."""

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
class LearningLoopDemo:
    """Adapter for ADR-0056 reviewed-teaching learning loop."""

    demo_id: str = "learning-loop"
    claim_contract_version: int = CLAIM_CONTRACT_VERSION

    def run(self, *, output_dir: Path, seed: int | None = None) -> DemoResult:
        _ = safe_pack_id(self.demo_id)
        if seed is not None:
            raise DemoContractError(
                f"{self.demo_id!r} is fully deterministic and does not accept a seed"
            )
        from evals.learning_loop.run_demo import run_demo

        raw = run_demo(emit_json=True)
        return _result_from_raw(raw, output_dir=output_dir, demo_id=self.demo_id)


_LEARNING_LOOP_VOLATILE_KEYS: frozenset[str] = frozenset({"transient_corpus"})


def _strip_volatile_paths(node: Any) -> Any:
    """Drop absolute-path fields that vary per-run from the learning-loop raw.

    ADR-0099 byte-equality requires that the adapter's serialized JSON
    not include temp-directory absolute paths. The semantic content of
    the demo (chains accepted, claims supported) is unchanged.
    """
    if isinstance(node, dict):
        return {
            k: _strip_volatile_paths(v)
            for k, v in node.items()
            if k not in _LEARNING_LOOP_VOLATILE_KEYS
        }
    if isinstance(node, list):
        return [_strip_volatile_paths(v) for v in node]
    return node


def _result_from_raw(
    raw: dict[str, Any], *, output_dir: Path, demo_id: str
) -> DemoResult:
    """Extract claims from the learning-loop result dict."""
    top_level_supported = bool(raw.get("all_claims_supported", False))
    claims: list[Claim] = []
    # Per-scene claims: walk leaf booleans whose key ends in "_supported".
    def visit(prefix: str, node: Any) -> None:
        if isinstance(node, dict):
            for key in sorted(node.keys()):
                visit(f"{prefix}.{key}" if prefix else key, node[key])
        elif isinstance(node, bool) and prefix.endswith("_supported"):
            claims.append(
                Claim(
                    claim_id=prefix.replace(".", "__"),
                    statement=prefix.replace("_", " ").replace(".", ": "),
                    supported=node,
                    evidence_locator=prefix,
                )
            )

    visit("", raw)
    if not claims:
        claims.append(
            Claim(
                claim_id="learning_loop_all_claims_supported",
                statement="learning-loop: all claims supported",
                supported=top_level_supported,
                evidence_locator="all_claims_supported",
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{demo_id}.json"
    payload = {
        "demo_id": demo_id,
        "claim_contract_version": CLAIM_CONTRACT_VERSION,
        "raw": _strip_volatile_paths(raw),
        "claims": [c.as_dict() for c in claims],
    }
    payload_bytes = canonical_json(payload)
    json_path.write_bytes(payload_bytes)

    sha = hashlib.sha256(payload_bytes).hexdigest()
    evidence = {c.claim_id: f"sha256:{sha[:16]}" for c in claims}
    trace_features = {
        "all_claims_supported": "true" if top_level_supported else "false",
        "report_sha256": sha,
    }

    return DemoResult(
        demo_id=demo_id,
        claim_contract_version=CLAIM_CONTRACT_VERSION,
        claims=tuple(claims),
        evidence=evidence,
        all_claims_supported=top_level_supported and all(c.supported for c in claims),
        json_path=json_path,
        trace_features=trace_features,
    )
