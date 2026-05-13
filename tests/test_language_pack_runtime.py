from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from language_packs import load_pack


def test_load_pack_and_vocab_size():
    manifest, manifold = load_pack("en_minimal_v1")
    assert manifest.pack_id == "en_minimal_v1"
    assert len(manifold) == 60


def test_light_neighborhood_not_negation():
    _, manifold = load_pack("en_minimal_v1")
    light = manifold.get_versor("light")
    word, _ = manifold.nearest(light, exclude_idx=25)
    assert word not in {"no", "cannot"}


def test_chat_runtime_responds_and_varies():
    runtime = ChatRuntime("en_minimal_v1")
    a = runtime.respond("what is truth", max_tokens=8)
    b = runtime.respond("what is light", max_tokens=8)
    assert a.strip()
    assert b.strip()
    assert a != b


def test_chat_runtime_canonicalizes_case_and_punctuation():
    plain = ChatRuntime("en_minimal_v1").respond("what is light", max_tokens=8)
    punctuated = ChatRuntime("en_minimal_v1").respond("WHAT is light?", max_tokens=8)
    assert punctuated == plain


def test_chat_runtime_fail_closed_pack_rejects_oov():
    runtime = ChatRuntime("he_logos_micro_v1")
    with pytest.raises(KeyError):
        runtime.respond("light", max_tokens=4)


def test_vocab_manifold_exposes_public_word_index():
    _, manifold = load_pack("en_minimal_v1")
    idx = manifold.index_of("light")
    assert manifold.get_word_at(idx) == "light"
