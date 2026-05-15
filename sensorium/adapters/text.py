"""
sensorium/adapters/text.py — Text modality adapter.

The text adapter wires language-pack vocabulary points into the sensorium
protocol. It remains intentionally shallow until compiled language packs
provide morphology, grammar attractors, and holonomy alignment manifests.

Three pack_ids are defined:
  "en"   — English (operational base / articulation surface)
  "he"   — Hebrew (depth-root language; gate closed until seeding epoch)
  "grc"  — Koine Greek (depth-relation language; gate closed until seeding epoch)

OOV doctrine:
  English may use a tagged fallback during early articulation.
  Hebrew and Koine Greek fail closed by default. Unknown depth-language forms
  must become vocab-expansion proposals, not collapse to a shared e1 point.
"""

from __future__ import annotations

import logging

import numpy as np

import hashlib

from algebra.versor import construction_seed_versor, versor_condition
from language_packs.schema import LanguageRole, OOVPolicy
from sensorium.protocol import (
    CL41_DIM,
    Modality,
    ModalityPack,
    ModalityVocabulary,
)

log = logging.getLogger(__name__)

# A canonical English-only OOV point: e1 basis vector in Cl(4,1).
# Depth packs do not use this fallback; they fail closed.
_OOV_POINT = np.zeros(CL41_DIM, dtype=np.float32)
_OOV_POINT[1] = 1.0  # e1 blade


class TextProjectionHead:
    """
    D1 projection head for text tokens.

    Determinism class: D1 — deterministic given a pinned vocabulary artifact.
    The vocabulary is the external pinned artifact. Once the seeding epoch
    is complete and the vocab is frozen, every projection is reproducible.
    """

    modality:      Modality = Modality.TEXT
    embedding_dim: int      = CL41_DIM

    def __init__(
        self,
        vocabulary: ModalityVocabulary,
        oov_policy: OOVPolicy = OOVPolicy.TAGGED_FALLBACK,
    ) -> None:
        self._vocab = vocabulary
        self._oov_policy = oov_policy

    def project(self, signal: str) -> np.ndarray:
        """
        Project a single text token to a (32,) Cl(4,1) multivector.

        Uses the registered manifold point for `signal`. OOV behavior is
        pack-specific: English may use a tagged fallback; depth packs fail
        closed so unknown Hebrew/Greek forms do not collapse together.
        """
        if signal in self._vocab:
            return self._vocab.get_point(signal).astype(np.float32)

        if self._oov_policy is OOVPolicy.FAIL_CLOSED:
            raise KeyError(
                f"OOV token '{signal}' and OOVPolicy.FAIL_CLOSED is active. "
                "Route this surface form through the vocab-expansion path."
            )
        if self._oov_policy is OOVPolicy.PROPOSE_VOCAB_EXPANSION:
            raise KeyError(
                f"OOV token '{signal}' requires a vocab-expansion proposal."
            )

        log.warning("OOV token '%s' — using tagged English fallback point", signal)
        return _OOV_POINT.copy()

    def project_batch(self, signals: list[str]) -> np.ndarray:
        """Project a list of tokens. Returns (N, 32) float32."""
        return np.stack([self.project(s) for s in signals], axis=0)

    def verify_unitarity(self, sample: str) -> bool:
        """
        Verify that the projected multivector satisfies V · reverse(V) = ±1.

        Uses algebra.versor.versor_condition — the canonical check.
        Passes if condition < 1e-6.
        """
        try:
            from algebra.versor import versor_condition
            mv = self.project(sample)
            return versor_condition(mv) < 1e-6
        except Exception:
            return False


class TextSurfaceDecoder:
    """Exact text reconstruction over the mounted modality vocabulary."""

    modality: Modality = Modality.TEXT

    def __init__(self, vocabulary: ModalityVocabulary) -> None:
        self._vocab = vocabulary

    def decode(self, mv: np.ndarray) -> str:
        query = np.asarray(mv, dtype=np.float32)
        best_token: str | None = None
        best_distance = float("inf")
        for token in self._vocab._point_keys:
            point = self._vocab.get_point(token)
            distance = float(np.linalg.norm(query - point))
            if distance < best_distance:
                best_distance = distance
                best_token = str(token)
        if best_token is None:
            raise ValueError("cannot decode from an empty text vocabulary")
        return best_token

    def decode_batch(self, mvs: np.ndarray) -> list[str]:
        return [self.decode(mv) for mv in np.asarray(mvs, dtype=np.float32)]


def make_text_pack(
    pack_id: str,
    vocabulary: ModalityVocabulary | None = None,
    gate_engaged: bool = True,
    checksum_verified: bool = True,
    language_role: LanguageRole | None = None,
    oov_policy: OOVPolicy = OOVPolicy.TAGGED_FALLBACK,
) -> ModalityPack:
    """
    Construct a ModalityPack for a text modality.

    Parameters
    ----------
    pack_id          : "en", "he", or "grc"
    vocabulary       : Pre-built ModalityVocabulary. A fresh empty one is
                       created if None.
    gate_engaged     : False for Hebrew/Koine Greek until seeding epoch.
    checksum_verified: Set False if the vocabulary is not yet seeded.
    language_role    : Architectural role in CORE-Logos.
    oov_policy       : Pack-specific unknown-token behavior.
    """
    vocab = vocabulary if vocabulary is not None else ModalityVocabulary()
    head  = TextProjectionHead(vocab, oov_policy=oov_policy)
    decoder = TextSurfaceDecoder(vocab)
    return ModalityPack(
        pack_id=pack_id,
        modality_type=Modality.TEXT,
        projection=head,
        decoder=decoder,
        vocabulary=vocab,
        grammar_scaffold=None,
        checksum_verified=checksum_verified,
        gate_engaged=gate_engaged,
        language_role=language_role,
        oov_policy=oov_policy,
    )


# ---------------------------------------------------------------------------
# Default pack constructors for the three core language packs
# ---------------------------------------------------------------------------

def english_pack(vocabulary: ModalityVocabulary | None = None) -> ModalityPack:
    """English pack — operational base and articulation surface."""
    return make_text_pack(
        "en",
        vocabulary=vocabulary,
        gate_engaged=True,
        language_role=LanguageRole.OPERATIONAL_BASE,
        oov_policy=OOVPolicy.TAGGED_FALLBACK,
    )


def hebrew_pack(vocabulary: ModalityVocabulary | None = None) -> ModalityPack:
    """
    Hebrew pack — depth-root language.
    gate_engaged=False until Supervised Seeding Epoch completes.
    """
    return make_text_pack(
        "he",
        vocabulary=vocabulary,
        gate_engaged=False,
        checksum_verified=True,
        language_role=LanguageRole.DEPTH_ROOT,
        oov_policy=OOVPolicy.FAIL_CLOSED,
    )


def koine_greek_pack(vocabulary: ModalityVocabulary | None = None) -> ModalityPack:
    """
    Koine Greek pack — depth-relation language.
    gate_engaged=False until Supervised Seeding Epoch completes.
    """
    return make_text_pack(
        "grc",
        vocabulary=vocabulary,
        gate_engaged=False,
        checksum_verified=True,
        language_role=LanguageRole.DEPTH_RELATION,
        oov_policy=OOVPolicy.FAIL_CLOSED,
    )


# ---------------------------------------------------------------------------
# Deterministic hash-to-versor stub for testing without vocabulary
# ---------------------------------------------------------------------------


def deterministic_hash_versor(text: str) -> np.ndarray:
    """Map an arbitrary string to a valid Cl(4,1) versor, deterministically.

    Uses SHA-256 bytes mapped to bounded [-1, 1] floats to fill a dense
    32-component seed, then constructs a closed versor via the seed-to-rotor
    path (construction tier).
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = np.array(
        [(b / 127.5) - 1.0 for b in digest],
        dtype=np.float64,
    )
    full_seed = np.zeros(32, dtype=np.float64)
    full_seed[:32] = seed[:32]
    versor = construction_seed_versor(full_seed)
    vc = versor_condition(versor)
    if vc >= 1e-6:
        raise ValueError(f"deterministic_hash_versor: versor_condition {vc:.2e} >= 1e-6")
    return versor.astype(np.float32)
