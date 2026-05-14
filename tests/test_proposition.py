from __future__ import annotations

from algebra.cga import cga_inner
from generate.proposition import FrameRegistry, Proposition, propose
from ingest.gate import inject
from language_packs.compiler import load_mounted_packs
from vault.store import VaultStore


def test_light_prompt_generates_structured_proposition_near_prompt():
    vocab = load_mounted_packs(
        ("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1")
    )
    state = inject(["light", "אוֹר", "φῶς"], vocab)
    vault = VaultStore()
    random_idx = vault.store(vocab.get_versor("λόγος"), {"kind": "random"})
    registry = FrameRegistry.from_pack("grc", vocab)

    proposition = propose(state, vault, vocab, registry)

    assert isinstance(proposition, Proposition)
    assert proposition.subject
    assert proposition.predicate
    assert proposition.surface
    random_entry = vault.recall(vocab.get_versor("λόγος"), top_k=1)[0]["versor"]
    prompt = state.F

    assert cga_inner(proposition.subject_versor, prompt) > cga_inner(
        proposition.subject_versor,
        random_entry,
    )
    assert cga_inner(proposition.predicate_versor, prompt) > cga_inner(
        proposition.predicate_versor,
        random_entry,
    )
    stored = vault.recall(state.F, top_k=2)
    assert any(hit["metadata"].get("kind") == "proposition" for hit in stored)
    assert random_idx == 0
