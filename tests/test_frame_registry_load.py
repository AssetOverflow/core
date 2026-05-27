"""CW-1 — frame_registry loader tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.comprehension.frame_registry import (
    FrameRegistry,
    FrameRegistryLoadError,
    clear_cache,
    load_frame_registry,
    lookup,
)
from language_packs.compile_frames import compile_frames


@pytest.fixture
def empty_pack(tmp_path: Path) -> Path:
    """A pack with manifest but no frames/ dir — empty-registry no-op."""
    (tmp_path / "manifest.json").write_text(
        json.dumps({"pack_id": "test_empty", "checksum": "deadbeef"}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def populated_pack(tmp_path: Path) -> Path:
    """Pack with two ratified frame entries + matching manifest checksum."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "transfer_frame.jsonl").write_text(
        json.dumps(
            {
                "surface_form": "gave",
                "frame_category": "transfer_frame",
                "polarity": "affirms",
                "provenance": "test_provenance",
                "evidence_hashes": ["dead"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _, sha = compile_frames(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "test_populated",
                "checksum": "deadbeef",
                "frame_checksum": sha,
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def setup_function(_):
    clear_cache()


def test_empty_pack_returns_empty_registry(empty_pack: Path):
    reg = load_frame_registry(empty_pack)
    assert isinstance(reg, FrameRegistry)
    assert reg.is_empty()
    assert reg.source_pack_id == "test_empty"
    assert dict(reg.by_surface) == {}


def test_populated_pack_round_trip(populated_pack: Path):
    reg = load_frame_registry(populated_pack)
    assert not reg.is_empty()
    entry = lookup(reg, "gave")
    assert entry is not None
    assert entry.surface_form == "gave"
    assert entry.frame_category == "transfer_frame"
    assert entry.polarity == "affirms"
    assert entry.provenance == "test_provenance"


def test_case_fold_on_lookup(populated_pack: Path):
    reg = load_frame_registry(populated_pack)
    assert lookup(reg, "GAVE") is not None
    assert lookup(reg, "Gave") is not None


def test_unknown_surface_returns_none(populated_pack: Path):
    reg = load_frame_registry(populated_pack)
    assert lookup(reg, "shouted") is None


def test_manifest_checksum_mismatch_raises(populated_pack: Path):
    manifest_path = populated_pack / "manifest.json"
    payload = json.loads(manifest_path.read_text())
    payload["frame_checksum"] = "f" * 64  # bogus
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    clear_cache()
    with pytest.raises(FrameRegistryLoadError, match="checksum mismatch"):
        load_frame_registry(populated_pack)


def test_declared_checksum_without_compiled_file_raises(tmp_path: Path):
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "test",
                "checksum": "deadbeef",
                "frame_checksum": "f" * 64,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(FrameRegistryLoadError, match="frames.jsonl is missing"):
        load_frame_registry(tmp_path)


def test_deterministic_order_across_runs(populated_pack: Path):
    reg1 = load_frame_registry(populated_pack)
    clear_cache()
    reg2 = load_frame_registry(populated_pack)
    assert dict(reg1.by_surface) == dict(reg2.by_surface)
    assert reg1.pack_manifest_sha256 == reg2.pack_manifest_sha256


def test_invalid_polarity_raises(tmp_path: Path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "bad.jsonl").write_text(
        json.dumps(
            {
                "surface_form": "x",
                "frame_category": "y",
                "polarity": "maybe",
                "provenance": "",
                "evidence_hashes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _, sha = compile_frames(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"pack_id": "test", "checksum": "x", "frame_checksum": sha}),
        encoding="utf-8",
    )
    with pytest.raises(FrameRegistryLoadError, match="invalid polarity"):
        load_frame_registry(tmp_path)


def test_conflicting_entries_for_same_surface_raise(tmp_path: Path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "transfer.jsonl").write_text(
        json.dumps(
            {
                "surface_form": "gave",
                "frame_category": "transfer_frame",
                "polarity": "affirms",
                "provenance": "p1",
                "evidence_hashes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (frames_dir / "decrement.jsonl").write_text(
        json.dumps(
            {
                "surface_form": "gave",
                "frame_category": "decrement_frame",
                "polarity": "affirms",
                "provenance": "p2",
                "evidence_hashes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _, sha = compile_frames(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"pack_id": "test", "checksum": "x", "frame_checksum": sha}),
        encoding="utf-8",
    )
    with pytest.raises(FrameRegistryLoadError, match="conflicting entries"):
        load_frame_registry(tmp_path)


def test_cache_returns_same_instance(populated_pack: Path):
    reg1 = load_frame_registry(populated_pack)
    reg2 = load_frame_registry(populated_pack)
    assert reg1 is reg2  # cache hit


def test_compiled_bytes_are_byte_stable(tmp_path: Path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "a.jsonl").write_text(
        json.dumps(
            {
                "surface_form": "gave",
                "frame_category": "transfer_frame",
                "polarity": "affirms",
                "provenance": "p",
                "evidence_hashes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    bytes1, sha1 = compile_frames(tmp_path)
    bytes2, sha2 = compile_frames(tmp_path)
    assert bytes1 == bytes2
    assert sha1 == sha2
