"""Regenerate frozen expected artifacts for the vision eval lane."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from evals.vision_sensorium.synth import synthesize
from sensorium.vision import VisionCompiler, canonicalize_image
from sensorium.vision.types import VisionIR

_HERE = Path(__file__).resolve().parent


def event_type_counts(ir: VisionIR) -> dict[str, int]:
    events = (
        *ir.regions,
        *ir.contour_arcs,
        *ir.orient_events,
        *ir.texture_atoms,
        *ir.salient_events,
        *ir.content_anchors,
    )
    return dict(sorted(Counter(e.event_type for e in events).items()))


def main() -> None:
    spec = json.loads((_HERE / "fixtures.json").read_text())
    compiler = VisionCompiler()
    ir_lines: list[str] = []
    projection: dict[str, list[dict]] = {}

    for fx in spec["fixtures"]:
        image = canonicalize_image(synthesize(fx), size=int(spec["size"]))
        units = compiler.compile_image(image)
        counts = Counter()
        for unit in units:
            counts.update(event_type_counts(unit.vision_ir))
        ir_lines.append(json.dumps({
            "id": fx["id"],
            "canonical_sha256": image.canonical_sha256,
            "unit_count": len(units),
            "unit_ir_sha256": [unit.ir_sha256 for unit in units],
            "event_type_counts": dict(sorted(counts.items())),
        }, sort_keys=True))
        projection[fx["id"]] = [
            {
                "coord": {
                    "scale_level": unit.coord.scale_level,
                    "tile_row": unit.coord.tile_row,
                    "tile_col": unit.coord.tile_col,
                },
                "projection_sha256": unit.projection_sha256,
                "reference_versor": [float(x) for x in unit.versor.tolist()],
            }
            for unit in units
        ]

    (_HERE / "expected_ir.jsonl").write_text("\n".join(ir_lines) + "\n")
    (_HERE / "expected_projection.json").write_text(
        json.dumps(projection, indent=2, sort_keys=True) + "\n"
    )
    print(f"wrote expected artifacts for {len(spec['fixtures'])} fixtures")


if __name__ == "__main__":
    main()
