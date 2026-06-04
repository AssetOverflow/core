"""Vision pack loader with fail-closed checksum verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from sensorium.vision.operators import VisionOperatorRegistry, VisionOperatorSpec

_PACKS_ROOT = Path(__file__).resolve().parent


class VisionPackError(ValueError):
    """Raised when a vision pack is missing, malformed, or tampered."""


def _validate_pack_id(pack_id: object) -> str:
    from core._safe_display import safe_pack_id as _disp

    if not isinstance(pack_id, str):
        raise VisionPackError(f"pack_id must be a string, got {_disp(pack_id)!r}")
    if pack_id == "":
        raise VisionPackError("pack_id must not be empty")
    if ".." in pack_id:
        raise VisionPackError(f"pack_id must not contain '..': {_disp(pack_id)!r}")
    if "/" in pack_id or "\\" in pack_id:
        raise VisionPackError(f"pack_id must be a simple pack id, not a path: {_disp(pack_id)!r}")
    if pack_id.startswith("."):
        raise VisionPackError(f"pack_id must not start with '.': {_disp(pack_id)!r}")
    for ch in pack_id:
        if not (ch.isascii() and (ch.isalnum() or ch in {"_", "-"})):
            raise VisionPackError(f"pack_id must be alphanumeric/_/-, got {_disp(pack_id)!r}")
    return pack_id


@dataclass(frozen=True, slots=True)
class LoadedVisionPack:
    pack_id: str
    manifest: dict
    registry: VisionOperatorRegistry


def _verify_checksums(pack_dir: Path) -> None:
    checks_path = pack_dir / "checksums.json"
    if not checks_path.is_file():
        raise VisionPackError(f"checksums.json missing for pack at {pack_dir.name}")
    checks = json.loads(checks_path.read_text())
    for fname, expected in checks.get("files", {}).items():
        fpath = pack_dir / fname
        if not fpath.is_file():
            raise VisionPackError(f"pack file '{fname}' named in checksums.json is missing")
        actual = "sha256:" + hashlib.sha256(fpath.read_bytes()).hexdigest()
        if actual != expected:
            raise VisionPackError(
                f"checksum mismatch for '{fname}': expected {expected}, got {actual}"
            )


def _load_registry(pack_dir: Path, manifest: dict) -> VisionOperatorRegistry:
    specs: dict[str, VisionOperatorSpec] = {}
    for line in (pack_dir / "operators.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        gains = tuple(sorted((k, int(v)) for k, v in row["gain_rules"].items()))
        spec = VisionOperatorSpec(
            operator_id=row["operator_id"],
            event_type=row["event_type"],
            blade_alias=row["blade_alias"],
            blade_index=int(row["blade_index"]),
            base_theta_q=int(row["base_theta_q"]),
            gain_rules=gains,
            theta_clip_q=int(row["theta_clip_q"]),
            version=str(row.get("version", "1")),
        )
        specs[spec.event_type] = spec
    return VisionOperatorRegistry(specs, basis_version=manifest.get("basis_version", "vision-basis-v1"))


def load_vision_pack(
    pack_id: str = "vision_core_v1",
    *,
    packs_root: Path | None = None,
    verify: bool = True,
) -> LoadedVisionPack:
    safe_id = _validate_pack_id(pack_id)
    root = packs_root if packs_root is not None else _PACKS_ROOT
    pack_dir = (root / safe_id).resolve()
    if not str(pack_dir).startswith(str(root.resolve())):
        raise VisionPackError(f"resolved pack path escapes packs root: {safe_id!r}")
    if not pack_dir.is_dir():
        raise VisionPackError(f"no vision pack mounted at {safe_id!r}")
    if verify:
        _verify_checksums(pack_dir)
    manifest = json.loads((pack_dir / "manifest.json").read_text())
    return LoadedVisionPack(safe_id, manifest, _load_registry(pack_dir, manifest))
