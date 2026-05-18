"""Pack-driven identity-divergence runner (Phase 2 of pack-layer chain).

Drives the *real* `SentenceAssembler` + `SurfaceContext` across the three
ratified identity packs (`default_general_v1`, `precision_first_v1`,
`generosity_first_v1`) over the existing dev + public/v1 cases at five
alignment bands.  No mocks.  No pack growth.

Publishes per-pack numbers (hedge rate, qualifier rate, bare rate) and
pairwise divergence rates so the ADR-0027/0028 claim "identity is
load-bearing" reads as a measurement, not an assertion.

Output: `evals/identity_divergence/results/packs_v1/measurements.json`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generate.articulation import ArticulationPlan
from generate.surface import SentenceAssembler, SurfaceContext
from packs.identity.loader import load_identity_manifold


PACK_IDS: tuple[str, ...] = (
    "default_general_v1",
    "precision_first_v1",
    "generosity_first_v1",
)

ALIGNMENT_BANDS: tuple[float, ...] = (0.20, 0.45, 0.60, 0.80, 0.95)

_ASSEMBLER = SentenceAssembler()


@dataclass(frozen=True, slots=True)
class PackMetrics:
    pack_id: str
    case_count: int
    surface_count: int
    bare_rate: float
    hedge_rate: float
    qualifier_rate: float


@dataclass(frozen=True, slots=True)
class DivergenceMatrix:
    pack_a: str
    pack_b: str
    distinct_rate: float


def _humanize(token: str) -> str:
    return token.replace("_", " ").strip()


def _plan_from_case(case: dict[str, Any]) -> ArticulationPlan:
    nodes = case["proposition_graph"]["nodes"]
    head = nodes[0]
    return ArticulationPlan(
        subject=_humanize(str(head.get("subject", "x"))),
        predicate=_humanize(str(head.get("predicate", "relates"))),
        object=_humanize(str(head.get("obj", "y"))),
        surface="",
        output_language="en",
        frame_id="default",
    )


def _ctx_from_pack(pack_id: str, alignment: float) -> SurfaceContext:
    manifold = load_identity_manifold(pack_id)
    prefs = manifold.surface_preferences
    return SurfaceContext(
        identity_alignment=alignment,
        hedge_threshold_strong=prefs.hedge_threshold_strong,
        hedge_threshold_soft=prefs.hedge_threshold_soft,
        preferred_hedge_strong=prefs.preferred_hedge_strong,
        preferred_hedge_soft=prefs.preferred_hedge_soft,
        claim_strength=prefs.claim_strength,
        qualified_band_high=prefs.qualified_band_high,
        preferred_qualifier=prefs.preferred_qualifier,
    )


def _classify(surface: str, ctx: SurfaceContext) -> str:
    """Map a surface to {bare, hedge_strong, hedge_soft, qualifier}.

    Classification is exact (prefix match against the pack's own
    configured hedge/qualifier phrases) — no fuzzy heuristics, no NLP.
    """
    strong = ctx.preferred_hedge_strong
    soft = ctx.preferred_hedge_soft
    qual = ctx.preferred_qualifier
    if strong and surface.startswith(strong):
        return "hedge_strong"
    if soft and surface.startswith(soft):
        return "hedge_soft"
    if qual and surface.startswith(qual):
        return "qualifier"
    return "bare"


def _load_cases(eval_dir: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for split in ("dev/cases.jsonl", "public/v1/cases.jsonl"):
        path = eval_dir / split
        if not path.exists():
            continue
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    cases.append(json.loads(line))
    return cases


def _emit_surfaces(
    cases: list[dict[str, Any]],
) -> dict[str, dict[float, list[tuple[str, str, str]]]]:
    """Return surfaces keyed by pack_id → alignment → list of (case_id, surface, classification)."""
    out: dict[str, dict[float, list[tuple[str, str, str]]]] = {p: {} for p in PACK_IDS}
    for pack_id in PACK_IDS:
        for alignment in ALIGNMENT_BANDS:
            ctx = _ctx_from_pack(pack_id, alignment)
            band_rows: list[tuple[str, str, str]] = []
            for case in cases:
                plan = _plan_from_case(case)
                surface = _ASSEMBLER.assemble(plan, tokens=[], role="assert", context=ctx).surface
                band_rows.append((case["id"], surface, _classify(surface, ctx)))
            out[pack_id][alignment] = band_rows
    return out


def _pack_metrics(
    pack_id: str,
    bands: dict[float, list[tuple[str, str, str]]],
    case_count: int,
) -> PackMetrics:
    bare = hedge = qual = 0
    total = 0
    for rows in bands.values():
        for _cid, _surface, cls in rows:
            total += 1
            if cls == "bare":
                bare += 1
            elif cls in ("hedge_strong", "hedge_soft"):
                hedge += 1
            elif cls == "qualifier":
                qual += 1
    return PackMetrics(
        pack_id=pack_id,
        case_count=case_count,
        surface_count=total,
        bare_rate=round(bare / total, 4) if total else 0.0,
        hedge_rate=round(hedge / total, 4) if total else 0.0,
        qualifier_rate=round(qual / total, 4) if total else 0.0,
    )


def _divergence(
    pack_a: str,
    pack_b: str,
    surfaces: dict[str, dict[float, list[tuple[str, str, str]]]],
) -> DivergenceMatrix:
    distinct = 0
    total = 0
    for alignment in ALIGNMENT_BANDS:
        rows_a = surfaces[pack_a][alignment]
        rows_b = surfaces[pack_b][alignment]
        for (cid_a, surf_a, _), (cid_b, surf_b, _) in zip(rows_a, rows_b):
            assert cid_a == cid_b, "case order must match"
            total += 1
            if surf_a != surf_b:
                distinct += 1
    return DivergenceMatrix(
        pack_a=pack_a,
        pack_b=pack_b,
        distinct_rate=round(distinct / total, 4) if total else 0.0,
    )


def run_pack_divergence_eval(eval_dir: Path | None = None) -> dict[str, Any]:
    eval_dir = eval_dir or Path(__file__).parent
    cases = _load_cases(eval_dir)
    if not cases:
        raise FileNotFoundError(f"no cases found under {eval_dir}")
    surfaces = _emit_surfaces(cases)

    pack_metrics = [
        _pack_metrics(p, surfaces[p], len(cases)) for p in PACK_IDS
    ]
    pairs = [
        ("default_general_v1", "precision_first_v1"),
        ("default_general_v1", "generosity_first_v1"),
        ("precision_first_v1", "generosity_first_v1"),
    ]
    divergence = [_divergence(a, b, surfaces) for a, b in pairs]

    return {
        "schema_version": 1,
        "case_count": len(cases),
        "alignment_bands": list(ALIGNMENT_BANDS),
        "packs": [
            {
                "pack_id": m.pack_id,
                "case_count": m.case_count,
                "surface_count": m.surface_count,
                "bare_rate": m.bare_rate,
                "hedge_rate": m.hedge_rate,
                "qualifier_rate": m.qualifier_rate,
            }
            for m in pack_metrics
        ],
        "pairwise_divergence": [
            {"pack_a": d.pack_a, "pack_b": d.pack_b, "distinct_rate": d.distinct_rate}
            for d in divergence
        ],
        "load_bearing": all(d.distinct_rate > 0.0 for d in divergence),
    }


def _write_report(report: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "measurements.json"
    with out_path.open("w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return out_path


def main() -> int:
    eval_dir = Path(__file__).parent
    report = run_pack_divergence_eval(eval_dir)
    out_path = _write_report(report, eval_dir / "results" / "packs_v1")

    print(f"Pack-driven identity-divergence measurements ({report['case_count']} cases × {len(ALIGNMENT_BANDS)} alignment bands)")
    print("-" * 70)
    for entry in report["packs"]:
        print(
            f"  {entry['pack_id']:<24}  bare={entry['bare_rate']:.2f}  "
            f"hedge={entry['hedge_rate']:.2f}  qualifier={entry['qualifier_rate']:.2f}  "
            f"(n={entry['surface_count']})"
        )
    print("-" * 70)
    for pair in report["pairwise_divergence"]:
        print(
            f"  {pair['pack_a']} ⇆ {pair['pack_b']:<22}  distinct={pair['distinct_rate']:.2f}"
        )
    print("-" * 70)
    print(f"load_bearing={report['load_bearing']}  →  {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
