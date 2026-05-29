"""
ADR-0181 PR-3 — audio ProjectionHead mount + gate governance.

Covers the registry contract for audio:
  - the pack mounts gate-closed; projection is refused while the gate is closed;
  - mount-time unitarity runs on a probe AudioSignal and passes;
  - bad unitarity blocks the mount;
  - engaging the gate requires checksum_verified (ModalityPack invariant);
  - an engaged pack projects to (32,) float32.
"""

from __future__ import annotations

import numpy as np
import pytest

from sensorium.adapters.audio import AudioProjectionHead, make_audio_pack
from sensorium.audio.canonical import canonicalize
from sensorium.protocol import CL41_DIM, Modality, ModalityPack, ModalityVocabulary
from sensorium.registry import ModalityRegistry

SR = 24_000


def _signal():
    n = int(SR * 0.3)
    t = np.arange(n, dtype=np.float64) / SR
    samples = (0.5 * np.sin(2 * np.pi * 160.0 * t)).astype(np.float32)
    return canonicalize(samples, SR)


def test_pack_ships_gate_closed():
    pack = make_audio_pack("audio_core_v1")
    assert pack.modality_type is Modality.AUDIO
    assert pack.gate_engaged is False
    assert pack.projection is not None


def test_mount_runs_unitarity_and_succeeds():
    reg = ModalityRegistry()
    pack = make_audio_pack("audio_core_v1")
    reg.mount(pack, sample=_signal())          # runs verify_unitarity on the probe
    assert "audio_core_v1" in reg


def test_closed_gate_refuses_projection():
    reg = ModalityRegistry()
    reg.mount(make_audio_pack("audio_core_v1"), sample=_signal())
    with pytest.raises(RuntimeError, match="gate is not engaged"):
        reg.project("audio_core_v1", _signal())


def test_bad_unitarity_blocks_mount():
    """A projection whose verify_unitarity fails must not mount (eval-plan §2)."""
    class _BrokenHead:
        modality = Modality.AUDIO
        embedding_dim = CL41_DIM

        def project(self, signal):  # pragma: no cover - not reached
            return np.zeros(CL41_DIM, dtype=np.float32)

        def project_batch(self, signals):  # pragma: no cover
            return np.zeros((len(signals), CL41_DIM), dtype=np.float32)

        def verify_unitarity(self, sample) -> bool:
            return False

    pack = ModalityPack(
        pack_id="audio_broken",
        modality_type=Modality.AUDIO,
        projection=_BrokenHead(),
        vocabulary=ModalityVocabulary(),
        grammar_scaffold=None,
        checksum_verified=False,
        gate_engaged=False,
    )
    with pytest.raises(ValueError, match="Unitarity check failed"):
        ModalityRegistry().mount(pack, sample=_signal())


def test_engaging_gate_requires_checksum_verified():
    with pytest.raises(ValueError, match="checksum_verified"):
        make_audio_pack("audio_core_v1", gate_engaged=True, checksum_verified=False)


def test_engaged_pack_projects_32_float32():
    reg = ModalityRegistry()
    reg.mount(
        make_audio_pack("audio_core_v1", gate_engaged=True, checksum_verified=True),
        sample=_signal(),
    )
    mv = reg.project("audio_core_v1", _signal())
    assert mv.shape == (CL41_DIM,)
    assert mv.dtype == np.float32


def test_project_raw_canonicalises_then_projects():
    head: AudioProjectionHead = make_audio_pack("audio_core_v1").projection
    n = int(SR * 0.25)
    t = np.arange(n, dtype=np.float64) / SR
    raw = (0.4 * np.sin(2 * np.pi * 200.0 * t)).astype(np.float32)
    mv = head.project_raw(raw, SR)
    assert mv.shape == (CL41_DIM,) and mv.dtype == np.float32
