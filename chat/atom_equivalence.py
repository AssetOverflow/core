from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from chat.pack_resolver import resolve_lemma


@dataclass(frozen=True, slots=True)
class AtomEquivalence:
    status: str
    composer_atom_set_hash: str
    graph_atom_set_hash: str
    overlap_count: int


def normalize_atoms(atoms: tuple[str, ...]) -> tuple[str, ...]:
    cleaned = sorted(
        {
            atom.strip()
            for atom in atoms
            if atom and atom.strip() and atom.strip() != "<pending>"
        }
    )
    return tuple(cleaned)


def hash_atoms(atoms: tuple[str, ...]) -> str:
    cleaned = normalize_atoms(atoms)
    if not cleaned:
        return ""
    blob = "\n".join(cleaned).encode("utf-8")
    return sha256(blob).hexdigest()


def atoms_for_graph_nodes(graph) -> tuple[str, ...]:
    atoms: list[str] = []
    for node in getattr(graph, "nodes", ()) or ():
        for surface in (
            getattr(node, "subject", ""),
            getattr(node, "predicate", ""),
            getattr(node, "obj", ""),
        ):
            resolved = resolve_lemma(str(surface))
            if resolved is None:
                continue
            _, domains = resolved
            atoms.extend(domains)
    return normalize_atoms(tuple(atoms))


def compare_atom_sets(
    *,
    composer_atoms: tuple[str, ...],
    graph_atoms: tuple[str, ...],
    graph_unconstrained: bool,
    applicable: bool,
) -> AtomEquivalence:
    composer_norm = normalize_atoms(composer_atoms)
    graph_norm = normalize_atoms(graph_atoms)
    composer_hash = hash_atoms(composer_norm)
    graph_hash = hash_atoms(graph_norm)
    overlap = len(set(composer_norm).intersection(graph_norm))

    if not applicable:
        status = "not_applicable"
    elif not composer_norm:
        status = "composer_no_atoms"
    elif graph_unconstrained or not graph_norm:
        status = "graph_unconstrained"
    elif overlap > 0:
        status = "equivalent"
    else:
        status = "divergent"
    return AtomEquivalence(
        status=status,
        composer_atom_set_hash=composer_hash,
        graph_atom_set_hash=graph_hash,
        overlap_count=overlap,
    )
