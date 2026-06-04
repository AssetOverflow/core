"""Regenerate frozen expected artifacts for sensorimotor eval."""

from __future__ import annotations

import json
from pathlib import Path

from evals.sensorimotor_sensorium.synth import synthesize
from sensorium.sensorimotor import SensorimotorCompiler

_HERE = Path(__file__).resolve().parent


def main() -> None:
    spec = json.loads((_HERE / "fixtures.json").read_text())
    compiler = SensorimotorCompiler()
    lines: list[str] = []
    projection: dict[str, dict] = {}
    for fx in spec["fixtures"]:
        signal = synthesize(fx)
        unit = compiler.compile_signal(signal)
        lines.append(json.dumps({
            "id": fx["id"],
            "canonical_sha256": unit.canonical_sha256,
            "ir_sha256": unit.ir_sha256,
            "event_count": len(unit.sensorimotor_ir.events),
            "event_types": [event.event_type for event in unit.sensorimotor_ir.events],
        }, sort_keys=True))
        projection[fx["id"]] = {
            "projection_sha256": unit.projection_sha256,
            "reference_versor": [float(x) for x in unit.versor.tolist()],
        }
    (_HERE / "expected_ir.jsonl").write_text("\n".join(lines) + "\n")
    (_HERE / "expected_projection.json").write_text(
        json.dumps(projection, indent=2, sort_keys=True) + "\n"
    )
    print(f"wrote expected artifacts for {len(spec['fixtures'])} fixtures")


if __name__ == "__main__":
    main()
