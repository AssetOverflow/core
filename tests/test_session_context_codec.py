"""SessionContext.snapshot/restore — Shape B+ Phase C.

Composes the FieldState (Phase A) and VaultStore (Phase B) codecs with new
codecs for SessionGraph, ReferentRegistry, Proposition, and DialogueTurn. Exit
gate: a real session, snapshotted and restored into a fresh context, is
field-equal — field bit-exact, vault recall identical, graph/referents/dialogue
preserved (including the _slots<->_history object aliasing).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from core.cognition.pipeline import CognitiveTurnPipeline
from generate.dialogue import DialogueTurn
from generate.proposition import Proposition
from session.context import SessionContext
from session.graph import SessionGraph, TurnNode
from session.referents import ReferentEntry, ReferentRegistry

_PROMPTS = ("What causes light?", "What is a concept?", "What causes rain?", "Hello.")


def _v(seed: int) -> np.ndarray:
    v = np.zeros(32, dtype=np.float32)
    v[0] = 1.0
    v[(seed % 31) + 1] = 0.01 * (seed + 1)
    return v


# --------------------------------------------------------------------------- #
# Component round-trips                                                          #
# --------------------------------------------------------------------------- #
def test_turnnode_and_graph_round_trip() -> None:
    g = SessionGraph()
    g.add_turn(0, _v(1), _v(2), ("a", "b"), ("c",), "assert", {"neut_sg": 0}, [])
    g.add_turn(1, _v(3), _v(4), ("d",), ("e", "f"), "question", {"neut_sg": 0}, [0])
    r = SessionGraph.from_dict(g.to_dict())
    assert len(r) == 2
    for orig, rec in zip(g.all_nodes(), r.all_nodes()):
        assert rec.input_versor.tobytes() == orig.input_versor.tobytes()
        assert rec.output_versor.tobytes() == orig.output_versor.tobytes()
        assert rec.tokens_in == orig.tokens_in
        assert rec.backward_edges == orig.backward_edges
        assert rec.referent_slots == orig.referent_slots


def test_referent_registry_round_trip_preserves_slot_history_aliasing() -> None:
    reg = ReferentRegistry()
    reg.register("cat", _v(5), turn=0, slot="neut_sg")
    reg.register("dog", _v(6), turn=1, slot="neut_sg")  # same slot, twice
    restored = ReferentRegistry.from_dict(reg.to_dict())
    # Active slot points to the latest ("dog") and is the SAME object as the
    # corresponding history entry (the aliasing update_turn_versor relies on).
    active = restored.active_referent("neut_sg")
    assert active is not None and active.surface == "dog"
    assert active is restored.history()[-1]
    assert restored.history()[0].versor.tobytes() == reg.history()[0].versor.tobytes()


def test_proposition_and_dialogue_turn_round_trip() -> None:
    prop = Proposition(
        subject="s", predicate="p", object_="o", surface="s p o",
        frame_id="f", subject_versor=_v(7), predicate_versor=_v(8),
        object_versor=_v(9), relation=_v(10),
    )
    turn = DialogueTurn(proposition=prop, outer_product_blade=_v(11))
    rec = DialogueTurn.from_dict(turn.to_dict())
    assert rec.proposition.subject == "s"
    assert rec.proposition.subject_versor.tobytes() == prop.subject_versor.tobytes()
    assert rec.proposition.object_versor is not None
    assert rec.proposition.relation.tobytes() == prop.relation.tobytes()
    assert rec.outer_product_blade.tobytes() == turn.outer_product_blade.tobytes()


def test_proposition_none_object_versor_round_trips() -> None:
    prop = Proposition(
        subject="s", predicate="p", object_=None, surface="s p",
        frame_id="f", subject_versor=_v(1), predicate_versor=_v(2),
    )
    rec = Proposition.from_dict(prop.to_dict())
    assert rec.object_versor is None
    assert rec.object_ is None


# --------------------------------------------------------------------------- #
# Integration: a real session snapshot -> restore is field-equal                #
# --------------------------------------------------------------------------- #
def _drive_session(tmp_path: Path) -> SessionContext:
    runtime = ChatRuntime(config=RuntimeConfig(), engine_state_path=tmp_path / "es")
    pipe = CognitiveTurnPipeline(runtime=runtime)
    for p in _PROMPTS:
        pipe.run(p)
    return runtime._context


def test_session_context_snapshot_restore_is_field_equal(tmp_path: Path) -> None:
    ctx = _drive_session(tmp_path)
    snap = ctx.snapshot()

    restored = SessionContext(vocab=ctx.vocab, persona=ctx.persona)
    restored.restore(snap)

    # Field bit-exact + closure preserved.
    assert (ctx.state is None) == (restored.state is None)
    if ctx.state is not None:
        assert restored.state.F.tobytes() == ctx.state.F.tobytes()
    assert restored.turn == ctx.turn

    # Anchor bit-exact.
    if ctx._anchor_field is not None:
        assert restored._anchor_field.tobytes() == ctx._anchor_field.tobytes()

    # Vault recall identical (exact CGA preserved through the whole compose).
    query = ctx.state.F if ctx.state is not None else _v(0)
    before = ctx.vault.recall(query, top_k=5)
    after = restored.vault.recall(query, top_k=5)
    assert [(r["index"], r["score"]) for r in before] == [
        (r["index"], r["score"]) for r in after
    ]

    # Graph preserved.
    assert len(restored.graph) == len(ctx.graph)
    for orig, rec in zip(ctx.graph.all_nodes(), restored.graph.all_nodes()):
        assert rec.output_versor.tobytes() == orig.output_versor.tobytes()
        assert rec.tokens_in == orig.tokens_in

    # Referents + dialogue history preserved.
    assert restored.referents.active_slots() == ctx.referents.active_slots()
    assert len(restored._dialogue_history_compat) == len(ctx._dialogue_history_compat)
    assert (ctx.running_dialogue_blade is None) == (
        restored.running_dialogue_blade is None
    )
    if ctx.running_dialogue_blade is not None:
        assert (
            restored.running_dialogue_blade.tobytes()
            == ctx.running_dialogue_blade.tobytes()
        )


def test_session_context_snapshot_is_json_safe(tmp_path: Path) -> None:
    import json

    ctx = _drive_session(tmp_path)
    blob = json.dumps(ctx.snapshot())
    restored = SessionContext(vocab=ctx.vocab, persona=ctx.persona)
    restored.restore(json.loads(blob))
    assert restored.turn == ctx.turn
