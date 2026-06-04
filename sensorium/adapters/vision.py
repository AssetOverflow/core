"""Vision modality adapter."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sensorium.protocol import CL41_DIM, Modality, ModalityPack, ModalityVocabulary
from sensorium.vision.compiler import VisionCompiler
from sensorium.vision.types import VisionImage, VisionTileSignal


@dataclass(frozen=True, slots=True)
class VisionProjectionHead:
    """ProjectionHead for one tile-at-one-scale VisionTileSignal."""

    compiler: VisionCompiler
    modality: Modality = Modality.VISION

    @property
    def embedding_dim(self) -> int:
        return CL41_DIM

    def project(self, signal: VisionTileSignal) -> np.ndarray:
        out = self.compiler.compile_tile(signal).versor
        if out.shape != (CL41_DIM,):
            raise ValueError(f"expected ({CL41_DIM},), got {out.shape}")
        if out.dtype != np.float32:
            raise TypeError(f"expected float32, got {out.dtype}")
        return out

    def project_batch(self, signals: list[VisionTileSignal]) -> np.ndarray:
        return np.stack([self.project(signal) for signal in signals], axis=0)

    def compile_image(self, image: VisionImage):
        """Expand a whole canonical image into tile compilation units."""
        return self.compiler.compile_image(image)

    def verify_unitarity(self, sample: VisionTileSignal) -> bool:
        try:
            return self.compiler.compile_tile(sample).versor_condition < 1e-6
        except Exception:
            return False


def make_vision_pack(
    pack_id: str = "vision_core_v1",
    *,
    gate_engaged: bool = False,
    checksum_verified: bool = False,
    packs_root=None,
) -> ModalityPack:
    from packs.vision.loader import load_vision_pack

    loaded = load_vision_pack(pack_id, packs_root=packs_root)
    compiler = VisionCompiler(loaded.registry, pack_id=loaded.pack_id)
    head = VisionProjectionHead(compiler)
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
