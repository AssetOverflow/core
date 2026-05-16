"""Field-state signature probe for adversarial-identity attacks vs legitimates.

Run this script when designing or revisiting the IdentityManifold's axis
directions for fix #3 (the geometric identity-override defense).  It runs
each adversarial-identity case through a fresh CognitiveTurnPipeline,
captures the per-turn field-state delta and the existing identity_score,
and reports per-coordinate and per-case discriminators between attacks
and legitimates.

Result as of 2026-05-16 (recorded in `evals/adversarial_identity/gaps.md`):
field-state geometry produced by today's ingest gate + vault grounding
does NOT carry a discriminating signal between identity-override attacks
and legitimate corrections.  Per-case distributions overlap heavily;
`identity_score.alignment` is 1.000 universally; mean-level coordinate
differences are statistical artefacts of averaging, not per-case signals.

This script is preserved as the calibration baseline: any future change
to the ingest gate, vocabulary grounding, or value-axis encoding should
re-run this and demonstrate a per-case separation before claiming fix #3
is load-bearing.

Usage:
    python3 evals/adversarial_identity/calibration/probe_field_signature.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline


_SEMANTIC_COORDS = (6, 7, 9, 10, 12, 14, 27)
_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class CaseSignature:
    case_id: str
    kind: str
    vault_hits: int
    identity_alignment: float
    delta_norm: float
    semantic_coord_energy_ratio: float
    surface_len: int


def _load_cases(jsonl: Path) -> list[dict]:
    return [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]


def _signature(case: dict) -> CaseSignature | None:
    runtime = ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)
    prior = case.get("prior", "")
    if prior:
        try:
            pipeline.run(prior, max_tokens=8)
        except ValueError:
            return None
    try:
        result = pipeline.run(case["attack"], max_tokens=8)
    except ValueError:
        return None
    if result.field_state_before is None or result.field_state_after is None:
        return None

    f_before = result.field_state_before.F.astype(np.float64)
    f_after = result.field_state_after.F.astype(np.float64)
    delta = f_after - f_before

    semantic_energy = float((delta[list(_SEMANTIC_COORDS)] ** 2).sum())
    total_energy = float((delta ** 2).sum()) + 1e-12
    return CaseSignature(
        case_id=str(case.get("id", "")),
        kind=str(case.get("kind", "")),
        vault_hits=int(result.vault_hits),
        identity_alignment=(
            float(result.identity_score.alignment) if result.identity_score else 1.0
        ),
        delta_norm=float(np.linalg.norm(delta)),
        semantic_coord_energy_ratio=semantic_energy / total_energy,
        surface_len=len(result.surface or ""),
    )


def _summarize(label: str, signatures: list[CaseSignature]) -> None:
    if not signatures:
        print(f"{label}: no signatures")
        return
    norms = np.array([s.delta_norm for s in signatures])
    ratios = np.array([s.semantic_coord_energy_ratio for s in signatures])
    aligns = np.array([s.identity_alignment for s in signatures])
    hits = np.array([s.vault_hits for s in signatures])
    print(
        f"{label:>30s} n={len(signatures):3d}  "
        f"delta_norm: μ={norms.mean():.3f} σ={norms.std():.3f} "
        f"[{norms.min():.3f},{norms.max():.3f}]  "
        f"sem_ratio: μ={ratios.mean():.3f}  "
        f"align: μ={aligns.mean():.3f} min={aligns.min():.3f}  "
        f"vault_hits: μ={hits.mean():.2f}"
    )


def main() -> None:
    splits = [
        ("public/v3", "evals/adversarial_identity/public/v3/cases.jsonl"),
        ("holdouts/v3", "evals/adversarial_identity/holdouts/v3/cases.jsonl"),
        ("public/v5", "evals/adversarial_identity/public/v5/cases.jsonl"),
        ("holdouts/v5", "evals/adversarial_identity/holdouts/v5/cases.jsonl"),
    ]
    print("=" * 110)
    print("FIELD-STATE SIGNATURE PROBE — adversarial-identity attack vs legitimate")
    print("=" * 110)
    for split, path in splits:
        cases = _load_cases(_REPO_ROOT / path)
        attacks = [
            sig
            for c in cases
            if c["kind"] == "attack"
            for sig in [_signature(c)]
            if sig is not None
        ]
        legits = [
            sig
            for c in cases
            if c["kind"] == "legitimate"
            for sig in [_signature(c)]
            if sig is not None
        ]
        _summarize(f"{split} attacks", attacks)
        _summarize(f"{split} legitimates", legits)
    print("=" * 110)
    print(
        "Finding: per-case distributions overlap heavily; identity_score.alignment is\n"
        "1.000 universally across all kinds; no scalar derived from field-state geometry\n"
        "separates attack from legitimate at the per-case level.  See gaps.md."
    )


if __name__ == "__main__":
    main()
