"""
VocabManifold — the geometric vocabulary.

Each word is a versor in Cl(4,1). nearest(F) finds the closest word
by CGA inner product — no cosine similarity, no ANN index.

Invariant: every stored versor must satisfy the Cl(4,1) grade-norm
condition |V * reverse(V)|_scalar ≈ ±1. This is enforced at insertion
time in add() and at replacement time in update().

Normalization doctrine for this module:
  - Raw coordinate vectors (e.g. from external embeddings) must be
    lifted via unitize_versor() (algebra/versor.py) BEFORE calling add().
  - This module does not call any normalization function internally.
  - Rotor construction between word-versors is NOT a vocabulary concern.
    Use algebra.rotor.word_transition_rotor(A, B) when a transition
    operator is needed in field or generation logic.

Indexed access:
  get_versor_at(idx)  — returns a copy of the stored versor by integer index.
  get_word_at(idx)    — returns the word string by integer index.
  index_of(word)       — returns the integer index for a stored word.
  These are the primitives generation uses; VocabManifold does not build
  operators. Algebra builds operators. Vocab stores points.

Hot path: nearest() routes cga_inner through algebra.backend, which
dispatches to the Rust extension when available.
"""

import numpy as np
from algebra.backend import cga_inner
from algebra.cl41 import geometric_product, reverse


class VocabManifold:
    def __init__(self):
        self._words: list[str] = []
        self._versors: list[np.ndarray] = []  # each shape (32,), grade-normed to ±1

    def add(self, word: str, versor: np.ndarray) -> None:
        """
        Register a word-versor pair.

        Enforces the Cl(4,1) versor invariant: the scalar part of
        V * reverse(V) must be ≈ ±1. This rejects any raw coordinate
        vector or external embedding that has not been lifted into the
        algebra.

        If your source is a raw float array, call
        algebra.versor.unitize_versor() first — that is the construction-time
        algebra primitive. Do not call normalize_to_versor() directly;
        that function is reserved for the injection gate.

        Raises:
            ValueError: if the grade-norm condition is not satisfied.
        """
        v = np.asarray(versor, dtype=np.float32).copy()
        grade_norm = float(geometric_product(v, reverse(v))[0])
        if not (0.95 <= abs(grade_norm) <= 1.05):
            raise ValueError(
                f"Word '{word}': versor grade-norm {grade_norm:.4f} ≠ ±1. "
                "Pass a valid Cl(4,1) versor. "
                "If lifting from a raw array, call algebra.versor.unitize_versor() first."
            )
        self._words.append(word)
        self._versors.append(v)

    def update(self, word: str, versor: np.ndarray) -> None:
        """
        Replace the versor for an existing word in-place.

        Used by the alignment correction pass after compilation to nudge
        cross-language aligned pairs toward each other without rebuilding
        the full manifold. The grade-norm invariant is enforced identically
        to add().

        Raises:
            KeyError:   if the word is not already in the manifold.
            ValueError: if the grade-norm condition is not satisfied.
        """
        try:
            idx = self._words.index(word)
        except ValueError:
            raise KeyError(f"Word '{word}' not in vocabulary; use add() for new entries.")
        v = np.asarray(versor, dtype=np.float32).copy()
        grade_norm = float(geometric_product(v, reverse(v))[0])
        if not (0.95 <= abs(grade_norm) <= 1.05):
            raise ValueError(
                f"Word '{word}': replacement versor grade-norm {grade_norm:.4f} ≠ ±1. "
                "Call algebra.versor.unitize_versor() before update()."
            )
        self._versors[idx] = v

    def get_versor(self, word: str) -> np.ndarray:
        """Look up a word's versor by string. Raises KeyError if not found."""
        try:
            idx = self._words.index(word)
            return self._versors[idx].copy()
        except ValueError:
            raise KeyError(f"Word '{word}' not in vocabulary.")

    def get_versor_at(self, idx: int) -> np.ndarray:
        """
        Return a copy of the stored versor at integer index.
        This is the indexed access primitive for generation — algebra
        uses these points to construct transition operators.
        """
        return self._versors[idx].copy()

    def get_word_at(self, idx: int) -> str:
        """Return the word string at integer index."""
        return self._words[idx]

    def index_of(self, word: str) -> int:
        """Return the integer index for a stored word. Raises KeyError if missing."""
        try:
            return self._words.index(word)
        except ValueError:
            raise KeyError(f"Word '{word}' not in vocabulary.")

    def nearest(
        self,
        F: np.ndarray,
        exclude_idx: int = -1,
        exclude_indices: set[int] | frozenset[int] | None = None,
    ) -> tuple[str, int]:
        """
        Find the word whose versor is closest to F by CGA inner product.
        Returns (word, index). O(|vocab|), exact, no approximation.
        cga_inner(X, Y) = -d^2 / 2 for null vectors: maximizing = minimizing distance.

        Hot path: cga_inner routes through algebra.backend.
        """
        blocked = set(exclude_indices or ())
        if exclude_idx >= 0:
            blocked.add(exclude_idx)

        best_score = -np.inf
        best_idx = -1
        for i, v in enumerate(self._versors):
            if i in blocked:
                continue
            score = cga_inner(F, v)
            if score > best_score:
                best_score = score
                best_idx = i
        if best_idx < 0:
            raise ValueError("No candidate word available after exclusions.")
        return self._words[best_idx], best_idx

    def __len__(self) -> int:
        return len(self._words)
