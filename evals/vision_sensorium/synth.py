"""Deterministic synthetic image fixtures for vision_core_v1."""

from __future__ import annotations

import numpy as np

SIZE = 32


def _flat(rgb: list[float], size: int) -> np.ndarray:
    out = np.zeros((size, size, 3), dtype=np.float32)
    out[:, :, :] = np.asarray(rgb, dtype=np.float32)
    return out


def synthesize(spec: dict) -> np.ndarray:
    """Return a float32 RGB image for a fixture spec."""
    size = int(spec.get("size", SIZE))
    kind = spec["kind"]
    if kind == "flat":
        return _flat(list(spec.get("rgb", [0.5, 0.5, 0.5])), size)
    if kind == "edge":
        out = _flat([0.15, 0.15, 0.15], size)
        if spec.get("orientation") == "horizontal":
            out[size // 2:, :, :] = 0.9
        else:
            out[:, size // 2:, :] = 0.9
        return out
    if kind == "corner":
        out = _flat([0.1, 0.1, 0.1], size)
        out[4:16, 4:7, :] = 0.95
        out[4:7, 4:16, :] = 0.95
        out[11:16, 11:16, :] = 0.75
        return out
    if kind == "blob":
        out = _flat([0.2, 0.2, 0.2], size)
        yy, xx = np.mgrid[:size, :size]
        mask = (xx - size / 2) ** 2 + (yy - size / 2) ** 2 <= (size / 5) ** 2
        out[mask, :] = 0.95
        return out.astype(np.float32)
    if kind == "checker":
        period = int(spec.get("period", 4))
        yy, xx = np.mgrid[:size, :size]
        mask = ((xx // period) + (yy // period)) % 2
        out = np.repeat(mask[:, :, None].astype(np.float32), 3, axis=2)
        return out
    if kind == "ramp":
        x = np.linspace(0.0, 1.0, size, dtype=np.float32)
        ramp = np.repeat(x[None, :, None], size, axis=0)
        return np.repeat(ramp, 3, axis=2)
    if kind == "chroma_split":
        out = _flat([0.1, 0.1, 0.8], size)
        out[:, size // 2:, :] = np.asarray([0.9, 0.15, 0.1], dtype=np.float32)
        return out
    if kind == "salient_spot":
        out = _flat([0.45, 0.45, 0.45], size)
        out[size // 2 - 3:size // 2 + 3, size // 2 - 3:size // 2 + 3, :] = 1.0
        return out
    if kind == "contour_box":
        out = _flat([0.2, 0.2, 0.2], size)
        out[7:25, 7:11, :] = 1.0
        out[7:25, 21:25, :] = 1.0
        out[7:11, 7:25, :] = 1.0
        out[21:25, 7:25, :] = 1.0
        return out
    raise ValueError(f"unknown vision fixture kind: {kind!r}")
