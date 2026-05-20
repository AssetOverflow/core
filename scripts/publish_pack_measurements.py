"""Publish combined Phase-2 pack-measurement report (ADR-0043).

Runs both pack-driven runners (identity-divergence + refusal-calibration)
and writes a unified report to
`evals/results/phase2_pack_measurements.json` plus a per-runner copy
under each lane's own `results/packs_v1/` directory.

Usage:
    PYTHONPATH=. python3 scripts/publish_pack_measurements.py [--json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.identity_divergence.pack_runner import run_pack_divergence_eval
from evals.refusal_calibration.pack_runner import run_pack_refusal_eval


def build_combined_report() -> dict[str, Any]:
    identity = run_pack_divergence_eval()
    refusal = run_pack_refusal_eval()
    claims = {
        "identity_load_bearing": identity["load_bearing"],
        "grounding_gate_pack_invariant": refusal["pack_invariant_gate"],
        "no_fabrication_under_any_pack": all(
            p["fabrication_rate"] == 0.0 for p in refusal["packs"]
        ),
    }
    return {
        "schema_version": 1,
        "identity_divergence": identity,
        "refusal_calibration": refusal,
        "claims_supported": claims,
        # ``all_claims_supported`` is the canonical cross-demo success
        # field — AND of every entry in the nested claims_supported dict.
        # Operator tooling can consume this without knowing the claim list.
        "all_claims_supported": all(claims.values()),
    }


def write_report(report: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return out_path


def _print_human(report: dict[str, Any]) -> None:
    identity = report["identity_divergence"]
    refusal = report["refusal_calibration"]
    claims = report["claims_supported"]

    print("Phase-2 pack measurements (ADR-0043)")
    print("=" * 72)
    print(
        f"identity-divergence: {identity['case_count']} cases × "
        f"{len(identity['alignment_bands'])} alignment bands"
    )
    for entry in identity["packs"]:
        print(
            f"  {entry['pack_id']:<24}  bare={entry['bare_rate']:.2f}  "
            f"hedge={entry['hedge_rate']:.2f}  qualifier={entry['qualifier_rate']:.2f}"
        )
    print()
    for pair in identity["pairwise_divergence"]:
        print(
            f"  {pair['pack_a']} ⇆ {pair['pack_b']:<22}  "
            f"distinct_rate={pair['distinct_rate']:.2f}"
        )
    print()
    print(
        f"refusal-calibration: {refusal['case_count']} cases "
        f"(out_of_grounding={refusal['out_of_grounding_count']})"
    )
    for entry in refusal["packs"]:
        print(
            f"  {entry['pack_id']:<24}  refusal_rate={entry['refusal_rate']:.2f}  "
            f"fabrication_rate={entry['fabrication_rate']:.2f}"
        )
    print()
    print("Claims:")
    for k, v in claims.items():
        print(f"  {k:<40}  {v}")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit only JSON to stdout")
    args = parser.parse_args()

    report = build_combined_report()
    out_path = Path("evals/results/phase2_pack_measurements.json")
    write_report(report, out_path)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
        print(f"wrote → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
