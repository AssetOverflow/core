from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from algebra.cl41 import N_COMPONENTS, geometric_product
from algebra.versor import unitize_versor
from language_packs.schema import LanguagePackManifest, LanguageRole, LexicalEntry, OOVPolicy
from vocab.manifold import VocabManifold

if TYPE_CHECKING:
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


def _entry_to_coordinate(entry: LexicalEntry) -> np.ndarray:
    vec = np.zeros(N_COMPONENTS, dtype=np.float32)
    vec[0] = 1.0

    pos = (entry.pos or entry.part_of_speech or "").lower()
    for domain in entry.semantic_domains:
        vec = geometric_product(vec, _feature_rotor(domain.lower(), "domain", 0.7))

    if pos:
        vec = geometric_product(vec, _feature_rotor(pos, "pos", 0.35))

    for tag in entry.morphology_tags:
        vec = geometric_product(vec, _feature_rotor(tag.lower(), "morph", 0.15))

    vec = geometric_product(vec, _feature_rotor(entry.lemma.lower(), "lemma", 0.1))
    vec = geometric_product(vec, _feature_rotor(entry.surface.lower(), "surface", 0.05))
    return unitize_versor(vec)


def compile_entries_to_manifold(entries: list[LexicalEntry]) -> VocabManifold:
    manifold = VocabManifold()
    for entry in entries:
        versor = _entry_to_coordinate(entry)
        manifold.add(entry.surface, versor)
    return manifold


def compile_entries_to_modality_vocab(entries: list[LexicalEntry]) -> "ModalityVocabulary[str]":
    from sensorium.protocol import ModalityVocabulary

    vocab: ModalityVocabulary[str] = ModalityVocabulary()
    for entry in entries:
        point = _entry_to_coordinate(entry)
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
    return manifest, compile_entries_to_manifold(entries)


def load_pack_entries(pack_id: str) -> list[LexicalEntry]:
    pack_dir = Path(__file__).parent / "data" / pack_id
    lexicon_path = pack_dir / "lexicon.jsonl"
    entries: list[LexicalEntry] = []
    for line in lexicon_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(_parse_entry(json.loads(line)))
    return entries
