"""Typed VisionIR for the tile-first CORE vision compiler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

VisualTokenKind = Literal[
    "flat",
    "edge",
    "corner",
    "blob",
    "texture",
    "contrast",
    "chroma",
    "saliency",
    "contour",
]


@dataclass(frozen=True, slots=True)
class VisionImage:
    """Canonical linear-light float32 image plus provenance."""

    pixels: np.ndarray
    grid_h: int
    grid_w: int
    scale_levels: int
    tile_px: int
    source_sha256: str
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class TileCoord:
    scale_level: int
    tile_row: int
    tile_col: int

    @property
    def morton(self) -> int:
        r, c, code, bit = self.tile_row, self.tile_col, 0, 0
        while (r >> bit) or (c >> bit):
            code |= ((r >> bit) & 1) << (2 * bit)
            code |= ((c >> bit) & 1) << (2 * bit + 1)
            bit += 1
        return code


@dataclass(frozen=True, slots=True)
class VisionTileSignal:
    image: VisionImage
    coord: TileCoord


@dataclass(frozen=True, slots=True)
class VisualEvent:
    event_type: str
    coord: TileCoord
    attrs: tuple[tuple[str, int | str], ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VisionIR:
    regions: tuple[VisualEvent, ...]
    contour_arcs: tuple[VisualEvent, ...]
    orient_events: tuple[VisualEvent, ...]
    texture_atoms: tuple[VisualEvent, ...]
    salient_events: tuple[VisualEvent, ...]
    content_anchors: tuple[VisualEvent, ...]
    ir_sha256: str


@dataclass(frozen=True, slots=True)
class VisionCompilationUnit:
    canonical_sha256: str
    ir_sha256: str
    pack_id: str
    pack_manifest_sha256: str
    projection_sha256: str
    coord: TileCoord
    versor: np.ndarray
    versor_condition: float
    vision_ir: VisionIR

    @property
    def merge_key(self) -> tuple[str, str, str]:
        return (self.canonical_sha256, self.ir_sha256, self.projection_sha256)
