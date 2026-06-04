"""Shared protocols for deterministic sensorium compilers."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

import numpy as np

MergeKey = tuple[str, str, str]
S = TypeVar("S")
IR = TypeVar("IR")
U = TypeVar("U", bound="CompilationUnitLike")


@runtime_checkable
class CompilationUnitLike(Protocol):
    """Content-addressed unit emitted by a modality compiler.

    The protocol intentionally captures only the common CRDT/checksum law. The
    modality-specific IR field remains outside this contract.
    """

    canonical_sha256: str
    ir_sha256: str
    pack_id: str
    pack_manifest_sha256: str
    projection_sha256: str
    versor: np.ndarray
    versor_condition: float

    @property
    def merge_key(self) -> MergeKey: ...


@runtime_checkable
class CompilerLike(Protocol[S, IR, U]):
    """Minimal compiler shape shared by audio and vision."""

    def compile_signal(self, signal: S) -> U: ...
    def compile_ir(self, ir: IR) -> U: ...
