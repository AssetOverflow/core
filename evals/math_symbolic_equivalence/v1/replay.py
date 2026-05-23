"""Replay helpers for the ADR-0131.1 symbolic-equivalence lane."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Return stable JSON bytes for digesting lane artifacts."""
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_obj(obj: Any) -> str:
    """Return SHA-256 over stable JSON serialization."""
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()
