from __future__ import annotations

import numpy as np

from generate.articulation import ArticulationPlan
from generate.surface import SentenceAssembler, SurfaceContext
from session.correction import CorrectionPass
from session.graph import SessionGraph
from session.referents import ReferentRegistry
from vault.decompose import default_gate


def _v(slot: int, scale: float = 1.0) -> np.ndarray:
    arr = np.zeros(32, dtype=np.float32)
    arr[slot] = scale
    return arr


def test_backward_walk_returns_true_graph_distances_for_branching_dag() -> None:
    graph = SessionGraph()
    graph.add_turn(0, _v(0), _v(0), ("a",), ("a",), "assert")
    graph.add_turn(1, _v(1), _v(1), ("b",), ("b",), "assert")
    graph.add_turn(2, _v(2), _v(2), ("c",), ("c",), "assert", backward_edges=[0, 1])
    graph.add_turn(3, _v(3), _v(3), ("d",), ("d",), "assert", backward_edges=[2])

    walked = graph.backward_walk(3)

    assert [(dist, node.turn_idx) for dist, node in walked] == [(1, 2), (2, 0), (2, 1)]


def test_correction_pass_uses_graph_distance_not_bfs_ordinal() -> None:
    graph = SessionGraph()
    base = _v(0)
    graph.add_turn(0, base, base, ("a",), ("a",), "assert")
    graph.add_turn(1, base, base, ("b",), ("b",), "assert")
    graph.add_turn(2, base, base, ("c",), ("c",), "assert", backward_edges=[0, 1])
    graph.add_turn(3, base, base, ("d",), ("d",), "assert", backward_edges=[2])

    result = CorrectionPass(min_alignment=0.0).apply(graph, base, from_turn=3)
    by_turn = {record.turn_idx: record.graph_distance for record in result.records}

    assert by_turn[3] == 0
    assert by_turn[2] == 1
    assert by_turn[0] == 2
    assert by_turn[1] == 2


def test_referent_registry_tracks_only_currently_consumed_sources() -> None:
    registry = ReferentRegistry()
    registry.register("light", _v(4), turn=7)

    assert registry.resolve(["what", "is", "it"]) == ["what", "is", "light"]
    assert registry.consumed_turns() == [7]
    assert registry.consumed_slots() == {"neut_sg": 7}

    assert registry.resolve(["light"]) == ["light"]
    assert registry.consumed_turns() == []
    assert registry.consumed_slots() == {}


def test_surface_coreference_keeps_question_pronoun_lowercase() -> None:
    plan = ArticulationPlan(
        subject="Light",
        predicate="form",
        object=None,
        surface="Light form",
        output_language="en",
        frame_id="test",
    )
    ctx = SurfaceContext(active_referent_surface="Light", active_referent_slot="neut_sg")

    sentence = SentenceAssembler().assemble(plan, (), role="question", context=ctx)

    assert sentence.surface == "Given that Light, does it form?"


def test_surface_elaboration_matches_rendered_elaboration_string() -> None:
    plan = ArticulationPlan(
        subject="light",
        predicate="reveals",
        object="truth",
        surface="light reveals truth",
        output_language="en",
        frame_id="test",
    )
    ctx = SurfaceContext(valence_delta=-1.0)

    sentence = SentenceAssembler().assemble(
        plan,
        ("mercy", "justice"),
        role="elaborate",
        context=ctx,
    )

    assert sentence.elaboration == "mercy but justice"
    assert "mercy but justice" in sentence.surface


def test_running_dialogue_blade_stays_nonzero_after_three_turns() -> None:
    """The running blade must not collapse to zero through grade explosion."""
    from algebra.rotor import make_rotor_from_angle
    from generate.proposition import Proposition

    def _prop(slot: int) -> Proposition:
        relation = make_rotor_from_angle(0.1 * (slot + 1), bivector_idx=6)
        return Proposition(
            subject="a", predicate="b", object_=None, surface="a b",
            frame_id="test",
            subject_versor=_v(0), predicate_versor=_v(1),
            object_versor=None, relation=relation,
        )

    from session.context import SessionContext
    from language_packs import load_pack
    _, vocab = load_pack("en_core_cognition_v1")
    ctx = SessionContext(vocab)

    for i in range(5):
        ctx.record_dialogue(_prop(i))

    blade = ctx.running_dialogue_blade
    assert blade is not None
    assert float(np.linalg.norm(blade)) > 1e-6, (
        "running_dialogue_blade collapsed to zero after multiple turns"
    )


def test_unknown_gate_fires_on_empty_vault_without_self_storage() -> None:
    class EmptyVault:
        def __len__(self) -> int:
            return 0

    decision = default_gate.check(0.0, vault=EmptyVault(), query=_v(0))

    assert decision.fire is True
    assert decision.source == "empty_vault"
