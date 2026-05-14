from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from algebra.cl41 import N_COMPONENTS, geometric_product, reverse as cl_reverse
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
    from alignment.graph import AlignmentGraph
    from morphology.registry import MorphologyRegistry
    from sensorium.protocol import ModalityVocabulary

_ALIGNMENT_NUDGE_STRENGTH: float = 0.10
_MORPHOLOGY_CLUSTER_NUDGE_STRENGTH: float = 0.70
_PRIMARY_SEMANTIC_DOMAIN_WEIGHT: float = 0.55
_LOGOS_PARTICIPATION_WEIGHT: float = 0.25
_FEATURE_COMPONENTS: tuple[int, ...] = (6, 7, 9, 10, 12, 14)


def _hash_to_blade(name: str, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}:{name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:2], "big") % N_COMPONENTS


def _hash_unit(name: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") / 2**32


def _feature_component(name: str, salt: str) -> int:
    return _FEATURE_COMPONENTS[_hash_to_blade(name, f"{salt}:component") % len(_FEATURE_COMPONENTS)]


def _feature_sign(name: str, salt: str) -> float:
    return 1.0 if _hash_unit(name, f"{salt}:sign") >= 0.5 else -1.0


def _feature_rotor(name: str, salt: str, weight: float) -> np.ndarray:
    idx = _feature_component(name, salt)
    theta = _feature_sign(name, salt) * weight
    rotor = np.zeros(N_COMPONENTS, dtype=np.float32)
    rotor[0] = np.cos(theta)
    rotor[idx] = np.sin(theta)
    return rotor


def _unit_feature_versor(vec: np.ndarray) -> np.ndarray:
    versor = unitize_versor(vec)
    if float(versor[0]) < 0.0:
        versor = -versor
    return versor.astype(np.float32, copy=False)


def _blend_feature_versors(source: np.ndarray, target: np.ndarray, strength: float) -> np.ndarray:
    strength = max(0.0, min(1.0, float(strength)))
    nudge = _alignment_nudge_rotor(source, target, strength)
    return _unit_feature_versor(geometric_product(nudge, source))


def _apply_feature(vec: np.ndarray, name: str, salt: str, weight: float) -> np.ndarray:
    return geometric_product(vec, _feature_rotor(name, salt, weight))


def _domain_features(domain: str) -> list[tuple[str, float]]:
    parts = domain.lower().split(".")
    return [(".".join(parts[: depth + 1]), 0.30 / (depth + 1)) for depth in range(len(parts))]


def _has_logos_participation(domains: tuple[str, ...]) -> bool:
    return any(
        domain == "logos.core" or domain.startswith("logos.")
        for domain in (d.lower() for d in domains)
    )


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
    return sorted(inflection.items(), key=lambda item: (priority.get(item[0], len(_INFLECTION_PRIORITY)), item[0]))


def _compact_root(root: str) -> str:
    return root.replace("-", "")


_HEBREW_ROOT_ROMANIZATION = {
    "\u05d0": "A", "\u05d1": "B", "\u05d2": "G", "\u05d3": "D", "\u05d4": "H", "\u05d5": "W",
    "\u05d6": "Z", "\u05d7": "H", "\u05d8": "T", "\u05d9": "Y", "\u05db": "K", "\u05da": "K",
    "\u05dc": "L", "\u05de": "M", "\u05dd": "M", "\u05e0": "N", "\u05df": "N", "\u05e1": "S",
    "\u05e2": "A", "\u05e4": "P", "\u05e3": "P", "\u05e6": "TS", "\u05e5": "TS", "\u05e7": "Q",
    "\u05e8": "R", "\u05e9": "SH", "\u05ea": "T",
}


def _is_hebrew_root(root: str) -> bool:
    return any(ch in _HEBREW_ROOT_ROMANIZATION for ch in root.replace("-", ""))


def _triliteral_root(root: str) -> str:
    parts = [part for part in root.split("-") if part]
    romanized = [_HEBREW_ROOT_ROMANIZATION.get(part, part.upper()) for part in parts]
    return "-".join(romanized) if romanized else _compact_root(root).upper()


def _apply_morphology(vec: np.ndarray, morphology: MorphologyEntry) -> None:
    if morphology.root:
        if _is_hebrew_root(morphology.root):
            vec[:] = _apply_feature(
                vec,
                f"triliteral:{_triliteral_root(morphology.root).lower()}",
                "morph",
                0.30,
            )
        vec[:] = _apply_feature(
            vec,
            f"root:{_compact_root(morphology.root).lower()}",
            "morph",
            0.40,
        )

    for idx, prefix in enumerate(morphology.prefix_chain):
        vec[:] = _apply_feature(vec, f"{idx}:{prefix.lower()}", "morph:prefix", 0.03 / (idx + 1))

    if morphology.stem:
        vec[:] = _apply_feature(vec, morphology.stem.lower(), "morph:stem", 0.24)

    for key, value in _ordered_inflection_items(dict(morphology.inflection)):
        vec[:] = _apply_feature(vec, key.lower(), "morph:infl-role", 0.02)
        vec[:] = _apply_feature(vec, value.lower(), "morph:infl-value", 0.04)

    for idx, suffix in enumerate(morphology.suffix_chain):
        vec[:] = _apply_feature(vec, f"{idx}:{suffix.lower()}", "morph:suffix", 0.02 / (idx + 1))


def _entry_to_coordinate(entry: LexicalEntry, morphology: MorphologyEntry | None = None) -> np.ndarray:
    vec = np.zeros(N_COMPONENTS, dtype=np.float32)
    vec[0] = 1.0

    pos = (entry.pos or entry.part_of_speech or "").lower()
    for domain in entry.semantic_domains:
        for feature, weight in _domain_features(domain):
            vec = _apply_feature(vec, feature, "domain", weight)

    logos_participation = "logos" if _has_logos_participation(entry.semantic_domains) else "nonlogos"
    vec = _apply_feature(
        vec,
        f"logos-participation:{logos_participation}",
        "domain:logos-participation",
        _LOGOS_PARTICIPATION_WEIGHT,
    )

    if entry.semantic_domains:
        vec = _apply_feature(
            vec,
            f"primary:{entry.semantic_domains[0].lower()}",
            "domain:primary",
            _PRIMARY_SEMANTIC_DOMAIN_WEIGHT,
        )

    if pos:
        vec = _apply_feature(vec, pos, "pos", 0.20)

    if morphology is not None:
        _apply_morphology(vec, morphology)

    vec = _apply_feature(vec, entry.lemma.lower(), "lemma", 0.10)
    vec = _apply_feature(vec, entry.surface.lower(), "surface", 0.05)
    return _unit_feature_versor(vec)


def _alignment_nudge_rotor(source: np.ndarray, target: np.ndarray, strength: float) -> np.ndarray:
    R_full = geometric_product(target, cl_reverse(source))
    scalar = max(-1.0, min(1.0, float(R_full[0])))
    theta_full = float(np.arccos(scalar))
    if abs(theta_full) < 1e-6:
        identity = np.zeros(N_COMPONENTS, dtype=np.float32)
        identity[0] = 1.0
        return identity

    biv = R_full.copy()
    biv[0] = 0.0
    biv_norm = float(np.linalg.norm(biv))
    if biv_norm < 1e-6:
        identity = np.zeros(N_COMPONENTS, dtype=np.float32)
        identity[0] = 1.0
        return identity

    theta_nudge = theta_full * max(0.0, min(1.0, float(strength)))
    nudge = np.zeros(N_COMPONENTS, dtype=np.float32)
    nudge[0] = float(np.cos(theta_nudge))
    nudge += (biv / biv_norm * float(np.sin(theta_nudge))).astype(np.float32)
    return nudge


def _resolved_morphology(entry: LexicalEntry, morphology_registry: "MorphologyRegistry | None") -> MorphologyEntry | None:
    if morphology_registry is None or not entry.morphology_id:
        return None
    return morphology_registry.get(entry.morphology_id)


def _morphology_cluster_key(morphology: MorphologyEntry) -> str | None:
    if morphology.root:
        return f"root:{_compact_root(morphology.root).lower()}"
    if morphology.stem:
        return f"stem:{morphology.stem.lower()}"
    return None


def _apply_morphology_cluster_corrections(manifold: VocabManifold, entries: list[LexicalEntry], morphology_registry: "MorphologyRegistry") -> None:
    groups: dict[str, list[tuple[str, MorphologyEntry]]] = {}
    for entry in entries:
        morphology = _resolved_morphology(entry, morphology_registry)
        if morphology is None:
            continue
        key = _morphology_cluster_key(morphology)
        if key is not None:
            groups.setdefault(key, []).append((entry.surface, morphology))

    for members in groups.values():
        if len(members) < 2:
            continue
        prototype_surface = next((surface for surface, morphology in members if surface == morphology.lemma), members[0][0])
        try:
            prototype = manifold.get_versor(prototype_surface)
        except KeyError:
            continue
        for surface, _ in members:
            if surface == prototype_surface:
                continue
            try:
                source = manifold.get_versor(surface)
            except KeyError:
                continue
            manifold.update(surface, _blend_feature_versors(source, prototype, _MORPHOLOGY_CLUSTER_NUDGE_STRENGTH))


def compile_entries_to_manifold(entries: list[LexicalEntry], morphology_registry: "MorphologyRegistry | None" = None) -> tuple[VocabManifold, dict[str, str]]:
    manifold = VocabManifold()
    entry_id_to_surface: dict[str, str] = {}
    for entry in entries:
        morphology = _resolved_morphology(entry, morphology_registry)
        versor = _entry_to_coordinate(entry, morphology)
        manifold.add(entry.surface, versor, morphology=morphology, language=entry.language)
        entry_id_to_surface[entry.entry_id] = entry.surface

    if morphology_registry is not None:
        _apply_morphology_cluster_corrections(manifold, entries, morphology_registry)

    return manifold, entry_id_to_surface


def compile_entries_to_modality_vocab(entries: list[LexicalEntry], morphology_registry: "MorphologyRegistry | None" = None) -> "ModalityVocabulary[str]":
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


def _apply_alignment_corrections(home_manifold: VocabManifold, home_id_map: dict[str, str], foreign_manifold: VocabManifold, foreign_id_map: dict[str, str], pack_id: str) -> None:
    from alignment.graph import load_alignment

    graph = load_alignment(pack_id)
    if len(graph) == 0:
        return

    for edge in graph.aligned_pairs("cross_lang"):
        source_surface = home_id_map.get(edge.source_id)
        target_surface = foreign_id_map.get(edge.target_id)
        if source_surface is None or target_surface is None:
            continue
        try:
            source_v = home_manifold.get_versor(source_surface)
            target_v = foreign_manifold.get_versor(target_surface)
        except KeyError:
            continue
        corrected = _blend_feature_versors(source_v, target_v, edge.weight * _ALIGNMENT_NUDGE_STRENGTH)
        home_manifold.update(source_surface, corrected)


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

    home_manifold, home_id_map = compile_entries_to_manifold(entries, morphology_registry=morphology_registry)

    from alignment.graph import load_alignment
    alignment_graph = load_alignment(pack_id)
    if len(alignment_graph) > 0:
        foreign_pack_ids = _infer_foreign_pack_ids(pack_id, alignment_graph)
        for foreign_pack_id in foreign_pack_ids:
            foreign_pack_dir = Path(__file__).parent / "data" / foreign_pack_id
            if not foreign_pack_dir.exists():
                continue
            foreign_entries = load_pack_entries(foreign_pack_id)
            foreign_morph_registry = None
            if any(e.morphology_id for e in foreign_entries):
                from morphology.registry import load_morphology
                foreign_morph_registry = load_morphology(foreign_pack_id)
            foreign_manifold, foreign_id_map = compile_entries_to_manifold(foreign_entries, morphology_registry=foreign_morph_registry)
            _apply_alignment_corrections(home_manifold, home_id_map, foreign_manifold, foreign_id_map, pack_id)

    return manifest, home_manifold


def load_mounted_packs(pack_ids: tuple[str, ...] | list[str]) -> VocabManifold:
    """
    Mount multiple compiled packs into one exact-search manifold.

    The mounted field is a union of already-compiled Cl(4,1) points. It does
    not add a side index, fallback embedding, or approximate distance path.
    """
    mounted = VocabManifold()
    seen: set[str] = set()
    primary_groups: dict[str, list[tuple[str, str]]] = {}
    for pack_id in pack_ids:
        _, manifold = load_pack(pack_id)
        entries = load_pack_entries(pack_id)
        entry_by_surface = {entry.surface: entry for entry in entries}
        for idx in range(len(manifold)):
            surface = manifold.get_word_at(idx)
            if surface in seen:
                continue
            entry = entry_by_surface.get(surface)
            mounted.add(
                surface,
                manifold.get_versor_at(idx),
                morphology=manifold.morphology_for_word(surface),
                language=None if entry is None else entry.language,
            )
            if entry is not None and entry.semantic_domains:
                primary_groups.setdefault(entry.semantic_domains[0].lower(), []).append(
                    (entry.language, surface)
                )
            seen.add(surface)
    _apply_mounted_primary_domain_resonance(mounted, primary_groups)
    return mounted


def _apply_mounted_primary_domain_resonance(
    mounted: VocabManifold,
    primary_groups: dict[str, list[tuple[str, str]]],
) -> None:
    for surfaces in primary_groups.values():
        languages = {language for language, _ in surfaces}
        if len(languages) < 2:
            continue
        prototype_surface = next(
            (surface for language, surface in surfaces if language == "en"),
            surfaces[0][1],
        )
        prototype = mounted.get_versor(prototype_surface)
        for _, surface in surfaces:
            if surface == prototype_surface:
                continue
            source = mounted.get_versor(surface)
            mounted.update(surface, _blend_feature_versors(source, prototype, 0.85))


def _infer_foreign_pack_ids(home_pack_id: str, graph: "AlignmentGraph") -> list[str]:
    _PREFIX_TO_PACK: dict[str, str] = {
        "he": "he_logos_micro_v1",
        "grc": "grc_logos_micro_v1",
        "en": "en_minimal_v1",
    }
    foreign: set[str] = set()
    for edge in graph.edges:
        prefix = edge.target_id.split("-")[0]
        pack = _PREFIX_TO_PACK.get(prefix)
        if pack and pack != home_pack_id:
            foreign.add(pack)
    return sorted(foreign)


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
