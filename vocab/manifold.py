"""
VocabManifold — the geometric vocabulary.

Each word is a versor in Cl(4,1). nearest(F) finds the closest word
by CGA inner product — no cosine similarity, no ANN index.

Invariant: every stored versor must satisfy the full Cl(4,1) unit-versor
condition V * reverse(V) ≈ ±1. This rejects non-scalar construction residue,
not merely scalar grade-norm drift, and is enforced at insertion time in
add() and at replacement time in update().

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
from algebra.versor import versor_unit_residual
from core.epistemic_state import EpistemicState, coerce_epistemic_state
from core.physics.energy import EnergyProfile
from core.physics.valence import ValenceBundle
from language_packs.schema import MorphologyEntry

_MANIFOLD_RESIDUAL_TOLERANCE = 1e-5


def _versor_diagnostics(v: np.ndarray) -> tuple[float, float, float]:
    product = geometric_product(v, reverse(v))
    scalar = float(product[0])
    residue = product.copy()
    residue[0] = 0.0
    residue_norm = float(np.linalg.norm(residue))
    residual = versor_unit_residual(v, allow_negative=True)
    return residual, scalar, residue_norm


def _assert_manifold_versor(word: str, versor: np.ndarray, *, replacement: bool = False) -> None:
    residual, scalar, residue_norm = _versor_diagnostics(versor)
    if residual > _MANIFOLD_RESIDUAL_TOLERANCE:
        noun = "replacement versor" if replacement else "versor"
        action = "Call algebra.versor.unitize_versor() before update()." if replacement else (
            "If lifting from a raw array, call algebra.versor.unitize_versor() first."
        )
        raise ValueError(
            f"Word '{word}': {noun} residual {residual:.4e} exceeds "
            f"{_MANIFOLD_RESIDUAL_TOLERANCE:.1e}; scalar={scalar:.4f}, "
            f"non_scalar_residue={residue_norm:.4e}. Pass a clean Cl(4,1) "
            f"unit versor satisfying V*reverse(V)≈±1. {action}"
        )


class VocabManifold:
    def __init__(self):
        self._words: list[str] = []
        self._versors: list[np.ndarray] = []  # each shape (32,), unit-versor ±1
        self._morphology_by_word: dict[str, MorphologyEntry] = {}
        self._language_by_word: dict[str, str] = {}
        self._energy_by_word: dict[str, EnergyProfile] = {}
        self._valence_by_word: dict[str, ValenceBundle] = {}
        self._epistemic_state_by_word: dict[str, str] = {}
        self._transient_words: set[str] = set()
        self._unknown_token_log: list[dict[str, object]] = []

    def add(
        self,
        word: str,
        versor: np.ndarray,
        morphology: MorphologyEntry | None = None,
        language: str | None = None,
        energy: EnergyProfile | None = None,
        valence: ValenceBundle | None = None,
        epistemic_state: str | EpistemicState | None = None,
    ) -> None:
        """
        Register a word-versor pair.

        Enforces the Cl(4,1) manifold invariant: V * reverse(V) must be
        approximately +1 or -1 as a full multivector residual, not merely
        in its scalar component. This rejects raw coordinates, external
        embeddings, and dirty construction products.

        If your source is a raw float array, call
        algebra.versor.unitize_versor() first — that is the construction-time
        algebra primitive. Do not call normalize_to_versor() directly;
        that function is reserved for the injection gate.

        ``epistemic_state`` defaults to DECODED for compiled pack entries.
        The compiler can override this when a lexical row's review status
        maps to another ratified state.

        Raises:
            ValueError: if the full unit-versor residual is not satisfied.
        """
        v = np.asarray(versor, dtype=np.float32).copy()
        _assert_manifold_versor(word, v)
        self._words.append(word)
        self._versors.append(v)
        self._epistemic_state_by_word[word] = coerce_epistemic_state(
            epistemic_state,
            default=EpistemicState.DECODED,
        ).value
        resolved_language = language or (morphology.language if morphology is not None else None)
        if resolved_language:
            self._language_by_word[word] = resolved_language
        if morphology is not None:
            self._morphology_by_word[word] = morphology
        if energy is not None:
            self._energy_by_word[word] = energy
        if valence is not None:
            self._valence_by_word[word] = valence

    def insert_transient(self, word: str, versor: np.ndarray) -> None:
        """
        Register a session-local ad hoc word-versor pair.

        Transient entries live only in this manifold instance. They use the
        same storage as compiled entries so nearest() and get_versor() remain
        exact manifold operations, but no language pack persistence path ever
        sees them.
        """
        if word in self._words and word not in self._transient_words:
            raise ValueError(f"Word '{word}' already exists as a compiled manifold entry.")
        if word in self._transient_words:
            self.update(word, versor)
            return
        self.add(word, versor, epistemic_state=EpistemicState.UNVERIFIED_NOVEL)
        self._transient_words.add(word)

    def is_transient(self, word: str) -> bool:
        """Return True when word was inserted as a session-local transient."""
        return word in self._transient_words

    def morphology_entries(self) -> tuple[MorphologyEntry, ...]:
        """Return morphology entries carried by compiled manifold surfaces."""
        return tuple(self._morphology_by_word.values())

    def record_unknown_token(
        self,
        token: str,
        root_used: str,
        operators_applied: tuple[str, ...],
        versor_condition_score: float,
    ) -> None:
        """Append an audit record for gate-constructed unknown-token grounding."""
        self._unknown_token_log.append(
            {
                "token": token,
                "root_used": root_used,
                "operators_applied": operators_applied,
                "versor_condition_score": versor_condition_score,
            }
        )

    @property
    def unknown_token_log(self) -> tuple[dict[str, object], ...]:
        """Session-local audit trail of ad hoc unknown-token constructions."""
        return tuple(dict(entry) for entry in self._unknown_token_log)

    def update(self, word: str, versor: np.ndarray) -> None:
        """
        Replace the versor for an existing word in-place.

        Used by the alignment correction pass after compilation to nudge
        cross-language aligned pairs toward each other without rebuilding
        the full manifold. The full unit-versor residual is enforced
        identically to add().

        Raises:
            KeyError:   if the word is not already in the manifold.
            ValueError: if the full unit-versor residual is not satisfied.
        """
        try:
            idx = self._words.index(word)
        except ValueError:
            raise KeyError(f"Word '{word}' not in vocabulary; use add() for new entries.")
        v = np.asarray(versor, dtype=np.float32).copy()
        _assert_manifold_versor(word, v, replacement=True)
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

    def morphology_for_word(self, word: str) -> MorphologyEntry | None:
        """Return structured morphology for a stored surface, if the pack provided it."""
        return self._morphology_by_word.get(word)

    def energy_for_word(self, word: str) -> EnergyProfile | None:
        """Return ADR-0006 energy profile for a stored surface, when available."""
        return self._energy_by_word.get(word)

    def valence_for_word(self, word: str) -> ValenceBundle | None:
        """Return ADR-0007 valence bundle for a stored surface, when available."""
        return self._valence_by_word.get(word)

    def epistemic_state_for_word(self, word: str) -> str:
        """Return the ratified epistemic state for a stored surface.

        Missing state metadata defaults to UNDETERMINED rather than
        silently treating the entry as decoded.
        """
        if word not in self._words:
            raise KeyError(f"Word '{word}' not in vocabulary.")
        return self._epistemic_state_by_word.get(word, EpistemicState.UNDETERMINED.value)

    def language_for_word(self, word: str) -> str | None:
        """Return the language code for a stored surface, if known."""
        morphology = self._morphology_by_word.get(word)
        if morphology is not None:
            return morphology.language
        return self._language_by_word.get(word)

    def indices_for_language(self, lang: str) -> np.ndarray:
        """Return manifold indices whose language matches lang."""
        matches = [
            idx
            for idx, word in enumerate(self._words)
            if self.language_for_word(word) == lang
        ]
        return np.asarray(matches, dtype=np.int64)

    def nearest(
        self,
        F: np.ndarray,
        exclude_idx: int = -1,
        exclude_indices: set[int] | frozenset[int] | None = None,
        candidate_indices: np.ndarray | list[int] | tuple[int, ...] | None = None,
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

        if candidate_indices is None:
            candidates = range(len(self._versors))
        else:
            candidates = [int(idx) for idx in candidate_indices]

        best_score = -np.inf
        best_idx = -1
        # Strict `>` is load-bearing: on ties, the first candidate in iteration
        # order wins. ADR-0024 inner-loop re-selection relies on this for
        # deterministic rejected_attempts ordering across runs.
        for i in candidates:
            if i in blocked:
                continue
            score = cga_inner(F, self._versors[i])
            if score > best_score:
                best_score = score
                best_idx = i
        if best_idx < 0:
            raise ValueError("No candidate word available after exclusions.")
        return self._words[best_idx], best_idx

    def __len__(self) -> int:
        return len(self._words)
