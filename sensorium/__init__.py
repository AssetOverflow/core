"""
sensorium — Modality protocol layer.

Every surface signal (text, vision, audio, motor) is converted to a
(32,) Cl(4,1) multivector by a ProjectionHead before it reaches
core_ingest/ or ingest/gate.py. The gate is never modified.

The ProjectionHead is the Logos-recovery boundary for its modality:
all inputs reduce to words in the versor manifold. There is no
multimodal fusion problem because every modality becomes a versor
before the field sees it. One space.

Adding a modality requires:
  1. One file in sensorium/adapters/<modality>.py
  2. A registry entry in sensorium/registry.py
  3. Nothing else — no existing layer is touched.
"""

from sensorium.protocol import (
    Modality,
    ProjectionHead,
    SurfaceDecoder,
    ModalityVocabulary,
    ModalityPack,
)
from sensorium.registry import ModalityRegistry

__all__ = [
    "Modality",
    "ProjectionHead",
    "SurfaceDecoder",
    "ModalityVocabulary",
    "ModalityPack",
    "ModalityRegistry",
]
