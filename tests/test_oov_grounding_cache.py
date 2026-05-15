"""Tests for OOV grounding morphology cache behavior."""
from __future__ import annotations

import numpy as np
import pytest

from algebra.versor import versor_condition
from ingest import gate
from ingest.gate import inject
from language_packs.compiler import load_mounted_packs


def test_oov_grounding_repeated_token_is_deterministic() -> None:
    vocab_a = load_mounted_packs(("he_logos_micro_v1",))
    vocab_b = load_mounted_packs(("he_logos_micro_v1",))

    state_a = inject(["דברית"], vocab_a)
    state_b = inject(["דברית"], vocab_b)

    np.testing.assert_allclose(
        vocab_a.get_versor("דברית"),
        vocab_b.get_versor("דברית"),
        atol=1e-6,
    )
    np.testing.assert_allclose(state_a.F, state_b.F, atol=1e-6)


def test_oov_cache_does_not_skip_unknown_token_audit() -> None:
    vocab = load_mounted_packs(("he_logos_micro_v1",))

    inject(["דברית"], vocab)

    log = vocab.unknown_token_log
    assert len(log) >= 1
    assert log[0]["token"] == "דברית"


def test_oov_cache_does_not_share_transients_between_vocab_instances() -> None:
    vocab_a = load_mounted_packs(("he_logos_micro_v1",))
    vocab_b = load_mounted_packs(("he_logos_micro_v1",))

    inject(["דברית"], vocab_a)

    assert vocab_a.is_transient("דברית")
    assert not vocab_b.is_transient("דברית")


def test_oov_cache_preserves_versor_condition() -> None:
    vocab = load_mounted_packs(("he_logos_micro_v1",))

    state = inject(["דברית"], vocab)

    assert versor_condition(state.F) < 1e-6
    assert versor_condition(vocab.get_versor("דברית")) < 1e-6


def test_oov_cache_reuses_morphology_index(monkeypatch: pytest.MonkeyPatch) -> None:
    vocab = load_mounted_packs(("he_logos_micro_v1",))

    gate._MORPH_INDEX_CACHE.pop(id(vocab), None)

    calls = 0
    original = gate._build_morphology_index

    def counted(v, entries):
        nonlocal calls
        calls += 1
        return original(v, entries)

    monkeypatch.setattr(gate, "_build_morphology_index", counted)

    inject(["דברית"], vocab)
    vocab_b = load_mounted_packs(("he_logos_micro_v1",))
    inject(["דברית"], vocab_b)

    assert calls <= 2
