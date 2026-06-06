"""Bit-exact (de)serialization of numpy arrays for deterministic persistence.

A numpy array encodes to ``{"dtype", "shape", "b64"}`` where ``b64`` is base64 of
the array's raw bytes. This is **bit-exact**: every float round-trips with zero
precision loss, so a restored versor keeps ``versor_condition < 1e-6`` and a
replayed turn keeps its ``trace_hash``.

NEVER serialize field arrays as decimal/JSON floats. Decimal truncates the
mantissa and silently breaks both closure and deterministic replay — the Cl(4,1)
float-truncation pitfall. ``dtype`` carries byte order (``'<f4'``/``'<f8'``), so
the encoding is portable, and ``float32`` is never conflated with ``float64``.

This module is a leaf: it imports only numpy + base64, so every layer (field,
vault, session, engine_state) can use it without an import cycle.

Zig-codec follow-up (tagged — NOT authorized).  This bit-exact codec is the natural
locked **reference contract** (ADR-0196 decision rule 1) for a future Ring-1 Zig
byte-exact serialization component: deterministic buffer ownership, stable layout, and
edge-native build are exactly Zig's profile.  It is gated behind the G0–G8 ladder and
is **only** worth proposing AFTER (1) persistence becomes incremental/append-only
(O(Δ)/turn — the algorithmic fix, in Python), and (2) the edge-budget gate
(``evals/edge_budget/``) proves the bounded per-turn codec is still the device
bottleneck.  A Zig rewrite of today's O(n) snapshot would only speed up the wrong
asymptotics.  See ``evals/edge_budget/contract.md``.
"""

from __future__ import annotations

import base64
from typing import Any

import numpy as np


def encode_array(arr: np.ndarray) -> dict[str, Any]:
    """Encode a numpy array to a bit-exact, JSON-safe dict."""
    contiguous = np.ascontiguousarray(arr)
    return {
        "dtype": contiguous.dtype.str,  # byte-order-aware, e.g. '<f4', '<f8', '<i4'
        "shape": list(contiguous.shape),
        "b64": base64.b64encode(contiguous.tobytes()).decode("ascii"),
    }


def decode_array(payload: dict[str, Any]) -> np.ndarray:
    """Decode a payload produced by ``encode_array`` back to an exact array.

    Returns a writable copy (``np.frombuffer`` is read-only) so the restored
    array can be composed and mutated like a freshly-built one.
    """
    dtype = np.dtype(payload["dtype"])
    raw = base64.b64decode(payload["b64"])
    flat = np.frombuffer(raw, dtype=dtype)
    return flat.reshape(payload["shape"]).copy()


def encode_optional_array(arr: np.ndarray | None) -> dict[str, Any] | None:
    """Encode an array, or return ``None`` for ``None`` (e.g. optional holonomy)."""
    return None if arr is None else encode_array(arr)


def decode_optional_array(payload: dict[str, Any] | None) -> np.ndarray | None:
    """Decode an optional-array payload, or return ``None`` for ``None``."""
    return None if payload is None else decode_array(payload)
