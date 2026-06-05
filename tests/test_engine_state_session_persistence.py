"""Shape B+ Phase D — engine_state session-state I/O + ChatRuntime wiring.

The payoff test (test_chat_runtime_restores_lived_state_across_reboot) is a
direct preview of the L10 spike's P2b: after Phase D, a reboot restores the lived
field/vault/anchor/graph — so resuming continues the same life, not a fresh one
sharing only recognizers/candidates.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from engine_state import EngineStateStore

_PROMPTS = ("What causes light?", "What is a concept?", "What causes rain?", "Hello.")
# Shape B+ persistence is opt-in; the resume-mode config for these tests.
_PERSIST = RuntimeConfig(persist_session_state=True)


# --------------------------------------------------------------------------- #
# EngineStateStore session-state I/O                                            #
# --------------------------------------------------------------------------- #
def test_save_load_session_state_round_trips(tmp_path: Path) -> None:
    store = EngineStateStore(tmp_path)
    snap = {"turn": 3, "state": None, "vault": {"versors": [], "metadata": []}}
    store.save_session_state(snap)
    assert store.load_session_state() == snap


def test_load_session_state_is_none_when_absent(tmp_path: Path) -> None:
    assert EngineStateStore(tmp_path).load_session_state() is None


def test_schema_version_is_2(tmp_path: Path) -> None:
    store = EngineStateStore(tmp_path)
    store.save_manifest(turn_count=5)
    assert store.load_manifest()["schema_version"] == 2


def test_v1_checkpoint_still_loads_without_session_state(tmp_path: Path) -> None:
    # A v1 checkpoint: manifest with schema_version 1 and NO session_state.json.
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "turn_count": 4, "written_at_revision": "x"}),
        encoding="utf-8",
    )
    store = EngineStateStore(tmp_path)
    assert store.load_manifest() is not None  # tolerated (1 <= 2)
    assert store.load_session_state() is None  # -> fresh session fallback


# --------------------------------------------------------------------------- #
# ChatRuntime reboot restores the lived state (the Phase D payoff)              #
# --------------------------------------------------------------------------- #
def _drive(state_dir: Path) -> ChatRuntime:
    runtime = ChatRuntime(config=_PERSIST, engine_state_path=state_dir)
    pipe = CognitiveTurnPipeline(runtime=runtime)
    for p in _PROMPTS:
        pipe.run(p)
    return runtime


def test_chat_runtime_restores_lived_state_across_reboot(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    rt_a = _drive(state_dir)
    ctx_a = rt_a._context

    # Reboot: a fresh runtime over the same checkpoint dir (resume mode on).
    rt_b = ChatRuntime(config=_PERSIST, engine_state_path=state_dir)
    ctx_b = rt_b._context

    # The lived field is restored bit-exactly (NOT fresh/None).
    assert ctx_a.state is not None
    assert ctx_b.state is not None
    assert ctx_b.state.F.tobytes() == ctx_a.state.F.tobytes()
    assert ctx_b.turn == ctx_a.turn
    assert ctx_b.turn > 0  # we actually accumulated turns

    # Anchor restored.
    if ctx_a._anchor_field is not None:
        assert ctx_b._anchor_field is not None
        assert ctx_b._anchor_field.tobytes() == ctx_a._anchor_field.tobytes()

    # Vault is restored (not empty) and recalls identically.
    assert len(ctx_b.vault) == len(ctx_a.vault) > 0
    q = ctx_a.state.F
    assert [(r["index"], r["score"]) for r in ctx_b.vault.recall(q, 5)] == [
        (r["index"], r["score"]) for r in ctx_a.vault.recall(q, 5)
    ]

    # Graph restored.
    assert len(ctx_b.graph) == len(ctx_a.graph) > 0


def test_no_load_state_runtime_starts_fresh(tmp_path: Path) -> None:
    # no_load_state=True must NOT restore even if a checkpoint exists.
    state_dir = tmp_path / "es"
    _drive(state_dir)
    fresh = ChatRuntime(
        config=_PERSIST, engine_state_path=state_dir, no_load_state=True
    )
    assert fresh._context.state is None
    assert fresh._context.turn == 0
