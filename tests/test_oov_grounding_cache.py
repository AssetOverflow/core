"""Tests for OOV grounding morphology cache behavior."""
from __future__ import annotations

import numpy as np
import pytest

from algebra.versor import versor_condition
from core.config import DEFAULT_CONFIG
from ingest import gate
from ingest.gate import inject
from language_packs.compiler import load_mounted_packs
from persona.motor import PersonaMotor
from session.context import SessionContext


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


def test_generic_oov_probe_is_byte_stable_across_contexts_and_restore() -> None:
    token = "<oov>"
    collision_token_a = "xyzzy_unknown_token_12345"
    collision_token_b = "zzq-no-morph-019"
    persona = PersonaMotor.identity()
    vocab_a = load_mounted_packs(DEFAULT_CONFIG.input_packs)
    vocab_b = load_mounted_packs(DEFAULT_CONFIG.input_packs)
    vocab_c = load_mounted_packs(DEFAULT_CONFIG.input_packs)
    vocab_d = load_mounted_packs(DEFAULT_CONFIG.input_packs)

    ctx_a = SessionContext(vocab=vocab_a, persona=persona)
    ctx_b = SessionContext(vocab=vocab_b, persona=persona)
    ctx_c = SessionContext(vocab=vocab_c, persona=persona)
    ctx_d = SessionContext(vocab=vocab_d, persona=persona)

    field_a = ctx_a.probe_ingest([token]).F
    field_b = ctx_b.probe_ingest([token]).F
    field_c = ctx_c.probe_ingest([collision_token_a]).F
    field_d = ctx_d.probe_ingest([collision_token_b]).F

    assert field_a.tobytes() == field_b.tobytes()
    assert field_c.tobytes() != field_d.tobytes()
    assert versor_condition(field_a) < 1e-6
    assert versor_condition(field_b) < 1e-6
    assert versor_condition(field_c) < 1e-6
    assert versor_condition(field_d) < 1e-6

    restored = SessionContext(
        vocab=load_mounted_packs(DEFAULT_CONFIG.input_packs),
        persona=persona,
    )
    restored.restore(ctx_a.snapshot())
    restored_field = restored.probe_ingest([token]).F

    assert restored_field.tobytes() == field_a.tobytes()
    assert versor_condition(restored_field) < 1e-6


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
