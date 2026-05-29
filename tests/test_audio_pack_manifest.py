"""
ADR-0181 PR-3 — audio pack manifest + loader trust boundary.

Covers:
  - the loaded operator registry is byte-equivalent to the in-code
    DEFAULT_OPERATOR_REGISTRY (PR-2 ↔ PR-3 parity, via manifest_sha256);
  - fail-closed checksum verification (tampered artifact blocks load);
  - the ADR-0051 path-traversal guard;
  - the pinned FIR artifact integrity.
"""

from __future__ import annotations

import shutil

import pytest

from packs.audio.loader import AudioPackError, load_audio_pack
from sensorium.audio.operators import DEFAULT_OPERATOR_REGISTRY, ELLIPTIC_PLANES


def test_pack_loads_and_verifies():
    pack = load_audio_pack("audio_core_v1")
    assert pack.pack_id == "audio_core_v1"
    assert pack.manifest["cl41_dim"] == 32
    assert pack.manifest["gating"]["gate_engaged"] is False  # ships gate-closed


def test_loaded_registry_is_byte_equivalent_to_in_code_default():
    """The pack artifact and the in-code DEFAULT_OPERATOR_REGISTRY must produce
    the identical content hash — PR-3 externalises PR-2 without drift."""
    pack = load_audio_pack("audio_core_v1")
    assert pack.registry.manifest_sha256() == DEFAULT_OPERATOR_REGISTRY.manifest_sha256()
    assert set(pack.registry.specs) == set(DEFAULT_OPERATOR_REGISTRY.specs)


def test_all_loaded_operators_are_elliptic():
    pack = load_audio_pack("audio_core_v1")
    for spec in pack.registry.specs.values():
        assert spec.blade_index in ELLIPTIC_PLANES


def test_fir_artifact_is_odd_length_and_matches_manifest():
    pack = load_audio_pack("audio_core_v1")
    assert pack.fir is not None
    assert pack.fir.ndim == 1 and pack.fir.size % 2 == 1   # zero-phase symmetric
    assert pack.fir_sha256.endswith(pack.manifest["resampling"]["fir_sha256"])


# --- trust boundary -------------------------------------------------------

def test_checksum_mismatch_fails_closed(tmp_path):
    """A tampered artifact must block the load (eval-plan §2 mount validation)."""
    from packs.audio.loader import _PACKS_ROOT
    dst = tmp_path / "audio_core_v1"
    shutil.copytree(_PACKS_ROOT / "audio_core_v1", dst)
    # Corrupt operators.jsonl without updating checksums.json.
    (dst / "operators.jsonl").write_text((dst / "operators.jsonl").read_text() + "\n")
    with pytest.raises(AudioPackError, match="checksum mismatch"):
        load_audio_pack("audio_core_v1", packs_root=tmp_path)


@pytest.mark.parametrize("bad_id", ["..", "../secrets", "a/b", "a\\b", ".hidden", ""])
def test_path_traversal_rejected(bad_id):
    with pytest.raises(AudioPackError):
        load_audio_pack(bad_id)


def test_missing_pack_fails_closed(tmp_path):
    with pytest.raises(AudioPackError, match="no audio pack"):
        load_audio_pack("audio_core_v1", packs_root=tmp_path)
