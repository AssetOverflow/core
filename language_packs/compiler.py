from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from algebra.cl41 import N_COMPONENTS, geometric_product
from algebra.versor import unitize_versor
from language_packs.schema import (
    LanguagePackManifest,
    LanguageRole,
    LexicalEntry,
    MorphologyEntry,
    OOVPolicy,
)
from vocab.manifold import VocabManifold

if TYPE_CHECKING:
    from morphology.registry import MorphologyRegistry
    from sensorium.protocol import ModalityVocabulary


def _hash_to_blade(name: str, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}:{name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:2], "big") % N_COMPONENTS


def _hash_unit(name: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") / 2**32


def _feature_rotor(name: str, salt: str, weight: float) -> np.ndarray:
    negative_bivectors = (6, 7, 9, 10, 12, 14)
    idx = negative_bivectors[_hash_to_blade(name, f"{salt}:biv") % len(negative_bivectors)]
    theta = (0.2 + 0.8 * _hash_unit(name, f"{salt}:angle")) * weight
    rotor = np.zeros(N_COMPONENTS, dtype=np.float32)
    rotor[0] = np.cos(theta)
    rotor[idx] = np.sin(theta)
    return rotor


def _domain_features(domain: str) -> list[tuple[str, float]]:
    """
    Lift hierarchical semantic domains into a small feature chain.

    A domain like ``logos.illumination.photon`` contributes the trunk
    (``logos``), then the branch (``logos.illumination``), then the leaf.
    This reduces accidental hash collisions where unrelated surfaces land
    close together despite having disjoint semantic structure.
    """
    parts = domain.lower().split(".")
    return [
        (".".join(parts[: depth + 1]), 0.45 / (depth + 1))
        for depth in range(len(parts))
    ]


_INFLECTION_PRIORITY = (
    "pos",
    "binyan",
    "declension",
    "tense",
    "voice",
    "mood",
    "aspect",
    "person",
    "gender",
    "number",
    "case",
    "state",
)


def _ordered_inflection_items(inflection: dict[str, str]) -> list[tuple[str, str]]:
    priority = {key: idx for idx, key in enumerate(_INFLECTION_PRIORITY)}
    return sorted(
        inflection.items(),
        key=lambda item: (priority.get(item[0], len(_INFLECTION_PRIORITY)), item[0]),
    )


def _compact_root(root: str) -> str:
    return root.replace("-", "")


_HEBREW_ROOT_ROMANIZATION = {
    "א": "A",
    "ב": "B",
    "ג": "G",
    "ד": "D",
    "ה": "H",
    "ו": "W",
    "ז": "Z",
    "ח": "H",
    "ט": "T",
    "י": "Y",
    "כ": "K",
    "ך": "K",
    "ל": "L",
    "מ": "M",
    "ם": "M",
    "נ": "N",
    "ן": "N",
    "ס": "S",
    "ע": "A",
    "פ": "P",
    "ף": "P",
    "צ": "TS",
    "ץ": "TS",
    "ק": "Q",
    "ר": "R",
    "ש": "SH",
    "ת": "T",
}


def _is_hebrew_root(root: str) -> bool:
    """Return True if the root string contains Hebrew script characters."""
    return any(ch in _HEBREW_ROOT_ROMANIZATION for ch in root.replace("-", ""))


def _triliteral_root(root: str) -> str:
    parts = [part for part in root.split("-") if part]
    romanized = [_HEBREW_ROOT_ROMANIZATION.get(part, part.upper()) for part in parts]
    return "-".join(romanized) if romanized else _compact_root(root).upper()


def _apply_morphology(vec: np.ndarray, morphology: MorphologyEntry) -> np.ndarray:
    if morphology.root:
        if _is_hebrew_root(morphology.root):
            vec = geometric_product(
                vec,
                _feature_rotor(
                    f"triliteral:{_triliteral_root(morphology.root).lower()}",
                    "morph",
                    0.13,
                ),
            )
        vec = geometric_product(
            vec,
            _feature_rotor(f"root:{_compact_root(morphology.root).lower()}", "morph", 0.17),
        )

    for idx, prefix in enumerate(morphology.prefix_chain):
        weight = 0.05 / (idx + 1)
        vec = geometric_product(
            vec,
            _feature_rotor(f"{idx}:{prefix.lower()}", "morph:prefix", weight),
        )

    if morphology.stem:
        vec = geometric_product(vec, _feature_rotor(morphology.stem.lower(), "morph:stem", 0.10))

    for key, value in _ordered_inflection_items(dict(morphology.inflection)):
        vec = geometric_product(
            vec,
            _feature_rotor(key.lower(), "morph:infl-role", 0.02),
        )
        vec = geometric_product(
            vec,
            _feature_rotor(value.lower(), "morph", 0.05),
        )

    for idx, suffix in enumerate(morphology.suffix_chain):
        weight = 0.04 / (idx + 1)
        vec = geometric_product(
            vec,
            _feature_rotor(f"{idx}:{suffix.lower()}", "morph:suffix", weight),
        )

    return vec


def _entry_to_coordinate(
    entry: LexicalEntry,
    morphology: MorphologyEntry | None = None,
) -> np.ndarray:
    vec = np.zeros(N_COMPONENTS, dtype=np.float32)
    vec[0] = 1.0

    pos = (entry.pos or entry.part_of_speech or "").lower()
    for domain in entry.semantic_domains:
        for feature, weight in _domain_features(domain):
            vec = geometric_product(vec, _feature_rotor(feature, "domain", weight))

    if pos:
        vec = geometric_product(vec, _feature_rotor(pos, "pos", 0.35))

    if morphology is not None:
        vec = _apply_morphology(vec, morphology)

    vec = geometric_product(vec, _feature_rotor(entry.lemma.lower(), "lemma", 0.1))
    vec = geometric_product(vec, _feature_rotor(entry.surface.lower(), "surface", 0.05))
    return unitize_versor(vec)


def _resolved_morphology(
    entry: LexicalEntry,
    morphology_registry: "MorphologyRegistry | None",
) -> MorphologyEntry | None:
    if morphology_registry is None or not entry.morphology_id:
        return None
    return morphology_registry.get(entry.morphology_id)


def compile_entries_to_manifold(
    entries: list[LexicalEntry],
    morphology_registry: "MorphologyRegistry | None" = None,
) -> VocabManifold:
    manifold = VocabManifold()
    for entry in entries:
        versor = _entry_to_coordinate(entry, _resolved_morphology(entry, morphology_registry))
        manifold.add(entry.surface, versor)
    return manifold


def compile_entries_to_modality_vocab(
    entries: list[LexicalEntry],
    morphology_registry: "MorphologyRegistry | None" = None,
) -> "ModalityVocabulary[str]":
    from sensorium.protocol import ModalityVocabulary

    vocab: ModalityVocabulary[str] = ModalityVocabulary()
    for entry in entries:
        point = _entry_to_coordinate(entry, _resolved_morphology(entry, morphology_registry))
        vocab.register_point(entry.surface, point)
    return vocab


def _parse_entry(payload: dict) -> LexicalEntry:
    return LexicalEntry(
        entry_id=payload["entry_id"],
        surface=payload["surface"],
        lemma=payload.get("lemma", payload["surface"]),
        language=payload["language"],
        part_of_speech=payload.get("part_of_speech"),
        pos=payload.get("pos"),
        morphology_id=payload.get("morphology_id"),
        morphology_tags=tuple(payload.get("morphology_tags", [])),
        semantic_domains=tuple(payload.get("semantic_domains", [])),
        manifold_point_checksum=payload.get("manifold_point_checksum"),
        provenance_ids=tuple(payload.get("provenance_ids", [])),
    )


def load_pack(pack_id: str) -> tuple[LanguagePackManifest, VocabManifold]:
    pack_dir = Path(__file__).parent / "data" / pack_id
    manifest_path = pack_dir / "manifest.json"
    lexicon_path = pack_dir / "lexicon.jsonl"

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    lexicon_bytes = lexicon_path.read_bytes()
    checksum = hashlib.sha256(lexicon_bytes).hexdigest()
    if checksum != manifest_payload["checksum"]:
        raise ValueError(f"Checksum mismatch for {pack_id}: {checksum} != {manifest_payload['checksum']}")

    entries = load_pack_entries(pack_id)
    morphology_registry = None
    if any(entry.morphology_id for entry in entries):
        from morphology.registry import load_morphology

        morphology_registry = load_morphology(pack_id)

    manifest = LanguagePackManifest(
        pack_id=manifest_payload["pack_id"],
        language=manifest_payload["language"],
        role=LanguageRole(manifest_payload["role"]),
        script=manifest_payload["script"],
        normalization_policy=manifest_payload["normalization_policy"],
        source_manifest=manifest_payload["source_manifest"],
        determinism_class=manifest_payload["determinism_class"],
        checksum=manifest_payload["checksum"],
        version=manifest_payload.get("version", "1.0.0"),
        gate_engaged=manifest_payload.get("gate_engaged", False),
        oov_policy=OOVPolicy(manifest_payload.get("oov_policy", OOVPolicy.FAIL_CLOSED.value)),
    )
    return manifest, compile_entries_to_manifold(entries, morphology_registry=morphology_registry)


def load_pack_entries(pack_id: str) -> list[LexicalEntry]:
    pack_dir = Path(__file__).parent / "data" / pack_id
    lexicon_path = pack_dir / "lexicon.jsonl"
    entries: list[LexicalEntry] = []
    for line in lexicon_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(_parse_entry(json.loads(line)))
    _validate_morphology_links(pack_id, entries)
    return entries


def _validate_morphology_links(pack_id: str, entries: list[LexicalEntry]) -> None:
    morphology_ids = [entry.morphology_id for entry in entries if entry.morphology_id]
    if not morphology_ids:
        return

    from morphology.registry import load_morphology

    registry = load_morphology(pack_id)
    missing = [morphology_id for morphology_id in morphology_ids if registry.get(morphology_id) is None]
    if missing:
        raise ValueError(f"{pack_id}: dangling morphology_id link(s): {', '.join(missing)}")
