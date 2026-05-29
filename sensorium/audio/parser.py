"""
sensorium/audio/parser.py — typed AudioIR parser (spec §5).

Promotes the lexer's per-frame tokens into typed spans and events. The IR is
built from runs of like frames, never from individual mel/frame values. Output
event types match the operator registry keys so every event lowers to a rotor.

Determinism: every numeric attr is a quantized int; events are emitted in a
stable per-category order; ``ir_sha256`` hashes the canonical serialization.
"""

from __future__ import annotations

from sensorium.audio.checksum import sha256_json
from sensorium.audio.types import AudioIR, AudioToken, AuditoryEvent

LONG_PAUSE_HOPS = 30          # >= 300 ms (10 ms hop) is a long pause / turn
SLOPE_CENTS_THRESH = 1        # min |Δcents_q| to call a contour rise/fall
EMPHASIS_DB_THRESH = 6        # min intra-span energy delta (dB) for emphasis


def _runs(kinds: list[str | None]) -> list[tuple[str, int, int]]:
    """Collapse a per-hop primary-kind list into (kind, start_hop, end_hop)."""
    runs: list[tuple[str, int, int]] = []
    i = 0
    n = len(kinds)
    while i < n:
        k = kinds[i]
        if k is None:
            i += 1
            continue
        j = i
        while j < n and kinds[j] == k:
            j += 1
        runs.append((k, i, j))
        i = j
    return runs


def parse(tokens: tuple[AudioToken, ...], n_hops: int) -> AudioIR:
    primary: list[str | None] = [None] * n_hops
    energy_db: dict[int, int] = {}
    pitch_cents: dict[int, int] = {}

    for tok in tokens:
        h = tok.start_hop
        if tok.kind == "energy_bin":
            energy_db[h] = tok.value_q[0]
        elif tok.kind in ("silence", "voiced", "unvoiced"):
            primary[h] = tok.kind
        elif tok.kind == "pitch_candidates" and tok.value_q:
            pitch_cents[h] = tok.value_q[0]  # top candidate's cents_q

    speech_spans: list[AuditoryEvent] = []
    pause_spans: list[AuditoryEvent] = []
    prosody_arcs: list[AuditoryEvent] = []
    turn_events: list[AuditoryEvent] = []
    non_speech_events: list[AuditoryEvent] = []

    for kind, start, end in _runs(primary):
        dur = end - start
        if kind == "silence":
            is_long = dur >= LONG_PAUSE_HOPS
            etype = "pause.long" if is_long else "pause.short"
            pause_spans.append(AuditoryEvent(etype, start, end, (("dur_hops", dur),), ()))
            if is_long:
                turn_events.append(
                    AuditoryEvent("turn.boundary", start, end, (("boundary_q", dur),), ())
                )
        elif kind == "voiced":
            speech_spans.append(
                AuditoryEvent("speech.voiced", start, end, (("dur_hops", dur),), ())
            )
            # Prosody arc from the final-contour F0 slope over the span.
            cents = [pitch_cents[h] for h in range(start, end) if h in pitch_cents]
            if len(cents) >= 2:
                slope = cents[-1] - cents[0]
                if slope >= SLOPE_CENTS_THRESH:
                    prosody_arcs.append(
                        AuditoryEvent("prosody.rise", start, end, (("slope_q", slope),), ())
                    )
                elif slope <= -SLOPE_CENTS_THRESH:
                    prosody_arcs.append(
                        AuditoryEvent("prosody.fall", start, end, (("slope_q", -slope),), ())
                    )
            # Emphasis from intra-span energy delta.
            dbs = [energy_db[h] for h in range(start, end) if h in energy_db]
            if dbs and (max(dbs) - min(dbs)) >= EMPHASIS_DB_THRESH:
                prosody_arcs.append(
                    AuditoryEvent(
                        "prosody.emphasis", start, end,
                        (("delta_db_q", max(dbs) - min(dbs)),), (),
                    )
                )
        elif kind == "unvoiced":
            non_speech_events.append(
                AuditoryEvent("nonspeech.noise", start, end, (("noise_q", dur),), ())
            )

    ir_payload = _ir_payload(
        speech_spans, pause_spans, prosody_arcs, turn_events, non_speech_events, ()
    )
    return AudioIR(
        speech_spans=tuple(speech_spans),
        pause_spans=tuple(pause_spans),
        prosody_arcs=tuple(prosody_arcs),
        turn_events=tuple(turn_events),
        non_speech_events=tuple(non_speech_events),
        content_anchors=(),
        ir_sha256=sha256_json(ir_payload),
    )


def _ev(e: AuditoryEvent) -> dict:
    return {
        "event_type": e.event_type,
        "start_hop": e.start_hop,
        "end_hop": e.end_hop,
        "attrs": [list(a) for a in e.attrs],
        "evidence_ids": list(e.evidence_ids),
    }


def _ir_payload(speech, pause, prosody, turn, non_speech, content_anchor) -> dict:
    """Canonical JSON-serialisable IR image — the single source of truth for
    ``ir_sha256`` so a hint-augmented IR (PR-6) hashes by the same rule."""
    return {
        "speech": [_ev(e) for e in speech],
        "pause": [_ev(e) for e in pause],
        "prosody": [_ev(e) for e in prosody],
        "turn": [_ev(e) for e in turn],
        "non_speech": [_ev(e) for e in non_speech],
        "content_anchor": [_ev(e) for e in content_anchor],
    }


def ir_sha256_of(ir: AudioIR) -> str:
    """Recompute ``ir_sha256`` from an AudioIR's events. Byte-identical to what
    ``parse`` stored for an un-augmented IR (regression-guarded in tests); the
    teacher-hint admission path (`sensorium.audio.teachers`) uses it to re-hash
    an IR after appending content anchors."""
    return sha256_json(
        _ir_payload(
            ir.speech_spans, ir.pause_spans, ir.prosody_arcs,
            ir.turn_events, ir.non_speech_events, ir.content_anchors,
        )
    )
