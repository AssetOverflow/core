"""
packs/audio/loader.py — audio pack loader (ADR-0181 PR-3).

Trust boundary (CLAUDE.md §Security / ADR-0051):

* The pack id is validated for filesystem safety *before* any path join —
  traversal tokens, separators, and dotfiles fail closed.
* The loader is fail-closed on checksum mismatch: every file named in
  ``checksums.json`` is re-hashed and compared before the pack is observable
  to runtime code. A tampered or stale artifact blocks the load (and therefore
  the mount — bad checksum blocks pack mount, eval-plan §2).
* The loader never mutates a pack on disk.

The pack format is JSON (matching every other CORE pack loader and avoiding a
TOML parser dependency); ADR-0181 spec §6.1 showed TOML illustratively only.
The loaded operator registry is byte-equivalent to the in-code
``DEFAULT_OPERATOR_REGISTRY`` (asserted by tests via ``manifest_sha256``).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sensorium.audio.operators import AudioOperatorRegistry, OperatorSpec

_PACKS_ROOT = Path(__file__).resolve().parent


class AudioPackError(ValueError):
    """Raised when an audio pack is missing, malformed, or fails verification."""


def _validate_pack_id(pack_id: object) -> str:
    """Reject unsafe pack ids before any filesystem access (ADR-0051)."""
    from core._safe_display import safe_pack_id as _disp

    if not isinstance(pack_id, str):
        raise AudioPackError(f"pack_id must be a string, got {_disp(pack_id)!r}")
    if pack_id == "":
        raise AudioPackError("pack_id must not be empty")
    if ".." in pack_id:
        raise AudioPackError(f"pack_id must not contain '..': {_disp(pack_id)!r}")
    if "/" in pack_id or "\\" in pack_id:
        raise AudioPackError(f"pack_id must be a simple pack id, not a path: {_disp(pack_id)!r}")
    if pack_id.startswith("."):
        raise AudioPackError(f"pack_id must not start with '.': {_disp(pack_id)!r}")
    for ch in pack_id:
        if not (ch.isascii() and (ch.isalnum() or ch in {"_", "-"})):
            raise AudioPackError(f"pack_id must be alphanumeric/_/-, got {_disp(pack_id)!r}")
    return pack_id


@dataclass(frozen=True, slots=True)
class LoadedAudioPack:
    pack_id: str
    manifest: dict
    registry: AudioOperatorRegistry
    fir: np.ndarray | None
    fir_sha256: str


def _verify_checksums(pack_dir: Path) -> None:
    """Re-hash every file in checksums.json; fail closed on any mismatch."""
    checks_path = pack_dir / "checksums.json"
    if not checks_path.is_file():
        raise AudioPackError(f"checksums.json missing for pack at {pack_dir.name}")
    checks = json.loads(checks_path.read_text())
    for fname, expected in checks.get("files", {}).items():
        fpath = pack_dir / fname
        if not fpath.is_file():
            raise AudioPackError(f"pack file '{fname}' named in checksums.json is missing")
        actual = "sha256:" + hashlib.sha256(fpath.read_bytes()).hexdigest()
        if actual != expected:
            raise AudioPackError(
                f"checksum mismatch for '{fname}': expected {expected}, got {actual}"
            )


def _load_registry(pack_dir: Path) -> AudioOperatorRegistry:
    specs: dict[str, OperatorSpec] = {}
    for line in (pack_dir / "operators.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        # gain_rules dict -> sorted (name, gain) pairs for stable serialization.
        gains = tuple(sorted((k, int(v)) for k, v in row["gain_rules"].items()))
        spec = OperatorSpec(
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
    return AudioOperatorRegistry(specs)


def load_audio_pack(
    pack_id: str = "audio_core_v1",
    *,
    packs_root: Path | None = None,
    verify: bool = True,
) -> LoadedAudioPack:
    """Load and verify an audio pack from ``packs/audio/<pack_id>/``."""
    safe_id = _validate_pack_id(pack_id)
    root = packs_root if packs_root is not None else _PACKS_ROOT
    pack_dir = (root / safe_id).resolve()
    # Defense in depth: the resolved path must stay under the packs root.
    if not str(pack_dir).startswith(str(root.resolve())):
        raise AudioPackError(f"resolved pack path escapes packs root: {safe_id!r}")
    if not pack_dir.is_dir():
        raise AudioPackError(f"no audio pack mounted at {safe_id!r}")

    if verify:
        _verify_checksums(pack_dir)

    manifest = json.loads((pack_dir / "manifest.json").read_text())
    registry = _load_registry(pack_dir)

    fir_path = pack_dir / manifest.get("resampling", {}).get("fir_path", "resample_fir_v1.npy")
    fir: np.ndarray | None = np.load(fir_path) if fir_path.is_file() else None
    fir_sha256 = (
        "sha256:" + hashlib.sha256(fir_path.read_bytes()).hexdigest()
        if fir_path.is_file() else ""
    )
    return LoadedAudioPack(safe_id, manifest, registry, fir, fir_sha256)
