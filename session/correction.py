from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from algebra.backend import cga_inner

if TYPE_CHECKING:
    from session.graph import SessionGraph, TurnNode

DECAY_BASE: float = 0.6
MIN_ALIGNMENT: float = 0.05


@dataclass(frozen=True, slots=True)
class CorrectionRecord:
    turn_idx: int
    graph_distance: int
    alignment: float
    decay: float
    blend_weight: float
    old_versor: np.ndarray
    new_versor: np.ndarray


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    correction_versor: np.ndarray
    records: tuple[CorrectionRecord, ...]
    turns_affected: int
    turns_skipped: int


class CorrectionPass:
    def __init__(
        self,
        decay_base: float = DECAY_BASE,
        min_alignment: float = MIN_ALIGNMENT,
        max_depth: int = 16,
    ) -> None:
        self._decay_base = decay_base
        self._min_alignment = min_alignment
        self._max_depth = max_depth

    def apply(
        self,
        graph: "SessionGraph",
        correction_versor: np.ndarray,
        from_turn: int = -1,
    ) -> CorrectionResult:
        n_turns = len(graph)
        C = np.asarray(correction_versor, dtype=np.float32)
        if n_turns == 0:
            return CorrectionResult(C, (), 0, 0)

        start = from_turn if from_turn >= 0 else n_turns - 1
        start = min(start, n_turns - 1)

        start_node = graph.node_at(start)
        prior_nodes_with_dist = graph.backward_walk(start, max_depth=self._max_depth)
        nodes_with_distance: list[tuple[int, "TurnNode"]] = [(0, start_node)] + prior_nodes_with_dist

        records: list[CorrectionRecord] = []
        skipped = 0
        for dist, node in nodes_with_distance:
            V = node.output_versor
            alignment = abs(float(cga_inner(V, C)))
            if alignment < self._min_alignment:
                skipped += 1
                continue

            decay = self._decay_base ** dist
            blend = alignment * decay
            new_V = V + blend * (C - V)
            norm = float(np.linalg.norm(new_V))
            old_norm = float(np.linalg.norm(V))
            if norm > 1e-8:
                new_V = new_V / norm * old_norm

            updated = graph.update_output(node.turn_idx, new_V)
            records.append(
                CorrectionRecord(
                    turn_idx=node.turn_idx,
                    graph_distance=dist,
                    alignment=alignment,
                    decay=decay,
                    blend_weight=blend,
                    old_versor=V.copy(),
                    new_versor=updated.output_versor.copy(),
                )
            )

        return CorrectionResult(
            correction_versor=C,
            records=tuple(records),
            turns_affected=len(records),
            turns_skipped=skipped,
        )
