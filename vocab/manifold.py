"""
VocabManifold — the geometric vocabulary.

Each word is a versor in Cl(4,1). nearest(F) finds the closest word
by CGA inner product — no cosine similarity, no ANN index.
"""

import numpy as np
from algebra.cga import cga_inner
from algebra.versor import normalize_to_versor
from algebra.cl41 import geometric_product, reverse


class VocabManifold:
    def __init__(self):
        self._words: list = []
        self._versors: list = []  # each shape (32,)

    def add(self, word: str, versor: np.ndarray) -> None:
        """Register a word-versor pair."""
        self._words.append(word)
        self._versors.append(np.asarray(versor, dtype=np.float32).copy())

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

    def edge_rotor(self, from_idx: int, to_idx: int) -> np.ndarray:
        """
        Compute the rotor that rotates from_versor toward to_versor.
        R = normalize(1 + B * reverse(A))
        """
        A = self._versors[from_idx]
        B = self._versors[to_idx]
        R = geometric_product(B, reverse(A))
        R = R.copy()
        R[0] += 1.0
        return normalize_to_versor(R)

    def __len__(self) -> int:
        return len(self._words)
