"""Python reference compiler for synthetic event-stream vision packets."""

from __future__ import annotations

import numpy as np

from algebra.cl41 import geometric_product
from algebra.versor import unitize_versor, versor_condition
from sensorium.vision.checksum import sha256_array
from sensorium.vision.operators import VisionOperatorRegistry, build_elliptic_rotor
from sensorium.vision_event.lexer import lex_event_packet
from sensorium.vision_event.operators import DEFAULT_EVENT_OPERATOR_REGISTRY
from sensorium.vision_event.parser import parse_event_atoms
from sensorium.vision_event.types import EventAtom, EventCompilationUnit, EventIR, EventPacket

CL41_DIM = 32
VERSOR_CONDITION_MAX = 1e-6
_PRECEDENCE = {"event.onset": 0, "event.decay": 1, "event.motion_delta": 2}


def canonical_event_atom_order(ir: EventIR) -> list[EventAtom]:
    atoms = [*ir.onset_events, *ir.decay_events, *ir.motion_bins]
    return sorted(
        atoms,
        key=lambda atom: (
            atom.coord.scale_level,
            atom.coord.morton,
            _PRECEDENCE.get(atom.event_type, len(_PRECEDENCE)),
            atom.event_type,
            atom.attrs,
            atom.evidence_ids,
        ),
    )


def compile_event_atoms(
    atoms: list[EventAtom],
    registry: VisionOperatorRegistry,
) -> tuple[np.ndarray, float]:
    """Serialization barrier: fold one packet's canonical deltas into one versor."""
    v = np.zeros(CL41_DIM, dtype=np.float64)
    v[0] = 1.0
    for atom in atoms:
        if atom.event_type not in registry:
            continue
        spec = registry[atom.event_type]
        r = build_elliptic_rotor(spec.blade_index, spec.theta_q_from_event(atom))
        v = geometric_product(v, r)
        v = unitize_versor(v)
    vc = float(versor_condition(v))
    if vc >= VERSOR_CONDITION_MAX:
        raise ValueError(
            f"event vision compilation failed versor check: versor_condition={vc:.3e} "
            f">= {VERSOR_CONDITION_MAX:.0e}"
        )
    return v.astype(np.float32), vc


class EventVisionCompiler:
    """Deterministic compiler from one EventPacket to one compilation unit."""

    def __init__(
        self,
        registry: VisionOperatorRegistry = DEFAULT_EVENT_OPERATOR_REGISTRY,
        pack_id: str = "vision_event_core_v1",
    ) -> None:
        self._registry = registry
        self._pack_id = pack_id
        self._manifest_sha256 = registry.manifest_sha256()

    def compile_packet(self, packet: EventPacket) -> EventCompilationUnit:
        ir = parse_event_atoms(lex_event_packet(packet))
        return self.compile_ir(
            ir,
            canonical_sha256=packet.canonical_sha256,
            packet_tick=packet.packet_tick,
            grid_shape=(packet.grid_h, packet.grid_w),
        )

    def compile_signal(self, packet: EventPacket) -> EventCompilationUnit:
        return self.compile_packet(packet)

    def compile_ir(
        self,
        ir: EventIR,
        *,
        canonical_sha256: str = "",
        packet_tick: int = 0,
        grid_shape: tuple[int, int] = (0, 0),
    ) -> EventCompilationUnit:
        atoms = canonical_event_atom_order(ir)
        if not atoms:
            raise ValueError("cannot replay EventIR with no event atoms")
        versor, vc = compile_event_atoms(atoms, self._registry)
        return EventCompilationUnit(
            canonical_sha256=canonical_sha256,
            ir_sha256=ir.ir_sha256,
            pack_id=self._pack_id,
            pack_manifest_sha256=self._manifest_sha256,
            projection_sha256=sha256_array(versor),
            packet_tick=int(packet_tick),
            grid_shape=(int(grid_shape[0]), int(grid_shape[1])),
            versor=versor,
            versor_condition=vc,
            event_ir=ir,
        )


__all__ = [
    "EventVisionCompiler",
    "canonical_event_atom_order",
    "compile_event_atoms",
]
