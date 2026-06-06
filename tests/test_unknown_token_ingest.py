from __future__ import annotations

import numpy as np

from algebra.backend import cga_inner
from algebra.versor import unitize_versor, versor_condition
from ingest.gate import inject
from language_packs.compiler import load_mounted_packs
from session.context import SessionContext


def _random_versor(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(32).astype(np.float32)
    return unitize_versor(vec)


def test_unknown_token_is_grounded_as_valid_transient_versor() -> None:
    vocab = load_mounted_packs(("he_logos_micro_v1",))
    token = "דברית"

    state = inject([token], vocab)
    constructed = vocab.get_versor(token)
    root = vocab.get_versor("דבר")
    random = _random_versor(41)

    assert versor_condition(constructed) < 1e-6
    assert versor_condition(state.F) < 1e-6
    assert vocab.is_transient(token)
    token_idx = vocab.index_of(token)
    assert vocab.nearest(constructed, exclude_indices=set(range(token_idx)))[0] == token
    assert cga_inner(constructed, root) > cga_inner(constructed, random)

    log = vocab.unknown_token_log
    assert log[0]["token"] == token
    assert log[0]["root_used"] == "דבר"
    assert log[0]["operators_applied"][0] == "suffix:ית"
    assert log[0]["operators_applied"][1].startswith("token:sha256:")
    assert log[0]["versor_condition_score"] < 1e-6


def test_unknown_token_session_turn_evolves_field() -> None:
    vocab = load_mounted_packs(("he_logos_micro_v1", "grc_logos_micro_v1"))
    session = SessionContext(vocab=vocab)
    token = "דברית"

    first = session.ingest([token])
    response = session.respond(max_tokens=3)
    second = session.ingest([token])

    assert vocab.is_transient(token)
    assert versor_condition(first.F) < 1e-6
    assert versor_condition(response.final_state.F) < 1e-6
    assert versor_condition(second.F) < 1e-6
    assert not np.array_equal(first.F, second.F)
