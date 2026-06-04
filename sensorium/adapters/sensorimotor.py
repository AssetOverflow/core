"""Sensorimotor modality adapter.

Sensorimotor v1 is afferent proprioceptive feedback only. It provides a
ProjectionHead so compiled feedback can enter the shared manifold, but it does
not provide a SurfaceDecoder or any motor command path.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sensorium.protocol import CL41_DIM, Modality, ModalityPack, ModalityVocabulary
from sensorium.sensorimotor.compiler import SensorimotorCompiler
from sensorium.sensorimotor.types import ProprioceptiveSignal


@dataclass(frozen=True, slots=True)
class SensorimotorProjectionHead:
    """ProjectionHead for quantized afferent ProprioceptiveSignal values."""

    compiler: SensorimotorCompiler
    modality: Modality = Modality.SENSORIMOTOR

    @property
    def embedding_dim(self) -> int:
        return CL41_DIM

    def project(self, signal: ProprioceptiveSignal) -> np.ndarray:
        out = self.compiler.compile_signal(signal).versor
        if out.shape != (CL41_DIM,):
            raise ValueError(f"expected ({CL41_DIM},), got {out.shape}")
        if out.dtype != np.float32:
            raise TypeError(f"expected float32, got {out.dtype}")
        return out

    def project_batch(self, signals: list[ProprioceptiveSignal]) -> np.ndarray:
        return np.stack([self.project(signal) for signal in signals], axis=0)

    def verify_unitarity(self, sample: ProprioceptiveSignal) -> bool:
        try:
            return self.compiler.compile_signal(sample).versor_condition < 1e-6
        except Exception:
            return False


def make_sensorimotor_pack(
    pack_id: str = "sensorimotor_core_v1",
    *,
    gate_engaged: bool = False,
    checksum_verified: bool = False,
    packs_root=None,
) -> ModalityPack:
    from packs.sensorimotor.loader import load_sensorimotor_pack

    loaded = load_sensorimotor_pack(pack_id, packs_root=packs_root)
    compiler = SensorimotorCompiler(
        loaded.pack_id,
        pack_manifest_sha256=loaded.manifest_sha256,
    )
    return ModalityPack(
        pack_id=loaded.pack_id,
        modality_type=Modality.SENSORIMOTOR,
        projection=SensorimotorProjectionHead(compiler),
        decoder=None,
        vocabulary=ModalityVocabulary(),
        grammar_scaffold=None,
        checksum_verified=checksum_verified,
        gate_engaged=gate_engaged,
    )
