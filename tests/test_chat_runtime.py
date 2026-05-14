from __future__ import annotations

import numpy as np

from chat.runtime import ChatResponse, ChatRuntime


def test_chat_runtime_keeps_live_session_across_two_turns() -> None:
    runtime = ChatRuntime()

    first = runtime.chat("light logos", max_tokens=8)
    first_field = runtime.session.state.F.copy()

    second = runtime.chat("light truth", max_tokens=8)
    second_field = runtime.session.state.F.copy()

    assert isinstance(first, ChatResponse)
    assert first.surface.strip()
    assert second.surface.strip()
    assert first.versor_condition < 1e-6
    assert second.versor_condition < 1e-6
    assert second.dialogue_role in {"elaborate", "assert"}
    assert not np.array_equal(second_field, first_field)


def test_chat_runtime_keeps_groundable_oov_tokens_in_open_pack() -> None:
    runtime = ChatRuntime()

    response = runtime.chat("what is דברית", max_tokens=4)

    assert response.surface.strip()
    assert runtime.session.state is not None
    assert runtime.session.vault.recall(runtime.session.state.F, top_k=1)
