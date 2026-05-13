"""
VocabManifold — the geometric vocabulary.

Each word is a versor in Cl(4,1). nearest(F) finds the closest word
by CGA inner product — no cosine similarity, no ANN index.

Invariant: every stored versor must satisfy the Cl(4,1) grade-norm
condition |V * reverse(V)|_scalar ≈ ±1. This is enforced at insertion
time in add(). Raw coordinate vectors (e.g. from external embeddings)
will fail this check — use normalize_to_versor() before calling add().

Rotor construction between word-versors is NOT a vocabulary concern.
Use algebra.word_transition_rotor(A, B) from the algebra layer when
a transition operator is needed in field or generation logic.
"""

import numpy as np
from algebra.cga import cga_inner
from algebra.cl41 import geometric_product, reverse
from algebra.versor import normalize_to_versor


class VocabManifold:
    def __init__(self):
        self._words: list = []
        self._versors: list = []  # each shape (32,), grade-normed to ±1

    def add(self, word: str, versor: np.ndarray) -> None:
        """
        Register a word-versor pair.

        Enforces the Cl(4,1) versor invariant: the scalar part of
        V * reverse(V) must be ≈ ±1. This rejects any raw coordinate
        vector or external embedding that has not been lifted into the
        algebra. If your source is a float array from outside the system,
        call normalize_to_versor() first.

        Raises:
            ValueError: if the grade-norm condition is not satisfied.
        """
        v = np.asarray(versor, dtype=np.float32).copy()
        grade_norm = float(geometric_product(v, reverse(v))[0])
        if not (0.95 <= abs(grade_norm) <= 1.05):
            raise ValueError(
                f"Word '{word}': versor grade-norm {grade_norm:.4f} ≠ ±1. "
                "Pass a valid Cl(4,1) versor. "
                "If lifting from a raw array, call normalize_to_versor() first."
            )
        self._words.append(word)
        self._versors.append(v)

    def get_versor(self, word: str) -> np.ndarray:
        """Look up a word's versor. Raises KeyError if not found."""
        try:
            idx = self._words.index(word)
            return self._versors[idx].copy()
        except ValueError:
            raise KeyError(f"Word '{word}' not in vocabulary.")

    def nearest(self, F: np.ndarray, exclude_idx: int = -1) -> tuple:
        """
        Find the word whose versor is closest to F by CGA inner product.
        Returns (word, index). O(|vocab|), exact, no approximation.
        cga_inner(X, Y) = -d^2 / 2 for null vectors: maximizing = minimizing distance.
        """
        best_score = -np.inf
        best_idx = 0
        for i, v in enumerate(self._versors):
            if i == exclude_idx:
                continue
            score = cga_inner(F, v)
            if score > best_score:
                best_score = score
                best_idx = i
        return self._words[best_idx], best_idx

    def __len__(self) -> int:
        return len(self._words)
