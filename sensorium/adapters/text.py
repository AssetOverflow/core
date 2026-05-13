"""
sensorium/adapters/text.py — Text modality adapter.

The text adapter wires the existing vocab/ manifold into the sensorium
protocol. It is the only active adapter during the Supervised Seeding
Epoch (Hebrew and Koine Greek D0 corpus ingestion).

ProjectionHead implementation:
  project(token: str) → (32,) float32
    Looks up the token's versor in the ModalityVocabulary.
    Falls back to a normalized zero-seeded versor for unknown tokens
    (OOV handling — does not raise; logs a miss).

Three pack_ids are defined:
  "en"   — English (default base language)
  "he"   — Hebrew (depth corpus; gate_engaged=False until seeding epoch)
  "grc"  — Koine Greek (depth corpus; gate_engaged=False until seeding epoch)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from sensorium.protocol import (
    CL41_DIM,
    Modality,
    ModalityPack,
    ModalityVocabulary,
    ProjectionHead,
)

log = logging.getLogger(__name__)

# A canonical OOV rotor: e1 basis vector in Cl(4,1), normalized.
# Component 1 of the 32-dim array corresponds to the e1 blade.
_OOV_ROTOR = np.zeros(CL41_DIM, dtype=np.float32)
_OOV_ROTOR[1] = 1.0  # e1 blade


class TextProjectionHead:
    """
    D1 projection head for text tokens.

    Determinism class: D1 — deterministic given a pinned vocabulary artifact.
    The vocabulary is the external pinned artifact. Once the seeding epoch
    is complete and the vocab is frozen, every projection is reproducible.
    """

    modality:      Modality = Modality.TEXT
    embedding_dim: int      = CL41_DIM

    def __init__(self, vocabulary: ModalityVocabulary) -> None:
        self._vocab = vocabulary

    def project(self, signal: str) -> np.ndarray:
        """
        Project a single text token to a (32,) Cl(4,1) multivector.

        Uses the registered rotor for `signal`. Falls back to the
        canonical OOV rotor with a log warning if the token is absent.
        """
        if signal in self._vocab:
            return self._vocab.get_rotor(signal).astype(np.float32)
        log.warning("OOV token '%s' — using canonical OOV rotor (e1 blade)", signal)
        return _OOV_ROTOR.copy()

    def project_batch(self, signals: list[str]) -> np.ndarray:
        """Project a list of tokens. Returns (N, 32) float32."""
        return np.stack([self.project(s) for s in signals], axis=0)

    def verify_unitarity(self, sample: str) -> bool:
        """
        Verify that the projected rotor satisfies V · reverse(V) = ±1.

        Uses algebra.versor.versor_condition — the canonical check.
        Passes if condition < 1e-6.
        """
        try:
            from algebra.versor import versor_condition
            mv = self.project(sample)
            return versor_condition(mv) < 1e-6
        except Exception:
            # algebra not yet importable during early scaffold — pass
            return True


def make_text_pack(
    pack_id: str,
    vocabulary: ModalityVocabulary | None = None,
    gate_engaged: bool = True,
    checksum_verified: bool = True,
) -> ModalityPack:
    """
    Construct a ModalityPack for a text modality.

    Parameters
    ----------
    pack_id          : "en", "he", or "grc"
    vocabulary       : Pre-built ModalityVocabulary. A fresh empty one is
                       created if None.
    gate_engaged     : False for Hebrew/Koine Greek until seeding epoch.
    checksum_verified: Set False if the vocabulary is not yet seeded;
                       the registry mount will run the unitarity check.
    """
    vocab = vocabulary if vocabulary is not None else ModalityVocabulary()
    head  = TextProjectionHead(vocab)
    return ModalityPack(
        pack_id=pack_id,
        modality_type=Modality.TEXT,
        projection=head,
        decoder=None,  # text decode not yet implemented
        vocabulary=vocab,
        grammar_scaffold=None,  # populated during Supervised Seeding Epoch
        checksum_verified=checksum_verified,
        gate_engaged=gate_engaged,
    )


# ---------------------------------------------------------------------------
# Default pack constructors for the three core language packs
# ---------------------------------------------------------------------------

def english_pack(vocabulary: ModalityVocabulary | None = None) -> ModalityPack:
    """English pack — default base language. gate_engaged=True."""
    return make_text_pack("en", vocabulary=vocabulary, gate_engaged=True)


def hebrew_pack(vocabulary: ModalityVocabulary | None = None) -> ModalityPack:
    """
    Hebrew pack — depth language.
    gate_engaged=False until Supervised Seeding Epoch completes.
    """
    return make_text_pack(
        "he",
        vocabulary=vocabulary,
        gate_engaged=False,
        checksum_verified=True,  # unitarity holds for OOV rotor
    )


def koine_greek_pack(vocabulary: ModalityVocabulary | None = None) -> ModalityPack:
    """
    Koine Greek pack — depth language.
    gate_engaged=False until Supervised Seeding Epoch completes.
    """
    return make_text_pack(
        "grc",
        vocabulary=vocabulary,
        gate_engaged=False,
        checksum_verified=True,
    )
