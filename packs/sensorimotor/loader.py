"""Sensorimotor pack loader with fail-closed checksum verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from sensorium.audio.checksum import sha256_json

_PACKS_ROOT = Path(__file__).resolve().parent


class SensorimotorPackError(ValueError):
    """Raised when a sensorimotor pack is missing, malformed, or tampered."""


def _validate_pack_id(pack_id: object) -> str:
    from core._safe_display import safe_pack_id as _disp

    if not isinstance(pack_id, str):
        raise SensorimotorPackError(f"pack_id must be a string, got {_disp(pack_id)!r}")
    if pack_id == "":
        raise SensorimotorPackError("pack_id must not be empty")
    if ".." in pack_id:
        raise SensorimotorPackError(f"pack_id must not contain '..': {_disp(pack_id)!r}")
    if "/" in pack_id or "\\" in pack_id:
        raise SensorimotorPackError(f"pack_id must be a simple pack id, not a path: {_disp(pack_id)!r}")
    if pack_id.startswith("."):
        raise SensorimotorPackError(f"pack_id must not start with '.': {_disp(pack_id)!r}")
    for ch in pack_id:
        if not (ch.isascii() and (ch.isalnum() or ch in {"_", "-"})):
            raise SensorimotorPackError(f"pack_id must be alphanumeric/_/-, got {_disp(pack_id)!r}")
    return pack_id


@dataclass(frozen=True, slots=True)
class LoadedSensorimotorPack:
    pack_id: str
    manifest: dict
    manifest_sha256: str
    basis_map: dict


def _verify_checksums(pack_dir: Path) -> None:
    checks_path = pack_dir / "checksums.json"
    if not checks_path.is_file():
        raise SensorimotorPackError(f"checksums.json missing for pack at {pack_dir.name}")
    checks = json.loads(checks_path.read_text())
    for fname, expected in checks.get("files", {}).items():
        fpath = pack_dir / fname
        if not fpath.is_file():
            raise SensorimotorPackError(f"pack file '{fname}' named in checksums.json is missing")
        actual = "sha256:" + hashlib.sha256(fpath.read_bytes()).hexdigest()
        if actual != expected:
            raise SensorimotorPackError(
                f"checksum mismatch for '{fname}': expected {expected}, got {actual}"
            )


def load_sensorimotor_pack(
    pack_id: str = "sensorimotor_core_v1",
    *,
    packs_root: Path | None = None,
    verify: bool = True,
) -> LoadedSensorimotorPack:
    safe_id = _validate_pack_id(pack_id)
    root = packs_root if packs_root is not None else _PACKS_ROOT
    pack_dir = (root / safe_id).resolve()
    if not str(pack_dir).startswith(str(root.resolve())):
        raise SensorimotorPackError(f"resolved pack path escapes packs root: {safe_id!r}")
    if not pack_dir.is_dir():
        raise SensorimotorPackError(f"no sensorimotor pack mounted at {safe_id!r}")
    if verify:
        _verify_checksums(pack_dir)

    manifest = json.loads((pack_dir / "manifest.json").read_text())
    basis_map = json.loads((pack_dir / "basis_map.json").read_text())
    manifest_sha256 = sha256_json({
        "pack_id": safe_id,
        "basis_version": manifest.get("basis_version", "sensorimotor-basis-v1"),
        "events": list(manifest.get("event_order", ())),
    })
    return LoadedSensorimotorPack(safe_id, manifest, manifest_sha256, basis_map)
