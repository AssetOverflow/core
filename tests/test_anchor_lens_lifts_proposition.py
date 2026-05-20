"""anchor_lens_lifts_proposition — load-bearing L1.3 invariant (ADR-0073c).

When a non-null lens engages on a cognition-pack lemma:
  - the surface differs from the unanchored baseline
  - the surface carries the lens annotation [lens(<id>):<mode>]
  - the trace_hash differs (the proposition has changed)

The complementary null-lift invariant (L1.2) continues to hold for the
unanchored sentinel and default_unanchored_v1 — pinned by
``tests/test_anchor_lens_null_lift.py``.

Cognition prompts used:
  "What is knowledge?"   — grc_logos_v1 engages, he_logos_v1 does not
  "What is truth?"       — he_logos_v1  engages, grc_logos_v1 does not

Together they exercise both lenses and confirm engagement is
substrate-scoped, not blanket.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig


_KNOWLEDGE_PROMPT = "What is knowledge?"
_TRUTH_PROMPT = "What is truth?"


def _run(lens_id: str | None, prompt: str):
    rt = ChatRuntime(config=RuntimeConfig(anchor_lens_id=lens_id))
    pipeline = CognitiveTurnPipeline(runtime=rt)
    result = pipeline.run(prompt)
    response = rt.turn_log[-1]
    return result, response


# ---------- grc_logos_v1 engages on "knowledge" ----------


def test_grc_logos_v1_surface_differs_from_unanchored_on_knowledge():
    _, base = _run(None, _KNOWLEDGE_PROMPT)
    _, lensed = _run("grc_logos_v1", _KNOWLEDGE_PROMPT)
    assert base.surface != lensed.surface


def test_grc_logos_v1_surface_carries_annotation_on_knowledge():
    _, lensed = _run("grc_logos_v1", _KNOWLEDGE_PROMPT)
    assert "[lens(grc_logos_v1):systematic]" in lensed.surface


def test_grc_logos_v1_trace_hash_differs_from_unanchored_on_knowledge():
    base_result, _ = _run(None, _KNOWLEDGE_PROMPT)
    lensed_result, _ = _run("grc_logos_v1", _KNOWLEDGE_PROMPT)
    assert base_result.trace_hash != lensed_result.trace_hash


# ---------- he_logos_v1 engages on "truth" ----------


def test_he_logos_v1_surface_differs_from_unanchored_on_truth():
    _, base = _run(None, _TRUTH_PROMPT)
    _, lensed = _run("he_logos_v1", _TRUTH_PROMPT)
    assert base.surface != lensed.surface


def test_he_logos_v1_surface_carries_annotation_on_truth():
    _, lensed = _run("he_logos_v1", _TRUTH_PROMPT)
    assert "[lens(he_logos_v1):covenant-verity]" in lensed.surface


def test_he_logos_v1_trace_hash_differs_from_unanchored_on_truth():
    base_result, _ = _run(None, _TRUTH_PROMPT)
    lensed_result, _ = _run("he_logos_v1", _TRUTH_PROMPT)
    assert base_result.trace_hash != lensed_result.trace_hash


# ---------- engagement is substrate-scoped (cross-lens isolation) ----------


def test_grc_logos_v1_does_not_engage_on_truth():
    """grc lens does not touch truth — surface byte-identical to baseline."""
    _, base = _run(None, _TRUTH_PROMPT)
    _, grc = _run("grc_logos_v1", _TRUTH_PROMPT)
    assert base.surface == grc.surface
    assert "lens(" not in grc.surface


def test_he_logos_v1_does_not_engage_on_knowledge():
    """he lens does not touch knowledge — surface byte-identical to baseline."""
    _, base = _run(None, _KNOWLEDGE_PROMPT)
    _, he = _run("he_logos_v1", _KNOWLEDGE_PROMPT)
    assert base.surface == he.surface
    assert "lens(" not in he.surface


# ---------- three-way trace_hash divergence (the load-bearing claim) ----------


def test_three_way_surface_distinct_on_knowledge():
    """{unanchored, grc, he} produce two distinct surfaces on knowledge
    (grc engages, he does not so he == unanchored)."""
    _, base = _run(None, _KNOWLEDGE_PROMPT)
    _, grc = _run("grc_logos_v1", _KNOWLEDGE_PROMPT)
    _, he = _run("he_logos_v1", _KNOWLEDGE_PROMPT)
    distinct = {base.surface, grc.surface, he.surface}
    assert len(distinct) == 2  # grc differs; he matches base


def test_three_way_surface_distinct_on_truth():
    """Symmetric: he engages on truth, grc does not."""
    _, base = _run(None, _TRUTH_PROMPT)
    _, grc = _run("grc_logos_v1", _TRUTH_PROMPT)
    _, he = _run("he_logos_v1", _TRUTH_PROMPT)
    distinct = {base.surface, grc.surface, he.surface}
    assert len(distinct) == 2  # he differs; grc matches base


# ---------- replay determinism (same lens × same input → same output) ----------


@pytest.mark.parametrize("lens_id", ["grc_logos_v1", "he_logos_v1"])
@pytest.mark.parametrize("prompt", [_KNOWLEDGE_PROMPT, _TRUTH_PROMPT])
def test_lens_engagement_is_deterministic(lens_id: str, prompt: str):
    a_result, a = _run(lens_id, prompt)
    b_result, b = _run(lens_id, prompt)
    assert a.surface == b.surface
    assert a_result.trace_hash == b_result.trace_hash


# ---------- register-tour seam still holds under each lens ----------


@pytest.mark.parametrize("lens_id", [None, "default_unanchored_v1",
                                     "grc_logos_v1", "he_logos_v1"])
def test_register_seam_within_lens_holds(lens_id: str | None):
    """Per ADR-0073 orthogonality: within a fixed lens, varying register
    keeps trace_hash constant.  L1.3 must preserve R5's register-tour
    invariant inside every lens scope."""
    pipeline_neutral = CognitiveTurnPipeline(
        runtime=ChatRuntime(config=RuntimeConfig(
            register_pack_id="default_neutral_v1",
            anchor_lens_id=lens_id,
        ))
    )
    pipeline_convivial = CognitiveTurnPipeline(
        runtime=ChatRuntime(config=RuntimeConfig(
            register_pack_id="convivial_v1",
            anchor_lens_id=lens_id,
        ))
    )
    n = pipeline_neutral.run(_KNOWLEDGE_PROMPT)
    c = pipeline_convivial.run(_KNOWLEDGE_PROMPT)
    assert n.trace_hash == c.trace_hash, (
        f"register-tour seam broken under lens={lens_id!r}: "
        f"neutral trace_hash {n.trace_hash[:12]}... != "
        f"convivial trace_hash {c.trace_hash[:12]}..."
    )
