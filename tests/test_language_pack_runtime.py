from __future__ import annotations

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
