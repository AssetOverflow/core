"""Reboot identity verification — L11 Phase 3.

On reboot the engine recomputes its identity from the current ratified substrate
and compares it to the identity stamped in the checkpoint. A match = continuous
identity. A mismatch = the substrate changed while the engine was down (a pack
mutated), so resuming would carry the lived state into a DIFFERENT identity —
surfaced (warn + ``identity_continuity_break`` flag) by default, refused under
``strict_identity_continuity``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from core.engine_identity import IdentityContinuityError


def _drive(state_dir: Path, n: int = 2, config: RuntimeConfig | None = None) -> None:
    runtime = ChatRuntime(config=config or RuntimeConfig(), engine_state_path=state_dir)
    pipe = CognitiveTurnPipeline(runtime=runtime)
    for _ in range(n):
        pipe.run("What causes light?")


def test_same_substrate_reboot_has_no_break(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    _drive(state_dir)
    rt = ChatRuntime(config=RuntimeConfig(), engine_state_path=state_dir)
    assert rt.identity_continuity_break is False


def test_substrate_change_during_downtime_surfaces_break(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    _drive(state_dir)  # stamps the default identity
    # Boot under a different identity pack over the same checkpoint dir.
    with pytest.warns(RuntimeWarning, match="identity continuity break"):
        rt = ChatRuntime(
            config=RuntimeConfig(identity_pack="precision_first_v1"),
            engine_state_path=state_dir,
        )
    assert rt.identity_continuity_break is True


def test_strict_mode_refuses_on_identity_mismatch(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    _drive(state_dir)
    with pytest.raises(IdentityContinuityError):
        ChatRuntime(
            config=RuntimeConfig(
                identity_pack="precision_first_v1", strict_identity_continuity=True
            ),
            engine_state_path=state_dir,
        )


def test_strict_mode_allows_matching_identity(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    _drive(state_dir)
    # Same substrate + strict mode -> boots cleanly, no break.
    rt = ChatRuntime(
        config=RuntimeConfig(strict_identity_continuity=True),
        engine_state_path=state_dir,
    )
    assert rt.identity_continuity_break is False


def test_genesis_runtime_has_no_break(tmp_path: Path) -> None:
    # No checkpoint to compare against -> no break.
    rt = ChatRuntime(config=RuntimeConfig(), engine_state_path=tmp_path / "fresh")
    assert rt.identity_continuity_break is False
