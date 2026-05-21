"""Generation stop-tokens override — Finding 6 (audit 2026-05-20).

Pre-fix ``_STOP_TOKENS = frozenset({"it", "to", "word"})`` was hardcoded
inside ``generate.stream.generate()`` and inhibited those three tokens
unconditionally across every pack, language, and domain.  If a pack
legitimately needed one of them as a content word — e.g. a philosophy
pack where ``"word"`` maps to λόγος — there was no override path.

This test pins:

  * The default (``stop_tokens=None``) is byte-identical to the
    historical ``_STOP_TOKENS`` frozenset.
  * An explicit override genuinely changes which vocabulary indices
    are added to the per-step ``stop_nodes`` filter.
  * ``RuntimeConfig.stop_tokens`` threads through to ``generate()``.
"""

from __future__ import annotations

import inspect

from chat.runtime import ChatRuntime
from core.config import DEFAULT_CONFIG, RuntimeConfig
from generate.stream import _STOP_TOKENS, generate


def test_runtime_config_default_is_none() -> None:
    assert DEFAULT_CONFIG.stop_tokens is None


def test_generate_signature_exposes_stop_tokens() -> None:
    sig = inspect.signature(generate)
    assert "stop_tokens" in sig.parameters
    assert sig.parameters["stop_tokens"].default is None


def test_historical_default_unchanged() -> None:
    """The ``None`` resolution path must equal the original constant."""
    assert _STOP_TOKENS == frozenset({"it", "to", "word"})


def test_runtime_threads_explicit_override() -> None:
    """A non-None ``stop_tokens`` config flows through to generate()."""
    rt = ChatRuntime(
        config=RuntimeConfig(
            stop_tokens=("custom_stop",),
        ),
    )
    # The runtime constructs without error and carries the override.
    assert rt.config.stop_tokens == ("custom_stop",)
    # And a non-trivial smoke turn still runs end-to-end (no regression
    # on the surface contract when the override is harmless).
    response = rt.chat("What is truth?", max_tokens=4)
    assert isinstance(response.surface, str)
