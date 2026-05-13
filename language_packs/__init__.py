"""
language_packs — compiled linguistic manifold schemas.

Language packs are not datasets. They are pinned, checksummed, compiled
linguistic manifolds: surface forms, morphology, grammar attractors,
cross-language resonances, and holonomy resonance proofs.
"""

from .schema import (
    AlignmentEdge,
    GrammarAttractor,
    HolonomyAlignmentCase,
    LanguagePackManifest,
    LanguageRole,
    LexicalEntry,
    MorphologyEntry,
    OOVPolicy,
)

__all__ = [
    "AlignmentEdge",
    "GrammarAttractor",
    "HolonomyAlignmentCase",
    "LanguagePackManifest",
    "LanguageRole",
    "LexicalEntry",
    "MorphologyEntry",
    "OOVPolicy",
]
