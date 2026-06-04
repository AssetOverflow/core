"""Trace-safe hashing for merged sensorium deltas."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from sensorium.compiler.delta import ContentAddressedDelta
from sensorium.compiler.protocol import CompilationUnitLike


def _assert_trace_safe(value: Any, *, path: str) -> None:
    if isinstance(value, (np.ndarray, bytes, bytearray)):
        raise TypeError(f"trace value at {path} is not trace-safe: {type(value).__name__}")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _assert_trace_safe(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for idx, child in enumerate(value):
            _assert_trace_safe(child, path=f"{path}[{idx}]")


def merge_trace_hash(
    merged: ContentAddressedDelta[CompilationUnitLike],
    evidence_trace_fn: Callable[[CompilationUnitLike], dict[str, object]],
) -> str:
    """Hash trace-safe evidence records in canonical merge-key order."""
    payload = []
    for unit in merged.units:
        trace = evidence_trace_fn(unit)
        _assert_trace_safe(trace, path="trace")
        payload.append(trace)
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
