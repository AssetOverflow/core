"""Canonical serialization for CORE Trace Protocol v0.

The canonical layer is intentionally small and dependency-free.  It rejects
non-deterministic numeric values, normalizes ``-0.0`` to ``0.0``, sorts object
keys, and emits UTF-8 JSON bytes with compact separators.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

_HASH_PREFIX = "sha256:"


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented canonically."""


def _canonical_float(value: float) -> float:
    if not math.isfinite(value):
        raise CanonicalizationError("CTP canonical JSON forbids NaN and Infinity")
    if value == 0.0:
        return 0.0
    return float(value)


def canonicalize(value: Any) -> Any:
    """Return a JSON-compatible canonical structure.

    Supported leaves are ``None``, ``bool``, ``str``, ``int`` and finite
    ``float``.  Mappings are sorted during serialization; values are
    recursively canonicalized.  Dataclasses are converted through
    ``dataclasses.asdict``.
    """
    if is_dataclass(value):
        return canonicalize(asdict(value))
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return _canonical_float(value)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("CTP object keys must be strings")
            out[key] = canonicalize(item)
        return out
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [canonicalize(item) for item in value]
    raise CanonicalizationError(f"Unsupported CTP value type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Serialize *value* to canonical UTF-8 JSON bytes."""
    normalized = canonicalize(value)
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return encoded.encode("utf-8")


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 content address for *value*."""
    digest = hashlib.sha256(canonical_bytes(value)).hexdigest()
    return f"{_HASH_PREFIX}{digest}"
