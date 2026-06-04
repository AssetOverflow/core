"""Tile-grid helpers for tile-first vision compilation."""

from __future__ import annotations

from sensorium.vision.types import TileCoord, VisionImage, VisionTileSignal


def scale_grid(image: VisionImage, scale_level: int) -> tuple[int, int]:
    if scale_level < 0 or scale_level >= image.scale_levels:
        raise ValueError(f"scale_level out of range: {scale_level}")
    divisor = 2 ** scale_level
    return max(1, image.grid_h // divisor), max(1, image.grid_w // divisor)


def tile_bounds(image: VisionImage, coord: TileCoord) -> tuple[int, int, int, int]:
    rows, cols = scale_grid(image, coord.scale_level)
    if not (0 <= coord.tile_row < rows and 0 <= coord.tile_col < cols):
        raise ValueError(f"tile coord out of range: {coord}")
    h, w = image.pixels.shape[:2]
    r0 = coord.tile_row * h // rows
    r1 = (coord.tile_row + 1) * h // rows
    c0 = coord.tile_col * w // cols
    c1 = (coord.tile_col + 1) * w // cols
    return r0, r1, c0, c1


def iter_tile_signals(image: VisionImage) -> tuple[VisionTileSignal, ...]:
    out: list[VisionTileSignal] = []
    for scale_level in range(image.scale_levels):
        rows, cols = scale_grid(image, scale_level)
        for tile_row in range(rows):
            for tile_col in range(cols):
                out.append(VisionTileSignal(image, TileCoord(scale_level, tile_row, tile_col)))
    return tuple(out)
