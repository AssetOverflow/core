"""Deterministic canonical image formation for vision_core_v1."""

from __future__ import annotations

import numpy as np

from sensorium.vision.checksum import sha256_array, sha256_bytes
from sensorium.vision.types import VisionImage

DEFAULT_SIZE = 32
DEFAULT_TILE_PX = 16
DEFAULT_SCALE_LEVELS = 2


def _to_linear_float_rgb(pixels: np.ndarray) -> np.ndarray:
    arr = np.asarray(pixels)
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    if arr.ndim != 3 or arr.shape[2] not in {3, 4}:
        raise ValueError(f"expected HxWx3/4 image, got shape {arr.shape}")
    arr = arr[:, :, :3]
    if np.issubdtype(arr.dtype, np.integer):
        arr = arr.astype(np.float64) / np.iinfo(arr.dtype).max
        # Pinned sRGB transfer approximation for integer source images.
        arr = np.where(arr <= 0.04045, arr / 12.92, ((arr + 0.055) / 1.055) ** 2.4)
    else:
        arr = arr.astype(np.float64)
        arr = np.clip(arr, 0.0, 1.0)
    return arr


def _resize_bilinear(arr: np.ndarray, size: int) -> np.ndarray:
    h, w, c = arr.shape
    if h == size and w == size:
        return arr.astype(np.float32)
    ys = np.linspace(0.0, h - 1, size, dtype=np.float64)
    xs = np.linspace(0.0, w - 1, size, dtype=np.float64)
    y0 = np.floor(ys).astype(np.int64)
    x0 = np.floor(xs).astype(np.int64)
    y1 = np.minimum(y0 + 1, h - 1)
    x1 = np.minimum(x0 + 1, w - 1)
    wy = (ys - y0)[:, None, None]
    wx = (xs - x0)[None, :, None]
    top = arr[y0[:, None], x0[None, :], :] * (1.0 - wx) + arr[y0[:, None], x1[None, :], :] * wx
    bot = arr[y1[:, None], x0[None, :], :] * (1.0 - wx) + arr[y1[:, None], x1[None, :], :] * wx
    return (top * (1.0 - wy) + bot * wy).astype(np.float32)


def canonicalize_image(
    pixels: np.ndarray,
    *,
    size: int = DEFAULT_SIZE,
    tile_px: int = DEFAULT_TILE_PX,
    scale_levels: int = DEFAULT_SCALE_LEVELS,
) -> VisionImage:
    """Return a canonical fixed-grid VisionImage from an image array."""
    source = np.ascontiguousarray(np.asarray(pixels))
    source_sha256 = sha256_bytes(source.tobytes())
    linear = _to_linear_float_rgb(source)
    canonical = np.ascontiguousarray(_resize_bilinear(linear, size), dtype=np.float32)
    if size % tile_px != 0:
        raise ValueError("canonical size must be divisible by tile_px")
    return VisionImage(
        pixels=canonical,
        grid_h=size // tile_px,
        grid_w=size // tile_px,
        scale_levels=scale_levels,
        tile_px=tile_px,
        source_sha256=source_sha256,
        canonical_sha256=sha256_array(canonical),
    )
