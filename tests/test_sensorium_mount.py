"""
Tests for sensorium/ modality protocol layer.

Covers:
  - ModalityPack construction and invariants
  - gate_engaged / checksum_verified invariant
  - embedding_dim enforcement (must be 32 for Cl(4,1))
  - ModalityRegistry mount, get, project, project_batch
  - gate_engaged=False blocks projection
  - unitarity check failure blocks mount
  - TextProjectionHead: project, project_batch, OOV fallback
  - Three core language packs: en, he, grc
  - Output shape invariant: every projection returns (32,) float32
"""

from __future__ import annotations

import numpy as np
import pytest

from sensorium.protocol import (
    CL41_DIM,
    Modality,
    ModalityPack,
    ModalityVocabulary,
)
from sensorium.registry import ModalityRegistry
from sensorium.adapters.text import (
    TextProjectionHead,
    english_pack,
    hebrew_pack,
    koine_greek_pack,
    make_text_pack,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rotor(seed: float = 1.0) -> np.ndarray:
    """A trivial unit versor: scalar component = seed, rest zero."""
    r = np.zeros(CL41_DIM, dtype=np.float32)
    r[0] = seed
    return r


def _vocab_with_tokens(*tokens: str) -> ModalityVocabulary:
    vocab = ModalityVocabulary()
    for i, tok in enumerate(tokens):
        r = np.zeros(CL41_DIM, dtype=np.float32)
        r[0] = 1.0  # scalar blade — unit versor
        vocab.register(tok, r)
    return vocab


# ---------------------------------------------------------------------------
# ModalityPack invariants
# ---------------------------------------------------------------------------

class TestModalityPackInvariants:

    def test_gate_engaged_requires_checksum(self):
        vocab = _vocab_with_tokens("logos")
        head  = TextProjectionHead(vocab)
        with pytest.raises(ValueError, match="checksum_verified"):
            ModalityPack(
                pack_id="en",
                modality_type=Modality.TEXT,
                projection=head,
                decoder=None,
                vocabulary=vocab,
                grammar_scaffold=None,
                checksum_verified=False,   # ← False
                gate_engaged=True,         # ← True — should raise
            )

    def test_gate_not_engaged_allows_unverified(self):
        vocab = _vocab_with_tokens("logos")
        head  = TextProjectionHead(vocab)
        # Should not raise
        pack = ModalityPack(
            pack_id="he",
            modality_type=Modality.TEXT,
            projection=head,
            decoder=None,
            vocabulary=vocab,
            grammar_scaffold=None,
            checksum_verified=False,
            gate_engaged=False,
        )
        assert not pack.gate_engaged

    def test_wrong_embedding_dim_raises(self):
        class BadHead:
            modality = Modality.TEXT
            embedding_dim = 16  # wrong — must be 32
            def project(self, s): return np.zeros(16, dtype=np.float32)
            def project_batch(self, ss): return np.zeros((len(ss), 16), dtype=np.float32)
            def verify_unitarity(self, s): return True

        vocab = ModalityVocabulary()
        with pytest.raises(ValueError, match="embedding_dim"):
            ModalityPack(
                pack_id="bad",
                modality_type=Modality.TEXT,
                projection=BadHead(),
                decoder=None,
                vocabulary=vocab,
                grammar_scaffold=None,
                checksum_verified=True,
                gate_engaged=True,
            )


# ---------------------------------------------------------------------------
# ModalityRegistry
# ---------------------------------------------------------------------------

class TestModalityRegistry:

    def test_mount_and_get(self):
        registry = ModalityRegistry()
        pack = english_pack(_vocab_with_tokens("beginning"))
        registry.mount(pack)
        assert "en" in registry
        assert registry.get("en") is pack

    def test_get_missing_raises(self):
        registry = ModalityRegistry()
        with pytest.raises(KeyError, match="vision"):
            registry.get("vision")

    def test_project_returns_shape_32(self):
        vocab = _vocab_with_tokens("logos", "beginning", "earth")
        pack  = english_pack(vocab)
        registry = ModalityRegistry()
        registry.mount(pack)
        mv = registry.project("en", "logos")
        assert mv.shape == (CL41_DIM,)
        assert mv.dtype == np.float32

    def test_project_batch_shape(self):
        vocab = _vocab_with_tokens("logos", "light", "word")
        registry = ModalityRegistry()
        registry.mount(english_pack(vocab))
        mvs = registry.project_batch("en", ["logos", "light", "word"])
        assert mvs.shape == (3, CL41_DIM)
        assert mvs.dtype == np.float32

    def test_gate_not_engaged_blocks_projection(self):
        vocab = _vocab_with_tokens("bereshit")
        pack  = hebrew_pack(vocab)  # gate_engaged=False
        registry = ModalityRegistry()
        registry.mount(pack)
        with pytest.raises(RuntimeError, match="gate is not engaged"):
            registry.project("he", "bereshit")

    def test_unitarity_failure_blocks_mount(self):
        class FailingHead:
            modality = Modality.TEXT
            embedding_dim = CL41_DIM
            def project(self, s): return np.zeros(CL41_DIM, dtype=np.float32)
            def project_batch(self, ss): return np.zeros((len(ss), CL41_DIM), dtype=np.float32)
            def verify_unitarity(self, s): return False  # always fails

        vocab = _vocab_with_tokens("test")
        pack = ModalityPack(
            pack_id="broken",
            modality_type=Modality.TEXT,
            projection=FailingHead(),
            decoder=None,
            vocabulary=vocab,
            grammar_scaffold=None,
            checksum_verified=False,
            gate_engaged=False,
        )
        registry = ModalityRegistry()
        with pytest.raises(ValueError, match="Unitarity check failed"):
            registry.mount(pack, sample="test")

    def test_mounted_packs_list(self):
        registry = ModalityRegistry()
        registry.mount(english_pack())
        assert "en" in registry.mounted_packs()


# ---------------------------------------------------------------------------
# TextProjectionHead
# ---------------------------------------------------------------------------

class TestTextProjectionHead:

    def test_known_token_returns_registered_rotor(self):
        vocab = _vocab_with_tokens("logos")
        head  = TextProjectionHead(vocab)
        mv = head.project("logos")
        assert mv.shape == (CL41_DIM,)
        assert mv[0] == pytest.approx(1.0)

    def test_oov_returns_e1_rotor(self):
        head = TextProjectionHead(ModalityVocabulary())
        mv   = head.project("unknown_token_xyz")
        assert mv.shape == (CL41_DIM,)
        # OOV rotor has e1 blade = 1.0, all others 0
        assert mv[1] == pytest.approx(1.0)
        assert mv[0] == pytest.approx(0.0)

    def test_batch_shape(self):
        vocab = _vocab_with_tokens("a", "b", "c")
        head  = TextProjectionHead(vocab)
        mvs   = head.project_batch(["a", "b", "c"])
        assert mvs.shape == (3, CL41_DIM)

    def test_output_always_float32(self):
        vocab = _vocab_with_tokens("word")
        head  = TextProjectionHead(vocab)
        assert head.project("word").dtype == np.float32
        assert head.project("oov").dtype  == np.float32


# ---------------------------------------------------------------------------
# Three core language packs
# ---------------------------------------------------------------------------

class TestCoreLanguagePacks:

    def test_english_pack_gate_engaged(self):
        pack = english_pack()
        assert pack.gate_engaged is True
        assert pack.pack_id == "en"
        assert pack.modality_type == Modality.TEXT

    def test_hebrew_pack_gate_not_engaged(self):
        pack = hebrew_pack()
        assert pack.gate_engaged is False
        assert pack.pack_id == "he"

    def test_koine_greek_pack_gate_not_engaged(self):
        pack = koine_greek_pack()
        assert pack.gate_engaged is False
        assert pack.pack_id == "grc"

    def test_all_three_mount_without_error(self):
        registry = ModalityRegistry()
        registry.mount(english_pack())
        registry.mount(hebrew_pack())
        registry.mount(koine_greek_pack())
        assert len(registry) == 3
