"""
session/graph.py — SessionGraph

A directed acyclic graph of TurnNodes that replaces the flat
`dialogue_history: list[DialogueTurn]` in SessionContext.

Each TurnNode holds:
  - the input versor (field state after ingest)
  - the output versor (field state after generation)
  - the surface tokens emitted
  - the dialogue role
  - referent slots active at this turn
  - backward edges to any earlier turn whose output versor was consumed
    as a referent during this turn's ingest

Backward edges enable CorrectionPass (session/correction.py) to walk the
graph retroactively and apply conjugate corrections to affected turns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


# ---------------------------------------------------------------------------
# TurnNode
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TurnNode:
    turn_idx: int
    input_versor: np.ndarray           # field F after ingest
    output_versor: np.ndarray          # field F after generation
    tokens_in: tuple[str, ...]         # tokenised user input
    tokens_out: tuple[str, ...]        # emitted surface tokens
    dialogue_role: str                 # "assert" | "elaborate" | "question" | "refute"
    referent_slots: dict[str, int]     # slot_name → turn_idx of registered referent
    backward_edges: list[int] = field(default_factory=list)  # turn indices consumed as referents

    def copy_with_output(
        self,
        new_output_versor: np.ndarray,
        new_tokens_out: tuple[str, ...] | None = None,
    ) -> "TurnNode":
        """Return a new TurnNode with a corrected output versor."""
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


# ---------------------------------------------------------------------------
# SessionGraph
# ---------------------------------------------------------------------------

class SessionGraph:
    """
    Append-only directed graph of TurnNodes.

    Nodes are indexed by turn_idx (0-based, monotonically increasing).
    Backward edges record which earlier turns provided referents consumed
    during ingest of the current turn.
    """

    def __init__(self) -> None:
        self._nodes: list[TurnNode] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

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
        """Append a new TurnNode and return it."""
        node = TurnNode(
            turn_idx=turn_idx,
            input_versor=np.asarray(input_versor, dtype=np.float32).copy(),
            output_versor=np.asarray(output_versor, dtype=np.float32).copy(),
            tokens_in=tuple(tokens_in),
            tokens_out=tuple(tokens_out),
            dialogue_role=dialogue_role,
            referent_slots=referent_slots or {},
            backward_edges=backward_edges or [],
        )
        self._nodes.append(node)
        return node

    def update_output(
        self,
        turn_idx: int,
        new_output_versor: np.ndarray,
        new_tokens_out: tuple[str, ...] | None = None,
    ) -> TurnNode:
        """
        Replace the output versor of an existing node (used by CorrectionPass).
        Returns the updated node.
        """
        node = self._nodes[turn_idx]
        updated = node.copy_with_output(new_output_versor, new_tokens_out)
        self._nodes[turn_idx] = updated
        return updated

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def node_at(self, turn_idx: int) -> TurnNode:
        return self._nodes[turn_idx]

    def all_nodes(self) -> list[TurnNode]:
        return list(self._nodes)

    def predecessors_of(self, turn_idx: int) -> list[TurnNode]:
        """Return all TurnNodes that the given turn consumed as referents."""
        node = self._nodes[turn_idx]
        return [self._nodes[i] for i in node.backward_edges if i < len(self._nodes)]

    def successors_of(self, turn_idx: int) -> list[TurnNode]:
        """Return all TurnNodes that consumed the given turn as a referent."""
        return [
            n for n in self._nodes
            if turn_idx in n.backward_edges
        ]

    def backward_walk(
        self,
        from_turn: int,
        max_depth: int = 16,
    ) -> list[TurnNode]:
        """
        BFS backward walk from *from_turn* following backward_edges.
        Returns nodes in BFS order (closest turns first), excluding
        *from_turn* itself.  Cycles are impossible in an append-only DAG
        but the visited set guards against malformed inputs.
        """
        visited: set[int] = {from_turn}
        queue: list[int] = list(self._nodes[from_turn].backward_edges)
        result: list[TurnNode] = []
        depth = 0
        while queue and depth < max_depth:
            next_queue: list[int] = []
            for idx in queue:
                if idx in visited or idx >= len(self._nodes):
                    continue
                visited.add(idx)
                result.append(self._nodes[idx])
                next_queue.extend(self._nodes[idx].backward_edges)
            queue = next_queue
            depth += 1
        return result

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self) -> str:
        return f"SessionGraph(turns={len(self._nodes)})"
