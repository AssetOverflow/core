"""Phase 3 — end-to-end live contemplation through ``ChatRuntime``.

Pins that turning on ``RuntimeConfig.discourse_contemplation`` causes
the runtime to populate ``runtime.last_plan_findings`` after each
turn where the discourse planner engaged, and leaves it empty
otherwise.  This is the load-bearing wiring claim — without this
test a future refactor could silently drop the contemplation pass
and the runtime would still pass every other gate.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from core.contemplation.schema import FindingKind
from teaching.epistemic import EpistemicStatus


# ---------------------------------------------------------------------------
# Disabled by default — no findings even on multi-move plans
# ---------------------------------------------------------------------------


def test_findings_empty_when_contemplation_disabled() -> None:
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=False))
    rt.chat("What is truth, and why does it matter?")
    assert rt.last_plan_findings == ()


# ---------------------------------------------------------------------------
# Enabled — multi-move predicate-monotonous plan triggers WEAK_SURFACE
# ---------------------------------------------------------------------------


def test_compound_prompt_triggers_weak_surface_finding() -> None:
    """The compound prompt "What is truth, and why does it matter?"
    plans 6 moves; 3 of them share the ``belongs_to`` predicate.
    Phase 3's predicate-monotony rule should fire."""
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat("What is truth, and why does it matter?")
    findings = rt.last_plan_findings
    assert findings, "expected at least one finding on this prompt"
    kinds = {f.kind for f in findings}
    assert FindingKind.WEAK_SURFACE in kinds
    # Pin the specific finding's content
    weak = next(f for f in findings if f.kind is FindingKind.WEAK_SURFACE)
    assert weak.subject == "truth"
    assert weak.predicate == "predicate_repeats_in_plan"
    assert weak.object == "belongs_to"
    assert weak.epistemic_status is EpistemicStatus.SPECULATIVE


# ---------------------------------------------------------------------------
# BRIEF prompts (fast-path) do not engage the planner → no findings
# ---------------------------------------------------------------------------


def test_brief_prompt_yields_no_findings() -> None:
    """``What is knowledge?`` is BRIEF mode; the runtime fast-path
    short-circuits the planner before any plan is built — there is
    nothing to contemplate."""
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat("What is knowledge?")
    assert rt.last_plan_findings == ()


# ---------------------------------------------------------------------------
# Findings do not leak across turns
# ---------------------------------------------------------------------------


def test_findings_reset_between_turns() -> None:
    """A turn that populates findings followed by a turn that does
    not must leave ``last_plan_findings == ()``.  Pinned because a
    prior bug would have kept the previous turn's findings live."""
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat("What is truth, and why does it matter?")  # populates
    assert rt.last_plan_findings  # sanity
    rt.chat("What is knowledge?")  # BRIEF — should clear
    assert rt.last_plan_findings == ()


# ---------------------------------------------------------------------------
# Determinism: same prompt → byte-equal findings
# ---------------------------------------------------------------------------


def test_findings_are_deterministic_across_runs() -> None:
    rt1 = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt2 = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt1.chat("What is truth, and why does it matter?")
    rt2.chat("What is truth, and why does it matter?")
    ids_1 = tuple(f.finding_id for f in rt1.last_plan_findings)
    ids_2 = tuple(f.finding_id for f in rt2.last_plan_findings)
    assert ids_1 == ids_2


# ---------------------------------------------------------------------------
# All emitted findings remain SPECULATIVE (doctrine pin)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "What is truth, and why does it matter?",
        "Tell me about memory.",
        "Explain truth.",
        "Compare knowledge and wisdom.",
    ],
)
def test_findings_always_speculative(prompt: str) -> None:
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat(prompt)
    for f in rt.last_plan_findings:
        assert f.epistemic_status is EpistemicStatus.SPECULATIVE
