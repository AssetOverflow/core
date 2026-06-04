"""Measured-fact visual lexer."""

from __future__ import annotations

import numpy as np

from sensorium.vision.grid import tile_bounds
from sensorium.vision.types import VisualEvent, VisionTileSignal


def _bin(value: float, *, max_value: float, bins: int = 16) -> int:
    if max_value <= 0:
        return 0
    q = int(round((max(0.0, min(value, max_value)) / max_value) * (bins - 1)))
    return max(0, min(bins - 1, q))


def lex_tile(signal: VisionTileSignal) -> tuple[VisualEvent, ...]:
    """Emit deterministic measured events for one tile."""
    image = signal.image
    coord = signal.coord
    r0, r1, c0, c1 = tile_bounds(image, coord)
    tile = image.pixels[r0:r1, c0:c1, :]
    luma = 0.2126 * tile[:, :, 0] + 0.7152 * tile[:, :, 1] + 0.0722 * tile[:, :, 2]
    mean = float(np.mean(luma))
    std = float(np.std(luma))
    contrast_q = _bin(std, max_value=0.5)
    salience_q = _bin(abs(mean - 0.5) + std, max_value=1.0)
    chroma = tile - np.mean(tile, axis=2, keepdims=True)
    chroma_q = _bin(float(np.mean(np.abs(chroma))), max_value=0.5)
    gy, gx = np.gradient(luma.astype(np.float64))
    energy = np.sqrt(gx * gx + gy * gy)
    energy_mean = float(np.mean(energy))
    orient_q = 0
    if energy_mean > 1e-9:
        angle = float(np.arctan2(np.mean(gy), np.mean(gx)) + np.pi)
        orient_q = int(np.floor((angle / (2.0 * np.pi)) * 16.0)) % 16
    edge_q = _bin(energy_mean, max_value=0.5)
    corner_q = _bin(float(np.mean(np.abs(gx * gy))), max_value=0.02)
    center = luma[luma.shape[0] // 4: 3 * luma.shape[0] // 4, luma.shape[1] // 4: 3 * luma.shape[1] // 4]
    blob_q = _bin(abs(float(np.mean(center)) - mean), max_value=0.5)
    texture_q = _bin(float(np.mean(np.abs(energy - energy_mean))), max_value=0.5)
    closure_q = _bin(edge_q + corner_q, max_value=30.0)

    events = [
        VisualEvent("region.flat" if contrast_q <= 1 else "region.contrast", coord, (("contrast_q", contrast_q),), ()),
        VisualEvent("orient.edge_energy", coord, (("orient_q", orient_q), ("energy_q", edge_q)), ()),
        VisualEvent("texture.regularity", coord, (("texture_q", texture_q),), ()),
        VisualEvent("salient.figure_ground", coord, (("salience_q", salience_q),), ()),
        VisualEvent("region.chroma", coord, (("chroma_q", chroma_q),), ()),
    ]
    if corner_q > 0:
        events.append(VisualEvent("region.corner", coord, (("corner_q", corner_q),), ()))
    if blob_q > 0:
        events.append(VisualEvent("region.blob", coord, (("blob_q", blob_q),), ()))
    if closure_q > 0:
        events.append(VisualEvent("contour.closure", coord, (("closure_q", closure_q),), ()))
    return tuple(events)
