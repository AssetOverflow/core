"""Event-stream vision modality adapter."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sensorium.protocol import CL41_DIM, Modality, ModalityPack, ModalityVocabulary
from sensorium.vision_event.compiler import EventVisionCompiler
from sensorium.vision_event.types import EventPacket


@dataclass(frozen=True, slots=True)
class EventVisionProjectionHead:
    """ProjectionHead for one synthetic EventPacket."""

    compiler: EventVisionCompiler
    modality: Modality = Modality.VISION

    @property
    def embedding_dim(self) -> int:
        return CL41_DIM

    def project(self, signal: EventPacket) -> np.ndarray:
        out = self.compiler.compile_packet(signal).versor
        if out.shape != (CL41_DIM,):
            raise ValueError(f"expected ({CL41_DIM},), got {out.shape}")
        if out.dtype != np.float32:
            raise TypeError(f"expected float32, got {out.dtype}")
        return out

    def project_batch(self, signals: list[EventPacket]) -> np.ndarray:
        return np.stack([self.project(signal) for signal in signals], axis=0)

    def verify_unitarity(self, sample: EventPacket) -> bool:
        try:
            return self.compiler.compile_packet(sample).versor_condition < 1e-6
        except Exception:
            return False


def make_event_vision_pack(
    pack_id: str = "vision_event_core_v1",
    *,
    gate_engaged: bool = False,
    checksum_verified: bool = False,
    packs_root=None,
) -> ModalityPack:
    from packs.vision.loader import load_vision_pack

    loaded = load_vision_pack(pack_id, packs_root=packs_root)
    compiler = EventVisionCompiler(loaded.registry, pack_id=loaded.pack_id)
    head = EventVisionProjectionHead(compiler)
    return ModalityPack(
        pack_id=loaded.pack_id,
        modality_type=Modality.VISION,
        projection=head,
        decoder=None,
        vocabulary=ModalityVocabulary(),
        grammar_scaffold=None,
        checksum_verified=checksum_verified,
        gate_engaged=gate_engaged,
    )


__all__ = ["EventVisionProjectionHead", "make_event_vision_pack"]
