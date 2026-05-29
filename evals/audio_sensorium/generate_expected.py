"""
evals/audio_sensorium/generate_expected.py — (re)generate frozen expected artifacts.

Run from the repo root:  ``uv run python -m evals.audio_sensorium.generate_expected``

Produces (committed, reviewed):
  - expected_ir.jsonl       per fixture: canonical_sha256, ir_sha256, event_type_counts
  - expected_projection.json per fixture: projection_sha256 + reference_versor

The int/quantized-derived pins (ir_sha256, event_type_counts, canonical_sha256)
are platform-stable and asserted hard by the gate tests. The reference_versor is
compared within numeric tolerance (cross-platform float safety — eval plan).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from evals.audio_sensorium.synth import synthesize
from sensorium.audio.canonical import canonicalize
from sensorium.audio.compiler import AudioCompiler
from sensorium.audio.types import AudioIR

_HERE = Path(__file__).resolve().parent
SR = 24_000


def event_type_counts(ir: AudioIR) -> dict[str, int]:
    events = (
        *ir.speech_spans, *ir.pause_spans, *ir.prosody_arcs,
        *ir.turn_events, *ir.non_speech_events, *ir.content_anchors,
    )
    return dict(sorted(Counter(e.event_type for e in events).items()))


def main() -> None:
    spec = json.loads((_HERE / "fixtures.json").read_text())
    compiler = AudioCompiler()
    ir_lines: list[str] = []
    projection: dict[str, dict] = {}

    for fx in spec["fixtures"]:
        signal = canonicalize(synthesize(fx), SR)
        unit = compiler.compile_signal(signal)
        ir_lines.append(json.dumps({
            "id": fx["id"],
            "canonical_sha256": unit.canonical_sha256,
            "ir_sha256": unit.ir_sha256,
            "event_type_counts": event_type_counts(unit.audio_ir),
        }, sort_keys=True))
        projection[fx["id"]] = {
            "projection_sha256": unit.projection_sha256,
            "reference_versor": [float(x) for x in unit.versor.tolist()],
        }

    (_HERE / "expected_ir.jsonl").write_text("\n".join(ir_lines) + "\n")
    (_HERE / "expected_projection.json").write_text(
        json.dumps(projection, indent=2, sort_keys=True) + "\n"
    )
    print(f"wrote expected artifacts for {len(spec['fixtures'])} fixtures")


if __name__ == "__main__":
    main()
