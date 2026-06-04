from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

from evals.sensorimotor_sensorium.synth import synthesize
from packs.sensorimotor.loader import SensorimotorPackError, load_sensorimotor_pack
from sensorium.adapters.sensorimotor import SensorimotorProjectionHead, make_sensorimotor_pack
from sensorium.protocol import Modality
from sensorium.registry import ModalityRegistry
from sensorium.sensorimotor import SensorimotorCompiler


def _fixture_signal():
    return synthesize({
        "id": "pack_probe",
        "pose_q": [1, 2, 3],
        "velocity_q": [0, 0, 1],
        "force_torque_q": [5, 8, 13],
        "contact_q": [1, 0],
        "actuator_state_q": [3, 5],
    })


def test_sensorimotor_pack_loads_and_mounts_closed_by_default():
    loaded = load_sensorimotor_pack("sensorimotor_core_v1")
    assert loaded.pack_id == "sensorimotor_core_v1"
    assert loaded.manifest["modality"] == "sensorimotor"
    assert loaded.manifest["gate_engaged"] is False

    pack = make_sensorimotor_pack("sensorimotor_core_v1")
    assert pack.modality_type is Modality.SENSORIMOTOR
    assert pack.decoder is None
    assert pack.gate_engaged is False

    reg = ModalityRegistry()
    reg.mount(pack, sample=_fixture_signal())
    with pytest.raises(RuntimeError, match="gate is not engaged"):
        reg.project("sensorimotor_core_v1", _fixture_signal())


def test_sensorimotor_projection_head_is_deterministic_when_engaged():
    sample = _fixture_signal()
    head = SensorimotorProjectionHead(SensorimotorCompiler())
    assert head.verify_unitarity(sample)
    mv = head.project(sample)
    assert mv.shape == (32,)
    assert mv.dtype == np.float32
    assert np.array_equal(mv, head.project(sample))

    reg = ModalityRegistry()
    reg.mount(
        make_sensorimotor_pack(
            "sensorimotor_core_v1",
            gate_engaged=True,
            checksum_verified=True,
        ),
        sample=sample,
    )
    assert np.array_equal(reg.project("sensorimotor_core_v1", sample), mv)


def test_sensorimotor_pack_rejects_path_traversal_and_checksum_mismatch(tmp_path: Path):
    with pytest.raises(SensorimotorPackError):
        load_sensorimotor_pack("../sensorimotor_core_v1")

    src = Path("packs/sensorimotor/sensorimotor_core_v1")
    root = tmp_path / "packs"
    shutil.copytree(src, root / "sensorimotor_core_v1")
    manifest = root / "sensorimotor_core_v1" / "manifest.json"
    manifest.write_text(manifest.read_text().replace('"cl41_dim": 32', '"cl41_dim": 31'))
    with pytest.raises(SensorimotorPackError, match="checksum mismatch"):
        load_sensorimotor_pack("sensorimotor_core_v1", packs_root=root)
