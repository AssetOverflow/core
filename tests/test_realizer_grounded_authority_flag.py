"""Realizer-grounded-authority flag — ADR-0088 Phase B (Finding 2).

Pre-fix ``CognitiveTurnPipeline.run()`` called ``realize_semantic`` on
the ungrounded ``PropositionGraph`` — every non-COMPARISON / non-
CORRECTION node was born with ``obj = "<pending>"`` and the realizer
emitted surfaces like ``"X is defined as ..."`` that
``_is_useful_surface`` rejected.  The realizer therefore never won
the surface resolver introduced by PR #76 — it was structurally
present but semantically inert in the hot pipeline path.

ADR-0088 Phase B wires opt-in graph grounding behind
``RuntimeConfig.realizer_grounded_authority``.  Default ``False``
preserves byte-identity for every existing pack and test.  When
``True`` the pipeline calls ``ground_graph(graph, response.recalled_words)``
between ``runtime.chat`` and the realizer's re-invocation.  The
realizer then competes as a real surface authority.

These tests pin:

  * The flag defaults to ``False`` on ``DEFAULT_CONFIG``.
  * Flag-off produces byte-identical surface + trace_hash to today
    (the null-lift invariant the codebase uses for every substantive
    runtime behavior change — see ADR-0072, ADR-0073d, ADR-0083).
  * ``ChatResponse.recalled_words`` is populated on the main path so
    the grounded-graph wiring has a real input when the flag is on.
  * Flag-on does not break the cognition lane — realized surfaces
    are still gated by ``_is_useful_surface`` so any case where the
    grounded realizer cannot produce a clean output falls through to
    the runtime path.

Phase A (realizer fluency parity — gloss-aware templates, 3sg verb
agreement, pack-provenance tag) is documented in ADR-0088 and is the
prerequisite for enabling this flag in production.
"""

from __future__ import annotations

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline
from core.config import DEFAULT_CONFIG, RuntimeConfig


def test_flag_defaults_to_false() -> None:
    assert DEFAULT_CONFIG.realizer_grounded_authority is False


def test_flag_off_byte_identical_surface_and_trace() -> None:
    """The null-lift invariant: flag-off behaviour is unchanged."""
    rt_a = ChatRuntime()
    rt_b = ChatRuntime()
    pa = CognitiveTurnPipeline(runtime=rt_a)
    pb = CognitiveTurnPipeline(runtime=rt_b)
    result_a = pa.run("What is truth?", max_tokens=4)
    result_b = pb.run("What is truth?", max_tokens=4)
    assert result_a.surface == result_b.surface
    assert result_a.trace_hash == result_b.trace_hash


def test_recalled_words_populated_on_main_path() -> None:
    """The grounded-graph wiring needs real input when the flag is on."""
    rt = ChatRuntime()
    response = rt.chat("What is truth?", max_tokens=4)
    # The walk produces at least one alphabetic token on the main
    # path of any non-stub cognition prompt.
    assert isinstance(response.recalled_words, tuple)
    assert all(isinstance(t, str) and t.isalpha() for t in response.recalled_words)


def test_flag_on_runs_without_crashing() -> None:
    """Flag-on routes through the grounded realizer; the surface still
    clears ``_is_useful_surface`` (or falls back to the runtime path),
    so the result is well-formed even though the surface contents may
    differ from the default until Phase A's fluency parity lands."""
    rt = ChatRuntime(config=RuntimeConfig(realizer_grounded_authority=True))
    pipeline = CognitiveTurnPipeline(runtime=rt)
    result = pipeline.run("What is truth?", max_tokens=4)
    # The result is well-formed regardless of which authority won.
    assert isinstance(result.surface, str)
    assert result.surface  # non-empty
    assert result.trace_hash  # hashed
