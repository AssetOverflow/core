"""
sensorium/audio/checksum.py — the layered checksum chain (ADR-0181 §2.2, spec §6).

    source_sha256 → canonical_sha256 → token_stream_sha256 → ir_sha256
                  → pack_manifest_sha256 → projection_sha256

Every link is content-addressed. The merge key
(canonical_sha256, ir_sha256, projection_sha256) is derived from these and is
what makes audio deltas idempotent under the Delta-CRDT join (ADR-0181 §2.2).

Hashing arrays uses the *exact bytes that would be written to disk* — the same
discipline CLAUDE.md §Semantic Pack Discipline requires of manifest checksums.
Floats are hashed as canonical float32 bytes so the hash is stable across the
float64 internal compute path (spec §7: cast to float32 only at the boundary).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    """Hash an array by its canonical float32 byte image."""
    return sha256_bytes(np.ascontiguousarray(arr, dtype=np.float32).tobytes())


def sha256_json(obj: Any) -> str:
    """Hash a JSON-serialisable object with sorted keys / stable separators."""
    serialized = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256_bytes(serialized.encode("utf-8"))
