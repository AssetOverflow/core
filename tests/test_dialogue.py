from __future__ import annotations

import numpy as np

from generate.dialogue import (
    blade_alignment,
    classify_dialogue_blade,
    propose_dialogue,
)
from generate.proposition import FrameRegistry
from language_packs.compiler import load_mounted_packs
from session.context import SessionContext


def _dialogue_proposition(tokens: list[str], registry: FrameRegistry, vocab, reference=None):
    session = SessionContext(vocab=vocab)
    session.ingest(tokens)
    generated = session.respond(max_tokens=3)
    return propose_dialogue(generated.final_state, None, vocab, registry, reference)


def test_relation_blade_classifies_parallel_as_elaboration():
    vocab = load_mounted_packs(
        ("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1")
    )
    registry = FrameRegistry.from_pack("grc", vocab)

    first = _dialogue_proposition(["light", "φῶς"], registry, vocab)
    second = _dialogue_proposition(["φῶς", "אוֹר"], registry, vocab, first.relation)

    assert classify_dialogue_blade(second.relation, first.relation) == "elaborate"
    assert second.frame_id == "el:colwell-construction"
    assert second.surface != first.surface


def test_two_turn_light_exchange_tracks_parallel_dialogue_trajectory():
    vocab = load_mounted_packs(
        ("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1")
    )
    registry = FrameRegistry.from_pack("grc", vocab)
    session = SessionContext(vocab=vocab)

    session.ingest(["light", "φῶς"])
    first_generated = session.respond(max_tokens=3)
    first = propose_dialogue(first_generated.final_state, None, vocab, registry)
    first_turn = session.record_dialogue(first)

    session.ingest(["light", "truth"])
    second_generated = session.respond(max_tokens=3)
    second = propose_dialogue(
        second_generated.final_state,
        None,
        vocab,
        registry,
        session.last_dialogue_blade,
    )
    second_turn = session.record_dialogue(second)

    random_turn = _dialogue_proposition(["truth", "λόγος"], registry, vocab)
    second_alignment = blade_alignment(
        second_turn.outer_product_blade,
        first_turn.outer_product_blade,
    )
    random_alignment = blade_alignment(random_turn.relation, first_turn.outer_product_blade)

    assert second.frame_id == "el:colwell-construction"
    assert second.surface != first.surface
    assert second_alignment > random_alignment
    assert second_alignment > 0.35
    assert len(session.dialogue_history) == 2
    assert session.running_dialogue_blade is not None
    assert np.linalg.norm(session.running_dialogue_blade) > 0.0
