"""
The single injection gate.

The ONLY point where raw data enters the versor manifold.
normalize_to_versor() is called here and nowhere else in production code.

Normalization doctrine (three-tier):

  unitize_versor()       algebra/versor.py — construction primitive.
                         Allowed in: algebra/, persona/, vocab/ (pre-add).
                         Purpose: build valid rotors/motors/manifold entries.

  inject()               THIS function — gate operation, once per raw input.
                         Calls normalize_to_versor() internally at the
                         holonomy-to-field boundary.

  FORBIDDEN:             normalization inside propagation, generation,
                         vault recall, or as post-hoc repair after a
                         supposedly closed transition. If normalization is
                         needed there, fix the operator — not the result.

Contract:
  Input:  raw token sequence + VocabManifold
  Output: FieldState with F satisfying versor_condition(F) < 1e-6
"""

from dataclasses import dataclass

import numpy as np

from algebra.cl41 import geometric_product
from algebra.versor import normalize_to_versor, versor_condition
from algebra.holonomy import holonomy_encode
from field.state import FieldState
from language_packs.schema import MorphologyEntry
from language_packs.compiler import _feature_rotor


@dataclass(frozen=True, slots=True)
class _GroundedUnknown:
    token: str
    root_used: str
    versor: np.ndarray
    operators_applied: tuple[str, ...]
    condition: float


def _compact_root(root: str) -> str:
    return root.replace("-", "")


def _known_edges(morphology_entries: tuple[MorphologyEntry, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    prefixes = {
        prefix
        for morphology in morphology_entries
        for prefix in morphology.prefix_chain
        if prefix
    }
    suffixes = {
        suffix
        for morphology in morphology_entries
        for suffix in morphology.suffix_chain
        if suffix
    }
    return (
        tuple(sorted(prefixes, key=len, reverse=True)),
        tuple(sorted(suffixes, key=len, reverse=True)),
    )


def _root_surfaces(vocab, morphology_entries: tuple[MorphologyEntry, ...]) -> dict[str, str]:
    roots: dict[str, str] = {}
    for morphology in morphology_entries:
        for candidate in (
            morphology.surface,
            morphology.lemma,
            morphology.stem,
            _compact_root(morphology.root) if morphology.root else None,
        ):
            if not candidate:
                continue
            try:
                vocab.get_versor(candidate)
            except KeyError:
                continue
            roots.setdefault(candidate, candidate)
    return roots


def _root_affinity(candidate: str, root: str) -> int:
    common_prefix = 0
    for left, right in zip(candidate, root):
        if left != right:
            break
        common_prefix += 1
    shared = len(set(candidate).intersection(root))
    length_penalty = abs(len(candidate) - len(root))
    return (common_prefix * 8) + (shared * 2) - length_penalty


def _best_decomposition(
    token: str,
    vocab,
    morphology_entries: tuple[MorphologyEntry, ...],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    prefixes, suffixes = _known_edges(morphology_entries)
    roots = _root_surfaces(vocab, morphology_entries)
    prefix_options = ("", *prefixes)
    suffix_options = ("", *suffixes)

    best: tuple[int, str, tuple[str, ...], tuple[str, ...]] | None = None
    for prefix in prefix_options:
        if prefix and not token.startswith(prefix):
            continue
        after_prefix = token[len(prefix):] if prefix else token
        for suffix in suffix_options:
            if suffix and not after_prefix.endswith(suffix):
                continue
            root_candidate = after_prefix[: -len(suffix)] if suffix else after_prefix
            root_surface = roots.get(root_candidate)
            if root_surface is None:
                continue
            score = len(root_candidate) * 8 + len(prefix) + len(suffix)
            if prefix or suffix:
                score += 64
            if best is None or score > best[0]:
                best = (
                    score,
                    root_surface,
                    (prefix,) if prefix else (),
                    (suffix,) if suffix else (),
                )

    if best is None:
        for prefix in prefix_options:
            if prefix and not token.startswith(prefix):
                continue
            after_prefix = token[len(prefix):] if prefix else token
            for suffix in suffix_options:
                if suffix and not after_prefix.endswith(suffix):
                    continue
                root_candidate = after_prefix[: -len(suffix)] if suffix else after_prefix
                for known_root, root_surface in roots.items():
                    affinity = _root_affinity(root_candidate, known_root)
                    score = affinity + len(prefix) + len(suffix)
                    if prefix or suffix:
                        score += 32
                    if best is None or score > best[0]:
                        best = (
                            score,
                            root_surface,
                            (prefix,) if prefix else (),
                            (suffix,) if suffix else (),
                        )

    if best is None:
        raise KeyError(f"Token '{token}' cannot be decomposed against mounted morphology.")
    _, root_surface, applied_prefixes, applied_suffixes = best
    return root_surface, applied_prefixes, applied_suffixes


def _compose_delta(root_versor: np.ndarray, prefixes: tuple[str, ...], suffixes: tuple[str, ...]) -> tuple[np.ndarray, tuple[str, ...]]:
    versor = np.asarray(root_versor, dtype=np.float32).copy()
    operators: list[str] = []

    for idx, prefix in enumerate(prefixes):
        versor = geometric_product(
            versor,
            _feature_rotor(f"{idx}:{prefix.lower()}", "morph:prefix", 0.03 / (idx + 1)),
        )
        operators.append(f"prefix:{prefix}")

    for idx, suffix in enumerate(suffixes):
        versor = geometric_product(
            versor,
            _feature_rotor(f"{idx}:{suffix.lower()}", "morph:suffix", 0.02 / (idx + 1)),
        )
        operators.append(f"suffix:{suffix}")

    return versor.astype(np.float32, copy=False), tuple(operators)


def _ground_unknown_token(token: str, vocab) -> np.ndarray:
    morphology_entries = (
        vocab.morphology_entries()
        if hasattr(vocab, "morphology_entries")
        else ()
    )
    if not morphology_entries or not hasattr(vocab, "insert_transient"):
        raise KeyError(f"Word '{token}' not in vocabulary.")

    root_used, prefixes, suffixes = _best_decomposition(token, vocab, morphology_entries)
    root_versor = vocab.get_versor(root_used)
    versor, operators_applied = _compose_delta(root_versor, prefixes, suffixes)
    condition = versor_condition(versor)
    if condition > 1e-6:
        raise RuntimeError(
            f"Unknown-token construction for '{token}' produced non-versor: "
            f"condition={condition:.2e}."
        )

    grounded = _GroundedUnknown(
        token=token,
        root_used=root_used,
        versor=versor,
        operators_applied=operators_applied,
        condition=condition,
    )
    vocab.insert_transient(grounded.token, grounded.versor)
    if hasattr(vocab, "record_unknown_token"):
        vocab.record_unknown_token(
            grounded.token,
            grounded.root_used,
            grounded.operators_applied,
            grounded.condition,
        )
    return grounded.versor.copy()


def _lookup_or_ground(token: str, vocab) -> np.ndarray:
    try:
        return vocab.get_versor(token)
    except KeyError:
        return _ground_unknown_token(token, vocab)


def inject(tokens: list, vocab) -> FieldState:
    """
    Encode a token sequence and inject into the versor manifold.

    Steps:
    1. Look up each token's versor in the vocab manifold
    2. Encode via holonomy walk
    3. normalize_to_versor() — the single allowed gate normalization call
    4. Assert versor condition before returning
    """
    word_versors = [_lookup_or_ground(t, vocab) for t in tokens]
    H = holonomy_encode(word_versors)
    F = normalize_to_versor(H)

    cond = versor_condition(F)
    if cond > 1e-5:
        raise RuntimeError(
            f"Injection produced non-versor field: condition={cond:.2e}. "
            "Check holonomy_encode() and normalize_to_versor()."
        )

    return FieldState(F=F, node=0, step=0, holonomy=H)
