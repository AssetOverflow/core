"""
session/graph.py — SessionGraph

Append-only DAG of dialogue turns.  Backward edges point from a turn to prior
turns whose output was consumed as a referent during ingest.  Correction passes
walk those edges with true BFS distance, not traversal ordinal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from core.array_codec import decode_array, encode_array


@dataclass(slots=True)
class TurnNode:
    turn_idx: int
    input_versor: np.ndarray
    output_versor: np.ndarray
    tokens_in: tuple[str, ...]
    tokens_out: tuple[str, ...]
    dialogue_role: str
    referent_slots: dict[str, int]
    backward_edges: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_idx": int(self.turn_idx),
            "input_versor": encode_array(self.input_versor),
            "output_versor": encode_array(self.output_versor),
            "tokens_in": list(self.tokens_in),
            "tokens_out": list(self.tokens_out),
            "dialogue_role": self.dialogue_role,
            "referent_slots": dict(self.referent_slots),
            "backward_edges": list(self.backward_edges),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TurnNode":
        return cls(
            turn_idx=int(payload["turn_idx"]),
            input_versor=decode_array(payload["input_versor"]),
            output_versor=decode_array(payload["output_versor"]),
            tokens_in=tuple(payload["tokens_in"]),
            tokens_out=tuple(payload["tokens_out"]),
            dialogue_role=payload["dialogue_role"],
            referent_slots=dict(payload["referent_slots"]),
            backward_edges=list(payload["backward_edges"]),
        )

    def copy_with_output(
        self,
        new_output_versor: np.ndarray,
        new_tokens_out: tuple[str, ...] | None = None,
    ) -> "TurnNode":
        return TurnNode(
            turn_idx=self.turn_idx,
            input_versor=self.input_versor.copy(),
            output_versor=np.asarray(new_output_versor, dtype=np.float32).copy(),
            tokens_in=self.tokens_in,
            tokens_out=new_tokens_out if new_tokens_out is not None else self.tokens_out,
            dialogue_role=self.dialogue_role,
            referent_slots=dict(self.referent_slots),
            backward_edges=list(self.backward_edges),
        )


class SessionGraph:
    """Append-only directed graph of TurnNodes indexed by turn_idx."""

    def __init__(self) -> None:
        self._nodes: list[TurnNode] = []

    def add_turn(
        self,
        turn_idx: int,
        input_versor: np.ndarray,
        output_versor: np.ndarray,
        tokens_in: Sequence[str],
        tokens_out: Sequence[str],
        dialogue_role: str,
        referent_slots: dict[str, int] | None = None,
        backward_edges: list[int] | None = None,
    ) -> TurnNode:
        clean_edges = [
            int(edge)
            for edge in dict.fromkeys(backward_edges or [])
            if 0 <= int(edge) < turn_idx
        ]
        node = TurnNode(
            turn_idx=turn_idx,
            input_versor=np.asarray(input_versor, dtype=np.float32).copy(),
            output_versor=np.asarray(output_versor, dtype=np.float32).copy(),
            tokens_in=tuple(tokens_in),
            tokens_out=tuple(tokens_out),
            dialogue_role=dialogue_role,
            referent_slots=dict(referent_slots or {}),
            backward_edges=clean_edges,
        )
        if turn_idx != len(self._nodes):
            raise ValueError(
                f"turn_idx must append monotonically: got {turn_idx}, expected {len(self._nodes)}"
            )
        self._nodes.append(node)
        return node

    def update_output(
        self,
        turn_idx: int,
        new_output_versor: np.ndarray,
        new_tokens_out: tuple[str, ...] | None = None,
    ) -> TurnNode:
        node = self._nodes[turn_idx]
        updated = node.copy_with_output(new_output_versor, new_tokens_out)
        self._nodes[turn_idx] = updated
        return updated

    def node_at(self, turn_idx: int) -> TurnNode:
        return self._nodes[turn_idx]

    def all_nodes(self) -> list[TurnNode]:
        return list(self._nodes)

    def predecessors_of(self, turn_idx: int) -> list[TurnNode]:
        node = self._nodes[turn_idx]
        return [self._nodes[i] for i in node.backward_edges if i < len(self._nodes)]

    def successors_of(self, turn_idx: int) -> list[TurnNode]:
        return [node for node in self._nodes if turn_idx in node.backward_edges]

    def backward_walk(
        self,
        from_turn: int,
        max_depth: int = 16,
    ) -> list[tuple[int, TurnNode]]:
        """
        BFS backward walk following backward_edges.

        Returns ``(distance, node)`` tuples in BFS order, excluding from_turn.
        Multiple nodes at the same graph depth preserve the same distance.
        """
        if from_turn < 0 or from_turn >= len(self._nodes):
            raise IndexError(f"from_turn out of range: {from_turn}")
        visited: set[int] = {from_turn}
        queue: list[tuple[int, int]] = [(1, idx) for idx in self._nodes[from_turn].backward_edges]
        result: list[tuple[int, TurnNode]] = []
        while queue:
            distance, idx = queue.pop(0)
            if distance > max_depth:
                continue
            if idx in visited or idx >= len(self._nodes) or idx < 0:
                continue
            visited.add(idx)
            node = self._nodes[idx]
            result.append((distance, node))
            queue.extend((distance + 1, parent) for parent in node.backward_edges)
        return result

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self) -> str:
        return f"SessionGraph(turns={len(self._nodes)})"

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [n.to_dict() for n in self._nodes]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionGraph":
        graph = cls()
        graph._nodes = [TurnNode.from_dict(n) for n in payload["nodes"]]
        return graph
