from __future__ import annotations

import numpy as np

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from generate.attention import AttentionOperator
from generate.salience import SalienceOperator


def test_salience_map_has_top_k_entries_and_descending_scores() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(output_language="en", frame_pack="en"))
    field = runtime.session.ingest(runtime.tokenize("word beginning truth"))
    salience = SalienceOperator().compute(field, runtime.session.vocab, top_k=8)

    assert len(salience.indices) == 8
    assert len(salience.scores) == 8
    assert salience.budget == 8
    assert np.all(salience.scores[:-1] >= salience.scores[1:])


def test_attention_plan_inhibits_salience_tail() -> None:
    runtime = ChatRuntime(config=RuntimeConfig(output_language="en", frame_pack="en"))
    field = runtime.session.ingest(runtime.tokenize("word beginning truth"))
    salience = SalienceOperator().compute(field, runtime.session.vocab, top_k=16)
    plan = AttentionOperator(inhibition_threshold=0.9).plan(salience, runtime.session.vocab)

    assert 0 < len(plan.allowed_indices) <= len(salience.indices)
    assert set(plan.allowed_indices).issubset(set(salience.indices))
    assert len(plan.allowed_indices) < len(salience.indices)


def test_salience_enabled_bounds_generation_walk() -> None:
    config = RuntimeConfig(output_language="en", frame_pack="en", salience_top_k=8)
    runtime = ChatRuntime(config=config)
    runtime.chat("word beginning truth")
    response = runtime.chat("word beginning truth")

    assert response.salience_top_k == 8
    assert response.candidates_used is not None
    assert 0 < response.candidates_used <= 8


def test_salience_disabled_preserves_full_generation_budget_telemetry() -> None:
    config = RuntimeConfig(output_language="en", frame_pack="en", use_salience=False, max_tokens=12)
    runtime = ChatRuntime(config=config)
    response = runtime.chat("word beginning truth")

    assert response.salience_top_k is None
    assert response.candidates_used is None
    assert len(response.walk_surface.split()) <= 12


def test_salience_changes_candidate_budget_without_changing_response_contract() -> None:
    enabled = ChatRuntime(config=RuntimeConfig(output_language="en", frame_pack="en", salience_top_k=8))
    disabled = ChatRuntime(config=RuntimeConfig(output_language="en", frame_pack="en", use_salience=False, max_tokens=8))

    enabled.chat("word beginning truth")
    disabled.chat("word beginning truth")
    salience_response = enabled.chat("word beginning truth")
    full_response = disabled.chat("word beginning truth")

    assert salience_response.candidates_used is not None
    assert full_response.candidates_used is None
    assert salience_response.surface
    assert full_response.surface
    assert enabled.session.state is not None
    assert disabled.session.state is not None
