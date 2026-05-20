"""ADR-0075 (C1) — holdout cluster + byte-identity invariant tests.

These tests pin the two invariants named in the ADR:

* ``invariant_realizer_no_illegal_articulation`` — every prompt in
  the C1 holdout cluster is rejected by the guard with the expected
  rule_id, and the surface is replaced with the bounded disclosure
  string.
* ``invariant_realizer_guard_byte_identity_on_currently_passing_cases``
  — every currently-passing cognition-lane DEFINITION prompt
  continues to produce a guard-accepted surface byte-identical to
  pre-C1 behavior.

The holdout cluster's exit code is the canonical coherence-floor
gate (see ``evals/realizer_guard/run_holdout.py``).
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals.realizer_guard.run_holdout import (
    _HOLDOUT_PROMPTS,
    _PRIMING_PROMPTS,
    run_holdout,
)
from generate.realizer_guard import DISCLOSURE_SURFACE


# ---------- invariant_realizer_no_illegal_articulation ----------


@pytest.fixture(scope="module")
def holdout_report():
    """Run the cluster once per test module — parametrized tests
    then read from the cached report instead of re-running the full
    six-prompt cluster each time."""
    return run_holdout(emit_json=True)


def test_holdout_cluster_all_claims_supported(holdout_report):
    assert holdout_report["all_claims_supported"] is True
    assert holdout_report["failures"] == []


def test_holdout_cluster_size(holdout_report):
    assert len(holdout_report["cells"]) == len(_HOLDOUT_PROMPTS)
    assert len(holdout_report["cells"]) == 6


@pytest.mark.parametrize("prompt,expected_rule", list(_HOLDOUT_PROMPTS))
def test_each_holdout_prompt_rejected(
    prompt: str, expected_rule: str, holdout_report,
):
    cell = next(c for c in holdout_report["cells"] if c["prompt"] == prompt)
    assert cell["realizer_guard_status"] == "rejected"
    assert cell["realizer_guard_rule"] == expected_rule
    assert cell["surface"] == DISCLOSURE_SURFACE
    assert cell["walk_surface"] != DISCLOSURE_SURFACE
    assert cell["walk_surface"].strip() != ""
    assert cell["grounding_source"] == "none"


def test_every_rejected_walk_surface_violates_R2(holdout_report):
    """Sanity: each preserved pre-guard candidate must in fact
    violate the rule it was rejected under (round-trip check).

    Uses the live runtime's pack POS table because the C1 rules
    fail-open on unknown POS — a null-lookup would not re-trigger
    R2 since the original trigger depends on the pack having
    classified the offending token (e.g. ``thought``) as ``NOUN``.
    """
    from chat.runtime import ChatRuntime
    from core.config import RuntimeConfig
    from generate.realizer_guard import check_surface

    rt = ChatRuntime(config=RuntimeConfig(
        register_pack_id="default_neutral_v1",
    ))
    for cell in holdout_report["cells"]:
        v = check_surface(
            cell["walk_surface"],
            pos_lookup=rt._pos_by_surface.get,
        )
        assert v.status == "rejected", (
            f"walk_surface {cell['walk_surface']!r} should still "
            f"violate the rule under round-trip check"
        )
        assert v.rule_id == cell["realizer_guard_rule"]


# ---------- byte-identity invariant on currently-passing cases ----------


_CURRENTLY_PASSING_PROMPTS: tuple[tuple[str, str], ...] = (
    (
        "What is light?",
        "Light is a source of revelation that makes things knowable. "
        "pack-grounded (en_core_cognition_v1).",
    ),
    (
        "Define knowledge.",
        "Knowledge is justified understanding grounded in evidence "
        "and recall. pack-grounded (en_core_cognition_v1).",
    ),
    (
        "What is truth?",
        "Truth is a claim or state grounded by evidence and coherent "
        "judgment. pack-grounded (en_core_cognition_v1).",
    ),
)


@pytest.mark.parametrize("prompt,expected_surface", _CURRENTLY_PASSING_PROMPTS)
def test_currently_passing_cases_byte_identical(
    prompt: str, expected_surface: str,
):
    """ADR-0075 byte-identity invariant.

    For every currently-passing cognition-lane DEFINITION case, the
    post-C1 surface must be byte-identical to the pre-C1 surface.
    If this regresses, the guard rule set is too aggressive and
    must be narrowed before merge.
    """
    rt = ChatRuntime(config=RuntimeConfig(
        register_pack_id="default_neutral_v1",
    ))
    pipeline = CognitiveTurnPipeline(runtime=rt)
    pipeline.run(prompt)
    te = rt.turn_log[-1]
    assert te.realizer_guard_status == "ok"
    assert te.realizer_guard_rule == ""
    assert te.surface == expected_surface


def test_priming_sequence_all_pass_guard():
    """Every priming prompt must pass the guard cleanly — the
    holdout cluster's rejection signal would be meaningless if the
    priming itself were also being rejected."""
    rt = ChatRuntime(config=RuntimeConfig(
        register_pack_id="default_neutral_v1",
    ))
    pipeline = CognitiveTurnPipeline(runtime=rt)
    for p in _PRIMING_PROMPTS:
        pipeline.run(p)
        te = rt.turn_log[-1]
        assert te.realizer_guard_status == "ok", (
            f"Priming prompt {p!r} was rejected; holdout signal "
            f"would be confounded.  Guard rule was "
            f"{te.realizer_guard_rule!r}, surface "
            f"{te.surface!r}"
        )
