"""
sensorium/audio/trace.py — audio evidence trace (spec §6, ADR-0181 §3.1).

Produces the trace-safe record of a compiled audio chunk: the layered
checksum chain, pack identity, and the content-addressed merge key — and
NEVER raw waveform bytes (ADR-0181 §4.2 A-6 / ADR-0180 §1.5.5). This is what
a CognitiveTurnResult / TurnEvent stores as audio evidence.
"""

from __future__ import annotations

from sensorium.audio.types import AudioCompilationUnit


def audio_evidence_trace(unit: AudioCompilationUnit) -> dict[str, object]:
    """Trace-safe evidence dict for one compiled chunk. No PCM."""
    return {
        "modality": "audio",
        "pack_id": unit.pack_id,
        "canonical_sha256": unit.canonical_sha256,
        "ir_sha256": unit.ir_sha256,
        "pack_manifest_sha256": unit.pack_manifest_sha256,
        "projection_sha256": unit.projection_sha256,
        "merge_key": list(unit.merge_key),
        "versor_condition": unit.versor_condition,
    }
