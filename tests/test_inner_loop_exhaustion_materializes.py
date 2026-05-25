"""W-012 — InnerLoopExhaustion materializes as ChatResponse (not unhandled exception).

Pin: when the generation walk raises InnerLoopExhaustion, ChatRuntime.chat()
catches it and returns a ChatResponse with refusal_reason populated with the
typed exhaustion code.
"""

from __future__ import annotations

from unittest.mock import patch

from chat.runtime import ChatResponse, ChatRuntime
from generate.exhaustion import InnerLoopExhaustion, RefusalReason


def _make_exhaustion(reason: RefusalReason = RefusalReason.INNER_LOOP_EXHAUSTION):
    return InnerLoopExhaustion(
        reason=reason,
        region_label="test-region",
        step_index=0,
        rejected_attempts=((-1, "word", 0.1),),
    )


class TestInnerLoopExhaustionMaterializes:
    """W-012: InnerLoopExhaustion returns a ChatResponse, not a crash."""

    def test_exhaustion_returns_chat_response_with_refusal_reason(self) -> None:
        runtime = ChatRuntime()
        # Warm the vault so the generate() path is reached.
        runtime.chat("what is truth")
        with patch("chat.runtime.generate", side_effect=_make_exhaustion()):
            response = runtime.chat("what is truth")
        assert isinstance(response, ChatResponse)
        assert response.refusal_reason == RefusalReason.INNER_LOOP_EXHAUSTION.value

    def test_rotor_rejection_materializes(self) -> None:
        runtime = ChatRuntime()
        runtime.chat("what is truth")
        with patch(
            "chat.runtime.generate",
            side_effect=_make_exhaustion(RefusalReason.ROTOR_REJECTION),
        ):
            response = runtime.chat("what is truth")
        assert isinstance(response, ChatResponse)
        assert response.refusal_reason == RefusalReason.ROTOR_REJECTION.value

    def test_happy_path_no_refusal_reason(self) -> None:
        runtime = ChatRuntime()
        response = runtime.chat("what is truth")
        assert isinstance(response, ChatResponse)
        assert response.refusal_reason == ""
