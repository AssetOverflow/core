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

# Strength of the cross-language alignment nudge applied in load_pack().
# Each aligned pair's source versor is rotated by this fraction of the
# geodesic arc toward the target versor. Small enough to preserve
# intra-pack geometry; large enough to pull cross-lang pairs into proximity.
_ALIGNMENT_NUDGE_STRENGTH: float = 0.06


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


def _canonicalize_versor(vec: np.ndarray) -> np.ndarray:
    """
    Unitize a construction-time coordinate and choose a deterministic rotor
    hemisphere.

    In Cl(4,1), ``R`` and ``-R`` encode the same rotor action. The language
    pack compiler compares entries with scalar/inner-product probes, so
    leaving the double-cover sign arbitrary can make same-root or aligned
    entries appear anti-resonant after otherwise legitimate construction
    changes. Canonicalizing on the scalar component preserves the geometry
    while making resonance comparisons deterministic.
    """
    versor = unitize_versor(vec)
    if float(versor[0]) < 0.0:
        versor = -versor
    return versor.astype(np.float32, copy=False)


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
    "\u05d0": "A",
    "\u05d1": "B",
    "\u05d2": "G",
    "\u05d3": "D",
    "\u05d4": "H",
    "\u05d5": "W",
    "\u05d6": "Z",
    "\u05d7": "H",
    "\u05d8": "T",
    "\u05d9": "Y",
    "\u05db": "K",
    "\u05da": "K",
    "\u05dc": "L",
    "\u05de": "M",
    "\u05dd": "M",
    "\u05e0": "N",
    "\u05df": "N",
    "\u05e1": "S",
    "\u05e2": "A",
    "\u05e4": "P",
    "\u05e3": "P",
    "\u05e6": "TS",
    "\u05e5": "TS",
    "\u05e7": "Q",
    "\u05e8": "R",
    "\u05e9": "SH",
    "\u05ea": "T",
}


def _is_hebrew_root(root: str) -> bool:
    """Return True if the root string contains Hebrew script characters."""
    return any(ch in _HEBREW_ROOT_ROMANIZATION for ch in root.replace("-", ""))


def _triliteral_root(root: str) -> str:
    parts = [part for part in root.split("-") if part]
    romanized = [_HEBREW_ROOT_ROMANIZATION.get(part, part.upper()) for part in parts]
    return "-".join(romanized) if romanized else _compact_root(root).upper()


def _apply_morphology(vec: np.ndarray, morphology: MorphologyEntry) -> np.ndarray:
    # Weight hierarchy:
    #   triliteral root  0.22  — shared abstract identity, strongest anchor
    #   root             0.30  — primary root geometry
    #   stem             0.18  — same-root forms cluster here
    #   inflection role  0.015 — key label, minimal perturbation
    #   inflection value 0.03  — number/gender/etc, perturbation only
    #   prefix           0.03/pos — small positional perturbation
    #   suffix           0.02/pos — smallest, inflectional tail only
    if morphology.root:
        if _is_hebrew_root(morphology.root):
            vec = geometric_product(
                vec,
                _feature_rotor(
                    f"triliteral:{_triliteral_root(morphology.root).lower()}",
                    "morph",
                    0.22,
                ),
            )
        vec = geometric_product(
            vec,
            _feature_rotor(f"root:{_compact_root(morphology.root).lower()}", "morph", 0.30),
        )

    for idx, prefix in enumerate(morphology.prefix_chain):
        weight = 0.03 / (idx + 1)
        vec = geometric_product(
            vec,
            _feature_rotor(f"{idx}:{prefix.lower()}", "morph:prefix", weight),
        )

    if morphology.stem:
        vec = geometric_product(vec, _feature_rotor(morphology.stem.lower(), "morph:stem", 0.18))

    for key, value in _ordered_inflection_items(dict(morphology.inflection)):
        vec = geometric_product(
            vec,
            _feature_rotor(key.lower(), "morph:infl-role", 0.015),
        )
        vec = geometric_product(
            vec,
            _feature_rotor(value.lower(), "morph", 0.03),
        )

    for idx, suffix in enumerate(morphology.suffix_chain):
        weight = 0.02 / (idx + 1)
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
    return _canonicalize_versor(vec)


def _resolved_morphology(
    entry: LexicalEntry,
    morphology_registry: "MorphologyRegistry | None",
) -> MorphologyEntry | None:
    if morphology_registry is None or not entry.morphology_id:
        return None
    return morphology_registry.get(entry.morphology_id)


def _alignment_nudge_rotor(
    source: np.ndarray,
    target: np.ndarray,
    strength: float,
) -> np.ndarray:
    """
    Build a rotor that rotates *source* a fraction *strength* of the way
    toward *target* along the geodesic arc between them.

    Uses the geometric product of target and reverse(source) to find the
    full-arc rotor, then scales the bivector angle by *strength* via slerp.
    Falls back to identity if source and target are anti-parallel (degenerate).
    """
    from algebra.cl41 import reverse as cl_reverse
    R_full = geometric_product(target, cl_reverse(source))

    scalar = float(R_full[0])
    scalar = max(-1.0, min(1.0, scalar))
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

    biv_unit = biv / biv_norm
    theta_nudge = theta_full * strength

    nudge = np.zeros(N_COMPONENTS, dtype=np.float32)
    nudge[0] = float(np.cos(theta_nudge))
    nudge += (biv_unit * float(np.sin(theta_nudge))).astype(np.float32)
    return nudge


def compile_entries_to_manifold(
    entries: list[LexicalEntry],
    morphology_registry: "MorphologyRegistry | None" = None,
) -> tuple[VocabManifold, dict[str, str]]:
    """
    Compile entries into a VocabManifold.

    Returns:
        (manifold, entry_id_to_surface): the compiled manifold and a mapping
        from entry_id to surface string, used by the alignment correction pass
        in load_pack() to resolve AlignmentEdge source/target IDs.
    """
    manifold = VocabManifold()
    entry_id_to_surface: dict[str, str] = {}
    for entry in entries:
        versor = _entry_to_coordinate(entry, _resolved_morphology(entry, morphology_registry))
        manifold.add(entry.surface, versor)
        entry_id_to_surface[entry.entry_id] = entry.surface
    return manifold, entry_id_to_surface


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


def _apply_alignment_corrections(
    home_manifold: VocabManifold,
    home_id_map: dict[str, str],
    foreign_manifold: VocabManifold,
    foreign_id_map: dict[str, str],
    pack_id: str,
) -> None:
    """
    Load alignment edges for *pack_id* and nudge each source versor toward
    its aligned foreign target versor.

    Modifies *home_manifold* in-place via VocabManifold.update().
    Silently skips edges whose source or target cannot be resolved —
    alignment is best-effort; missing entries must not block compilation.
    """
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

        nudge = _alignment_nudge_rotor(source_v, target_v, edge.weight * _ALIGNMENT_NUDGE_STRENGTH)
        corrected = _canonicalize_versor(geometric_product(nudge, source_v))
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

    home_manifold, home_id_map = compile_entries_to_manifold(
        entries, morphology_registry=morphology_registry
    )

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
            foreign_manifold, foreign_id_map = compile_entries_to_manifold(
                foreign_entries, morphology_registry=foreign_morph_registry
            )
            _apply_alignment_corrections(
                home_manifold, home_id_map,
                foreign_manifold, foreign_id_map,
                pack_id,
            )

    return manifest, home_manifold


def _infer_foreign_pack_ids(
    home_pack_id: str,
    graph: "alignment.graph.AlignmentGraph",
) -> list[str]:
    """
    Derive foreign pack_ids from target_id prefixes in the alignment graph.

    Convention: target_id is "<lang_prefix>-NNN" where lang_prefix maps to
    a known pack directory name. Currently supports he <-> grc cross-links.
    """
    from alignment.graph import AlignmentGraph  # noqa: F401  local import to avoid cycle

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
