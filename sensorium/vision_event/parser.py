"""Parser from event atoms into deterministic EventIR."""

from __future__ import annotations

from collections.abc import Iterable

from sensorium.vision.checksum import sha256_json
from sensorium.vision_event.types import EventAtom, EventIR


def _atom_record(atom: EventAtom) -> dict[str, object]:
    return {
        "event_type": atom.event_type,
        "coord": {
            "scale_level": atom.coord.scale_level,
            "tile_row": atom.coord.tile_row,
            "tile_col": atom.coord.tile_col,
            "morton": atom.coord.morton,
        },
        "attrs": [list(attr) for attr in atom.attrs],
        "evidence_ids": list(atom.evidence_ids),
    }


def _stable_atom(atom: EventAtom) -> tuple[object, ...]:
    return (
        atom.coord.scale_level,
        atom.coord.morton,
        atom.event_type,
        atom.attrs,
        atom.evidence_ids,
    )


def parse_event_atoms(atoms: Iterable[EventAtom]) -> EventIR:
    ordered = tuple(sorted(atoms, key=_stable_atom))
    onset = tuple(atom for atom in ordered if atom.event_type == "event.onset")
    decay = tuple(atom for atom in ordered if atom.event_type == "event.decay")
    motion = tuple(atom for atom in ordered if atom.event_type == "event.motion_delta")
    payload = {
        "kind": "EventIR",
        "onset_events": [_atom_record(atom) for atom in onset],
        "decay_events": [_atom_record(atom) for atom in decay],
        "motion_bins": [_atom_record(atom) for atom in motion],
    }
    return EventIR(
        onset_events=onset,
        decay_events=decay,
        motion_bins=motion,
        ir_sha256=sha256_json(payload),
    )


__all__ = ["parse_event_atoms"]
