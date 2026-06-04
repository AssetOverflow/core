"""Deterministic tile-first vision compiler."""

from __future__ import annotations

import numpy as np

from algebra.cl41 import geometric_product
from algebra.versor import unitize_versor, versor_condition
from sensorium.vision.checksum import sha256_array
from sensorium.vision.grid import iter_tile_signals
from sensorium.vision.lexer import lex_tile
from sensorium.vision.operators import (
    DEFAULT_OPERATOR_REGISTRY,
    VisionOperatorRegistry,
    build_elliptic_rotor,
)
from sensorium.vision.parser import parse
from sensorium.vision.types import VisionCompilationUnit, VisionIR, VisionImage, VisionTileSignal, VisualEvent

CL41_DIM = 32
VERSOR_CONDITION_MAX = 1e-6
_PRECEDENCE = ("region", "contour", "orient", "texture", "salient", "content_anchor")


def _category(event_type: str) -> str:
    prefix = event_type.split(".", 1)[0]
    if prefix == "content":
        return "content_anchor"
    return prefix


def _stable_event_id(event: VisualEvent) -> tuple[str, tuple[tuple[str, int | str], ...], tuple[str, ...]]:
    return (event.event_type, event.attrs, event.evidence_ids)


def canonical_event_order(ir: VisionIR) -> list[VisualEvent]:
    events = [
        *ir.regions,
        *ir.contour_arcs,
        *ir.orient_events,
        *ir.texture_atoms,
        *ir.salient_events,
        *ir.content_anchors,
    ]
    rank = {name: i for i, name in enumerate(_PRECEDENCE)}
    return sorted(
        events,
        key=lambda e: (
            e.coord.scale_level,
            e.coord.morton,
            rank.get(_category(e.event_type), len(_PRECEDENCE)),
            _stable_event_id(e),
        ),
    )


def compile_events(
    events: list[VisualEvent],
    registry: VisionOperatorRegistry,
) -> tuple[np.ndarray, float]:
    """Serialization barrier: fold canonical spatial events into one versor."""
    v = np.zeros(CL41_DIM, dtype=np.float64)
    v[0] = 1.0
    for ev in events:
        if ev.event_type not in registry:
            continue
        spec = registry[ev.event_type]
        r = build_elliptic_rotor(spec.blade_index, spec.theta_q_from_event(ev))
        v = geometric_product(v, r)
        v = unitize_versor(v)
    vc = float(versor_condition(v))
    if vc >= VERSOR_CONDITION_MAX:
        raise ValueError(
            f"vision compilation failed versor check: versor_condition={vc:.3e} "
            f">= {VERSOR_CONDITION_MAX:.0e}"
        )
    return v.astype(np.float32), vc


class VisionCompiler:
    """Deterministic compiler from one tile signal to one compilation unit."""

    def __init__(
        self,
        registry: VisionOperatorRegistry = DEFAULT_OPERATOR_REGISTRY,
        pack_id: str = "vision_core_v1",
    ) -> None:
        self._registry = registry
        self._pack_id = pack_id
        self._manifest_sha256 = registry.manifest_sha256()

    def compile_tile(self, signal: VisionTileSignal) -> VisionCompilationUnit:
        ir = parse(lex_tile(signal))
        versor, vc = compile_events(canonical_event_order(ir), self._registry)
        return VisionCompilationUnit(
            canonical_sha256=signal.image.canonical_sha256,
            ir_sha256=ir.ir_sha256,
            pack_id=self._pack_id,
            pack_manifest_sha256=self._manifest_sha256,
            projection_sha256=sha256_array(versor),
            coord=signal.coord,
            versor=versor,
            versor_condition=vc,
            vision_ir=ir,
        )

    def compile_signal(self, signal: VisionTileSignal) -> VisionCompilationUnit:
        return self.compile_tile(signal)

    def compile_image(self, image: VisionImage) -> tuple[VisionCompilationUnit, ...]:
        return tuple(self.compile_tile(signal) for signal in iter_tile_signals(image))

    def compile_ir(self, ir: VisionIR) -> VisionCompilationUnit:
        events = canonical_event_order(ir)
        if not events:
            raise ValueError("cannot replay VisionIR with no events")
        coord = events[0].coord
        versor, vc = compile_events(events, self._registry)
        return VisionCompilationUnit(
            canonical_sha256="",
            ir_sha256=ir.ir_sha256,
            pack_id=self._pack_id,
            pack_manifest_sha256=self._manifest_sha256,
            projection_sha256=sha256_array(versor),
            coord=coord,
            versor=versor,
            versor_condition=vc,
            vision_ir=ir,
        )
