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

    def __init__(self, vocabulary: ModalityVocabulary, oov_policy: OOVPolicy) -> None:
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
    return ModalityPack(
        pack_id=pack_id,
        modality_type=Modality.TEXT,
        projection=head,
        decoder=None,  # text decode not yet implemented
        vocabulary=vocab,
        grammar_scaffold=None,  # populated during Supervised Seeding Epoch
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
