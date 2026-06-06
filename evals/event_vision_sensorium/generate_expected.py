"""Regenerate frozen expected artifacts for the event-vision eval lane."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from evals.event_vision_sensorium.synth import synthesize
from sensorium.vision_event import EventVisionCompiler

_ROOT = Path(__file__).resolve().parent


def main() -> None:
    fixtures = json.loads((_ROOT / "fixtures.json").read_text(encoding="utf-8"))["fixtures"]
    compiler = EventVisionCompiler()
    expected_ir: list[dict[str, object]] = []
    expected_projection: dict[str, object] = {}
    for fixture in fixtures:
        fid = fixture["id"]
        unit = compiler.compile_packet(synthesize(fixture))
        counts = Counter(
            event.event_type
            for event in (
                *unit.event_ir.onset_events,
                *unit.event_ir.decay_events,
                *unit.event_ir.motion_bins,
            )
        )
        expected_ir.append({
            "id": fid,
            "ir_sha256": unit.ir_sha256,
            "event_type_counts": dict(sorted(counts.items())),
        })
        expected_projection[fid] = {
            "projection_sha256": unit.projection_sha256,
            "reference_versor": [float(x) for x in unit.versor.tolist()],
        }
    (_ROOT / "expected_ir.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in expected_ir) + "\n",
        encoding="utf-8",
    )
    (_ROOT / "expected_projection.json").write_text(
        json.dumps(expected_projection, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
