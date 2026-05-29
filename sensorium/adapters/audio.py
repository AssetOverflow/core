"""
sensorium/adapters/audio.py — Audio modality adapter (ADR-0181 PR-3).

The thin, pack-governed ProjectionHead for audio. It wraps the deterministic
AudioCompiler (PR-2): a canonical AudioSignal is compiled to one
AudioCompilationUnit and the unit's (32,) float32 versor crosses the
Logos-recovery boundary.

The pack mounts **gate-closed** (``gate_engaged=False``) until the eval gates
(PR-4) pass — `ModalityRegistry.project` refuses a closed gate, so audio
contributes no field state until determinism/checksum/versor gates are green
(ADR-0181 §2.5). Adding audio touches no existing layer (ADR-0013).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sensorium.audio.canonical import CANONICAL_SAMPLE_RATE, canonicalize
from sensorium.audio.compiler import AudioCompiler
from sensorium.audio.types import AudioSignal
from sensorium.protocol import (
    CL41_DIM,
    Modality,
    ModalityPack,
    ModalityVocabulary,
)


@dataclass(frozen=True, slots=True)
class AudioProjectionHead:
    """D1 projection head for audio.

    Determinism class: D1 — deterministic given a pinned pack (operator
    registry + basis). ``project`` accepts an already-canonical AudioSignal;
    raw waveform is canonicalised upstream via ``canonicalize`` (a helper is
    exposed as ``project_raw`` for convenience).
    """

    compiler: AudioCompiler
    modality: Modality = Modality.AUDIO

    @property
    def embedding_dim(self) -> int:
        return CL41_DIM

    def project(self, signal: AudioSignal) -> np.ndarray:
        out = self.compiler.compile_signal(signal).versor
        if out.shape != (CL41_DIM,):
            raise ValueError(f"expected ({CL41_DIM},), got {out.shape}")
        if out.dtype != np.float32:
            raise TypeError(f"expected float32, got {out.dtype}")
        return out

    def project_batch(self, signals: list[AudioSignal]) -> np.ndarray:
        return np.stack([self.project(s) for s in signals], axis=0)

    def project_raw(
        self, samples: np.ndarray, sample_rate: int, *, fir: np.ndarray | None = None
    ) -> np.ndarray:
        """Convenience: canonicalise raw samples then project."""
        signal = canonicalize(samples, sample_rate, target_sr=CANONICAL_SAMPLE_RATE, fir=fir)
        return self.project(signal)

    def verify_unitarity(self, sample: AudioSignal) -> bool:
        try:
            return self.compiler.compile_signal(sample).versor_condition < 1e-6
        except Exception:
            return False


def make_audio_pack(
    pack_id: str = "audio_core_v1",
    *,
    gate_engaged: bool = False,
    checksum_verified: bool = False,
    packs_root=None,
) -> ModalityPack:
    """Construct a gate-closed audio ModalityPack from a verified pack.

    Loads + checksum-verifies the pack (fail-closed), builds the compiler over
    the pack's operator registry, and wraps it in an AudioProjectionHead. The
    pack ships gate-closed; engaging the gate is the PR-4 eval-gate decision.
    """
    from packs.audio.loader import load_audio_pack

    loaded = load_audio_pack(pack_id, packs_root=packs_root)
    compiler = AudioCompiler(loaded.registry, pack_id=loaded.pack_id)
    head = AudioProjectionHead(compiler)
    return ModalityPack(
        pack_id=loaded.pack_id,
        modality_type=Modality.AUDIO,
        projection=head,
        decoder=None,
        vocabulary=ModalityVocabulary(),
        grammar_scaffold=None,
        checksum_verified=checksum_verified,
        gate_engaged=gate_engaged,
    )
