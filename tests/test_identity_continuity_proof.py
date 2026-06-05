"""The identity-continuity PROOF — L11 Phase 4.

"Same identity, not just same bytes" is proven by composing three legs:

1. **Continuity (sufficient):** under a fixed identity, a rebooted resume-mode
   run is BYTE-IDENTICAL to the uninterrupted run (Shape B+ P2b) AND the engine
   identity is unchanged (no break). The resumed life behaves AND is-identified
   as the same.
2. **Load-bearing (structural):** distinct identity packs are distinct engine
   identities — identity is causal, not incidental. (The `identity_divergence`
   lane separately proves distinct identities also *behave* differently.)
3. **Causal contrapositive (necessary):** resuming a checkpoint under a
   DIFFERENT identity raises the continuity break — continuity holds iff the
   identity is the same. Identity is necessary for continuity.

Legs 1 + 3 bracket it: same identity ⟹ continuous; different identity ⟹ break.
"""

from __future__ import annotations

from pathlib import Path

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from core.engine_identity import engine_identity_for_config
from engine_state import get_git_revision
from evals.l10_continuity.runner import run_soak

_PRECISION = RuntimeConfig(identity_pack="precision_first_v1")


def test_resumed_life_is_byte_identical_and_same_identity(tmp_path: Path) -> None:
    # Leg 1: under a fixed (non-default) identity, reboot is fully transparent.
    rebooted = run_soak(
        6, engine_state_dir=tmp_path / "r", reboot_at=(3,), config=_PRECISION
    )
    baseline = run_soak(6, engine_state_dir=tmp_path / "b", config=_PRECISION)
    assert rebooted.trace_hashes() == baseline.trace_hashes()  # behavior continuous
    # And the reboot carried the SAME identity (a fresh runtime over the dir
    # finds no continuity break).
    rt = ChatRuntime(config=_PRECISION, engine_state_path=tmp_path / "r")
    assert rt.identity_continuity_break is False


def test_identity_is_load_bearing_distinct_packs_distinct_identity() -> None:
    # Leg 2: three identity packs -> three distinct engine identities.
    rev = get_git_revision()
    default_id = engine_identity_for_config(RuntimeConfig(), rev)
    precision_id = engine_identity_for_config(_PRECISION, rev)
    generosity_id = engine_identity_for_config(
        RuntimeConfig(identity_pack="generosity_first_v1"), rev
    )
    assert len({default_id, precision_id, generosity_id}) == 3


def test_continuity_breaks_under_a_different_identity(tmp_path: Path) -> None:
    # Leg 3 (contrapositive): a life lived under one identity, resumed under
    # another, raises the break — identity is NECESSARY for continuity.
    state_dir = tmp_path / "es"
    writer = ChatRuntime(config=_PRECISION, engine_state_path=state_dir)
    pipe = CognitiveTurnPipeline(runtime=writer)
    pipe.run("What causes light?")
    pipe.run("What is a concept?")

    import pytest

    with pytest.warns(RuntimeWarning, match="identity continuity break"):
        resumed = ChatRuntime(
            config=RuntimeConfig(identity_pack="generosity_first_v1"),
            engine_state_path=state_dir,
        )
    assert resumed.identity_continuity_break is True
