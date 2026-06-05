"""EngineIdentity lineage — L11 Phase 2.

Every checkpoint manifest stamps the content-derived ``engine_identity`` the
engine was running under, plus the ``parent_engine_identity`` of the prior
checkpoint — a git-like lineage chain. With a stable ratified substrate the
identity is constant (identity == parent: one stable life); a ratified change
would make identity != parent (the bump). Across reboot the chain is continuous:
the resumed life's checkpoint descends from the pre-reboot identity.
"""

from __future__ import annotations

import json
from pathlib import Path

from chat.runtime import ChatRuntime, get_git_revision
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from core.engine_identity import engine_identity_for_config


def _manifest(state_dir: Path) -> dict:
    return json.loads((state_dir / "manifest.json").read_text(encoding="utf-8"))


def _drive(state_dir: Path, n: int, config: RuntimeConfig | None = None) -> ChatRuntime:
    runtime = ChatRuntime(config=config or RuntimeConfig(), engine_state_path=state_dir)
    pipe = CognitiveTurnPipeline(runtime=runtime)
    for _ in range(n):
        pipe.run("What causes light?")
    return runtime


def test_manifest_stamps_content_derived_engine_identity(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    rt = _drive(state_dir, 1)
    m = _manifest(state_dir)
    assert m["engine_identity"] == rt._engine_identity
    # It IS the content-derived identity of the ratified substrate.
    assert m["engine_identity"] == engine_identity_for_config(
        RuntimeConfig(), get_git_revision()
    )


def test_lineage_is_stable_across_a_continuous_run(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    _drive(state_dir, 2)  # 2 checkpoints
    m = _manifest(state_dir)
    # Stable substrate -> identity == parent (the life is one continuous identity).
    assert m["engine_identity"] == m["parent_engine_identity"]


def test_lineage_is_continuous_across_reboot(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    rt_a = _drive(state_dir, 2)
    id_a = rt_a._engine_identity

    # Reboot: a fresh runtime over the same checkpoint dir.
    rt_b = ChatRuntime(config=RuntimeConfig(), engine_state_path=state_dir)
    # The resumed life inherits the pre-reboot identity as its lineage parent.
    assert rt_b._loaded_engine_identity == id_a
    assert rt_b._engine_identity == id_a  # same substrate -> same identity

    pipe = CognitiveTurnPipeline(runtime=rt_b)
    pipe.run("What is a concept?")
    m = _manifest(state_dir)
    assert m["parent_engine_identity"] == id_a  # descends from the prior life
    assert m["engine_identity"] == id_a


def test_different_identity_pack_is_a_different_identity(tmp_path: Path) -> None:
    rt_default = ChatRuntime(
        config=RuntimeConfig(), engine_state_path=tmp_path / "a", no_load_state=True
    )
    rt_precision = ChatRuntime(
        config=RuntimeConfig(identity_pack="precision_first_v1"),
        engine_state_path=tmp_path / "b",
        no_load_state=True,
    )
    assert rt_default._engine_identity != rt_precision._engine_identity
