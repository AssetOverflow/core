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


def __getattr__(name: str):
    if name in {
        "compile_entries_to_manifold",
        "compile_entries_to_modality_vocab",
        "load_mounted_packs",
        "load_pack",
        "load_pack_entries",
    }:
        from .compiler import (
            compile_entries_to_manifold,
            compile_entries_to_modality_vocab,
            load_mounted_packs,
            load_pack,
            load_pack_entries,
        )

        return {
            "compile_entries_to_manifold": compile_entries_to_manifold,
            "compile_entries_to_modality_vocab": compile_entries_to_modality_vocab,
            "load_mounted_packs": load_mounted_packs,
            "load_pack": load_pack,
            "load_pack_entries": load_pack_entries,
        }[name]
    raise AttributeError(name)
