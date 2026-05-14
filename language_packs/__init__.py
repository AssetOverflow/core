"""
language_packs — compiled linguistic manifold schemas.

Language packs are not datasets. They are pinned, checksummed, compiled
linguistic manifolds: surface forms, morphology, grammar attractors,
cross-language resonances, and holonomy resonance proofs.
"""

from pathlib import Path

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

_DATA_DIR = Path(__file__).parent / "data"


def list_packs() -> list[str]:
    """Return available compiled language-pack ids."""
    if not _DATA_DIR.exists():
        return []
    return sorted(
        path.name
        for path in _DATA_DIR.iterdir()
        if path.is_dir()
        and (path / "manifest.json").exists()
        and (path / "lexicon.jsonl").exists()
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
    "list_packs",
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
