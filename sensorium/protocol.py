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

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

import numpy as np

from language_packs.schema import LanguageRole, OOVPolicy

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


@dataclass(frozen=True, slots=True)
class AuthorityToken:
    """Capability-scoped authority for efferent decode paths."""

    principal_id: str
    capabilities: tuple[str, ...]
    issued_at_revision: str

    @property
    def authority_sha256(self) -> str:
        payload = {
            "principal_id": self.principal_id,
            "capabilities": list(self.capabilities),
            "issued_at_revision": self.issued_at_revision,
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True, slots=True)
class EfferentVerdict:
    """Runtime admissibility verdict for an efferent decode."""

    admitted: bool
    reason: str
    authority_sha256: str
    policy_sha256: str


@runtime_checkable
class EfferentGate(Protocol):
    """Runtime gate for output actions. Runs before SurfaceDecoder.decode."""

    def admit(
        self,
        pack_id: str,
        mv: np.ndarray,
        authority: AuthorityToken,
    ) -> EfferentVerdict: ...


class EfferentRefusal(RuntimeError):
    """Raised when an efferent decode is refused before surface emission."""

    def __init__(self, pack_id: str, verdict: EfferentVerdict) -> None:
        self.pack_id = pack_id
        self.verdict = verdict
        super().__init__(f"efferent decode refused for '{pack_id}': {verdict.reason}")


class ModalityVocabulary(Generic[S]):
    """
    Bidirectional map: surface token ↔ manifold multivector.

    Vocabulary entries are positions/points in the field, not transition
    rotors. Operators are constructed separately by the algebra layer.
    Legacy get_rotor/register names remain as compatibility aliases while
    new code should use get_point/register_point.
    """

    def __init__(self) -> None:
        self._token_to_point: dict[Any, np.ndarray] = {}
        self._point_keys: list[Any] = []  # ordered token list
        # Compatibility aliases for older tests/callers.
        self._token_to_rotor = self._token_to_point
        self._rotor_keys = self._point_keys

    def register_point(self, token: S, point: np.ndarray) -> None:
        """Register a surface token → manifold point mapping."""
        if point.shape != (CL41_DIM,):
            raise ValueError(
                f"Manifold point must have shape ({CL41_DIM},), got {point.shape}"
            )
        self._token_to_point[token] = point.astype(np.float32)
        if token not in self._point_keys:
            self._point_keys.append(token)

    def get_point(self, token: S) -> np.ndarray:
        """Look up the manifold point for a surface token."""
        return self._token_to_point[token]

    # Compatibility aliases. Prefer register_point/get_point in new code.
    def register(self, token: S, rotor: np.ndarray) -> None:
        """Compatibility alias for register_point()."""
        self.register_point(token, rotor)

    def get_rotor(self, token: S) -> np.ndarray:
        """Compatibility alias for get_point()."""
        return self.get_point(token)

    def __len__(self) -> int:
        return len(self._token_to_point)

    def __contains__(self, token: object) -> bool:
        return token in self._token_to_point


@dataclass(frozen=True, slots=True)
class ModalityPack(Generic[S]):
    """
    Complete descriptor for one surface modality in CORE.

    pack_id          — stable identifier ("en", "he", "grc", "imagenet-1k", …)
    modality_type    — Modality enum value
    language_role    — role in CORE-Logos (English articulation, Hebrew root depth, etc.)
    oov_policy       — unknown-token behavior; depth packs fail closed by default
    projection       — ProjectionHead for this modality (None = not yet built)
    decoder          — SurfaceDecoder (None = decode not supported)
    vocabulary       — ModalityVocabulary for this modality
    grammar_scaffold — versor attractor seeds (universal across modalities)
    checksum_verified — True once verify_unitarity() has passed at mount time
    gate_engaged     — False during Supervised Seeding Epoch; True otherwise

    Invariants (enforced at construction)
    - embedding_dim of projection must equal CL41_DIM if projection is provided
    - gate_engaged=True requires checksum_verified=True
    - engaged depth packs must fail closed on OOV so unknown Hebrew/Greek forms
      never collapse to a shared fallback point
    """
    pack_id:           str
    modality_type:     Modality
    vocabulary:        ModalityVocabulary
    grammar_scaffold:  Any
    checksum_verified: bool
    projection:        Any | None = None  # ProjectionHead[S] — Any for frozen slot compat
    decoder:           Any | None = None  # SurfaceDecoder[S]
    gate_engaged:      bool = True
    language_role:     LanguageRole | None = None
    oov_policy:        OOVPolicy = OOVPolicy.TAGGED_FALLBACK

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
        if (
            self.gate_engaged
            and self.language_role in {LanguageRole.DEPTH_ROOT, LanguageRole.DEPTH_RELATION}
            and self.oov_policy is not OOVPolicy.FAIL_CLOSED
        ):
            raise ValueError(
                "Engaged depth language packs must use OOVPolicy.FAIL_CLOSED. "
                "Unknown Hebrew/Greek surfaces must not collapse to a fallback point."
            )
