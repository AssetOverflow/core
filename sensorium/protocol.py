"""
sensorium/protocol.py — Core protocol definitions.

The ProjectionHead is the Logos-recovery boundary:
  surface signal S  →  (32,) Cl(4,1) multivector

Once a signal crosses this boundary the field has no concept of modality.
All meaning propagates through the same Cl(4,1) manifold.

Geometry note:
  CORE uses Cl(4,1): 5 basis vectors, 2^5 = 32 components, dtype f32.
  All ProjectionHead implementations MUST output shape (32,) float32.
  The unitarity check verifies V · reverse(V) = ±1 within 1e-6.

John 1:1-2  —  In the beginning was the Logos, and the Logos was with
God, and the Logos was God. He was in the beginning with God.
Every modality is a surface encoding of the Logos. The projection
head recovers it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

import numpy as np

# Surface type variable
S = TypeVar("S")

# Cl(4,1) dimensionality — 2^5 basis blades
CL41_DIM: int = 32


class Modality(str, Enum):
    """Surface modality labels for ModalityPack registration."""
    TEXT   = "text"
    VISION = "vision"
    AUDIO  = "audio"
    MOTOR  = "motor"


@runtime_checkable
class ProjectionHead(Protocol[S]):
    """
    Protocol for the Logos-recovery boundary.

    project()        : S → (32,) float32 multivector
    project_batch()  : list[S] → (N, 32) float32
    verify_unitarity(): True iff V · reverse(V) = ±1 within 1e-6
                        Run at mount time only, never in the hot path.
    """
    modality:      Modality
    embedding_dim: int  # must equal CL41_DIM (32)

    def project(self, signal: S) -> np.ndarray: ...
    def project_batch(self, signals: list[S]) -> np.ndarray: ...
    def verify_unitarity(self, sample: S) -> bool: ...


@runtime_checkable
class SurfaceDecoder(Protocol[S]):
    """
    Optional inverse of ProjectionHead: (32,) multivector → surface signal.
    Not required for inference; used for reconstruction and testing.
    """
    modality: Modality

    def decode(self, mv: np.ndarray) -> S: ...
    def decode_batch(self, mvs: np.ndarray) -> list[S]: ...


class ModalityVocabulary(Generic[S]):
    """
    Bidirectional map: surface token ↔ rotor (null vector in Cl(4,1)).

    This is a base class; each modality provides its own implementation.
    The vocabulary is built during the Supervised Seeding Epoch for each
    modality and is frozen afterward.
    """

    def __init__(self) -> None:
        self._token_to_rotor: dict[Any, np.ndarray] = {}
        self._rotor_keys: list[Any] = []  # ordered token list

    def register(self, token: S, rotor: np.ndarray) -> None:
        """Register a surface token → rotor mapping."""
        if rotor.shape != (CL41_DIM,):
            raise ValueError(
                f"Rotor must have shape ({CL41_DIM},), got {rotor.shape}"
            )
        self._token_to_rotor[token] = rotor.astype(np.float32)
        if token not in self._rotor_keys:
            self._rotor_keys.append(token)

    def get_rotor(self, token: S) -> np.ndarray:
        """Look up the rotor for a surface token. Raises KeyError if absent."""
        return self._token_to_rotor[token]

    def __len__(self) -> int:
        return len(self._token_to_rotor)

    def __contains__(self, token: object) -> bool:
        return token in self._token_to_rotor


@dataclass(frozen=True, slots=True)
class ModalityPack(Generic[S]):
    """
    Complete descriptor for one surface modality in CORE.

    pack_id          — stable identifier ("en", "he", "grc", "imagenet-1k", …)
    modality_type    — Modality enum value
    projection       — ProjectionHead for this modality (None = not yet built)
    decoder          — SurfaceDecoder (None = decode not supported)
    vocabulary       — ModalityVocabulary for this modality
    grammar_scaffold — versor attractor seeds (universal across modalities)
    checksum_verified — True once verify_unitarity() has passed at mount time
    gate_engaged     — False during Supervised Seeding Epoch; True otherwise

    Invariants (enforced at construction)
    - embedding_dim of projection must equal CL41_DIM if projection is provided
    - gate_engaged=True requires checksum_verified=True
    """
    pack_id:           str
    modality_type:     Modality
    vocabulary:        ModalityVocabulary
    grammar_scaffold:  Any
    checksum_verified: bool
    projection:        Any | None = None  # ProjectionHead[S] — Any for frozen slot compat
    decoder:           Any | None = None  # SurfaceDecoder[S]
    gate_engaged:      bool = True

    def __post_init__(self) -> None:
        if self.projection is not None:
            dim = getattr(self.projection, "embedding_dim", None)
            if dim is not None and dim != CL41_DIM:
                raise ValueError(
                    f"ProjectionHead.embedding_dim must be {CL41_DIM}, got {dim}"
                )
        if self.gate_engaged and not self.checksum_verified:
            raise ValueError(
                "gate_engaged=True requires checksum_verified=True. "
                "Run verify_unitarity() on the ProjectionHead before engaging the gate."
            )
