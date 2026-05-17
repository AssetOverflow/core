"""Generate Phase 5.4–5.7 domain fluency OOD lanes.

Each lane reuses the english_fluency_ood case-builder over a
domain-specific vocabulary set, demonstrating that fluency is
mechanistic in the realizer (templates over typed graph nodes), not
lexical (pack-bound).  Same 13 constructions, same scoring rubric,
new vocabulary.

Lanes produced:
  5.4 elementary_mathematics_ood   public: arithmetic / set / geometry
                                   holdout: probability
  5.5 foundational_physics_ood     public: mechanics / electricity / thermo
                                   holdout: optics
  5.6 foundational_biology_ood     public: cell / organism / ecosystem
                                   holdout: genetics
  5.7 classical_literature_ood     public: epic / tragedy / lyric
                                   holdout: comedy

Predicates default to regular verbs so morphology gaps do not
confound the structural fluency claim.

Run:
    .venv/bin/python scripts/generate_phase5_domain_lanes.py
"""

from __future__ import annotations

import json
from pathlib import Path

# Import the proven case-builder + construction list from the 5.1 generator.
from scripts.generate_english_fluency_ood import CONSTRUCTIONS, build_case


_Triple = tuple[str, str, str]
_Domain = dict[str, list[_Triple]]
_LaneSpec = dict[str, str | _Domain]
LANES: dict[str, _LaneSpec] = {
    "elementary_mathematics_ood": {
        "prefix_pub": "EMO-PUB",
        "prefix_hold": "EMO-HOLD",
        "public": {
            "arithmetic": [
                ("addition", "yields", "sum"),
                ("product", "equals", "factor"),
                ("difference", "shows", "remainder"),
            ],
            "set": [
                ("union", "joins", "element"),
                ("subset", "fits", "superset"),
                ("intersection", "shares", "member"),
            ],
            "geometry": [
                ("triangle", "encloses", "angle"),
                ("circle", "bounds", "region"),
                ("polygon", "contains", "vertex"),
            ],
        },
        "holdout": {
            "probability": [
                ("event", "carries", "weight"),
                ("outcome", "favors", "sample"),
                ("distribution", "covers", "range"),
            ],
        },
    },
    "foundational_physics_ood": {
        "prefix_pub": "FPO-PUB",
        "prefix_hold": "FPO-HOLD",
        "public": {
            "mechanics": [
                ("force", "moves", "object"),
                ("torque", "rotates", "wheel"),
                ("impulse", "changes", "momentum"),
            ],
            "electricity": [
                ("current", "powers", "circuit"),
                ("voltage", "drives", "charge"),
                ("resistor", "limits", "flow"),
            ],
            "thermodynamics": [
                ("heat", "raises", "temperature"),
                ("piston", "compresses", "gas"),
                ("entropy", "tracks", "disorder"),
            ],
        },
        "holdout": {
            "optics": [
                ("lens", "focuses", "ray"),
                ("mirror", "reflects", "beam"),
                ("prism", "separates", "color"),
            ],
        },
    },
    "foundational_biology_ood": {
        "prefix_pub": "FBO-PUB",
        "prefix_hold": "FBO-HOLD",
        "public": {
            "cell": [
                ("ribosome", "assembles", "protein"),
                ("membrane", "guards", "interior"),
                ("mitochondrion", "produces", "energy"),
            ],
            "organism": [
                ("plant", "absorbs", "sunlight"),
                ("animal", "consumes", "food"),
                ("fungus", "decomposes", "matter"),
            ],
            "ecosystem": [
                ("predator", "hunts", "prey"),
                ("forest", "shelters", "creature"),
                ("river", "feeds", "wetland"),
            ],
        },
        "holdout": {
            "genetics": [
                ("gene", "encodes", "trait"),
                ("allele", "varies", "expression"),
                ("chromosome", "carries", "marker"),
            ],
        },
    },
    "classical_literature_ood": {
        "prefix_pub": "CLO-PUB",
        "prefix_hold": "CLO-HOLD",
        "public": {
            "epic": [
                ("hero", "leaves", "homeland"),
                ("warrior", "seeks", "glory"),
                ("voyager", "crosses", "ocean"),
            ],
            "tragedy": [
                ("king", "loses", "kingdom"),
                ("daughter", "warns", "father"),
                ("oracle", "reveals", "doom"),
            ],
            "lyric": [
                ("poet", "praises", "season"),
                ("singer", "mourns", "absence"),
                ("muse", "inspires", "verse"),
            ],
        },
        "holdout": {
            "comedy": [
                ("servant", "tricks", "master"),
                ("twin", "confuses", "spouse"),
                ("rogue", "outwits", "judge"),
            ],
        },
    },
}


def emit_split(
    domains: dict[str, list[tuple[str, str, str]]],
    prefix: str,
    out_path: Path,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for domain, triples in domains.items():
        for code, name in CONSTRUCTIONS:
            for i, triple in enumerate(triples):
                aux = triples[(i + 1) % len(triples)]
                cid = f"{prefix}_{domain}_{code}_{i+1:02d}"
                case = build_case(cid, code, name, triple, aux=aux)
                lines.append(json.dumps(case))
    out_path.write_text("\n".join(lines) + "\n")
    return len(lines)


def emit_dev(domains: dict[str, list[tuple[str, str, str]]], prefix: str, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # One case per construction from the first domain — the same shape
    # english_fluency_ood uses for its dev split.
    first_domain = next(iter(domains))
    triples = domains[first_domain]
    lines: list[str] = []
    for code, name in CONSTRUCTIONS:
        case = build_case(f"{prefix}-DEV_{code}", code, name, triples[0], aux=triples[1])
        lines.append(json.dumps(case))
    out_path.write_text("\n".join(lines) + "\n")
    return len(lines)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    for lane, spec in LANES.items():
        lane_dir = root / "evals" / lane
        pub = spec["public"]; assert isinstance(pub, dict)
        hold = spec["holdout"]; assert isinstance(hold, dict)
        prefix_pub = spec["prefix_pub"]; assert isinstance(prefix_pub, str)
        prefix_hold = spec["prefix_hold"]; assert isinstance(prefix_hold, str)
        n_pub = emit_split(pub, prefix_pub, lane_dir / "public" / "v1" / "cases.jsonl")
        n_hold = emit_split(hold, prefix_hold, lane_dir / "holdouts" / "v1" / "cases.jsonl")
        n_dev = emit_dev(pub, prefix_pub, lane_dir / "dev" / "cases.jsonl")
        print(f"{lane:38s}  public={n_pub:3d}  holdouts={n_hold:3d}  dev={n_dev:2d}")
