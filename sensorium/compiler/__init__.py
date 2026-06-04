"""Shared sensorium compiler substrate.

This package contains the modality-neutral law for compiled sensorium deltas:
content-addressed units, canonical semilattice joins, non-draining local
arenas, and trace-safe merge hashing. Modality compilers keep their own clocks,
IRs, lexers, and operator registries.
"""

from sensorium.compiler.arena import LocalArena
from sensorium.compiler.delta import ContentAddressedDelta, merge_deltas
from sensorium.compiler.protocol import CompilationUnitLike, CompilerLike, MergeKey
from sensorium.compiler.trace import merge_trace_hash

__all__ = [
    "CompilationUnitLike",
    "CompilerLike",
    "ContentAddressedDelta",
    "LocalArena",
    "MergeKey",
    "merge_deltas",
    "merge_trace_hash",
]
