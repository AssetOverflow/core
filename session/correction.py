"""
session/correction.py — CorrectionPass

Backward conjugate propagation through the SessionGraph.

When a user corrects the engine ("no, I meant X" / "that's wrong"),
CorrectionPass walks the session graph backward from the current turn
and applies a scaled conjugate operator to each prior node whose output
versor has nonzero inner product with the correction versor.

Math
----
Let V_t be the output versor at turn t.
Let C be the correction versor (derived from the user's corrective input).
Let alpha_t = |CGA_inner(V_t, C)| — alignment of turn t with the correction.
The corrected output at turn t is:

    V_t' = V_t + alpha_t * decay(d) * (C - V_t)

where d is the graph distance from the current turn to turn t, and

    decay(d) = DECAY_BASE ** d

This is a simple linear blend biased toward C at nearby turns and
fading to identity at distant turns.  It does not recompute propositions
or surface strings — it only updates the stored output versors in the
SessionGraph so that future recall from the vault is drawn toward C.

After the graph update, the caller is responsible for:
  1. Storing corrected versors back into VaultStore (if desired).
  2. Re-ingesting the current context so the next turn starts from
     the corrected field state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from algebra.backend import cga_inner

if TYPE_CHECKING:
    from session.graph import SessionGraph, TurnNode


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Geometric decay per graph-distance step.
DECAY_BASE: float = 0.6

#: Minimum alignment (|CGA inner product|) required to apply correction.
MIN_ALIGNMENT: float = 0.05


# ---------------------------------------------------------------------------
# CorrectionRecord — result for one corrected turn
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CorrectionRecord:
    turn_idx: int
    graph_distance: int
    alignment: float          # |CGA_inner(V_t, C)|
    decay: float              # DECAY_BASE ** graph_distance
    blend_weight: float       # alpha_t * decay
    old_versor: np.ndarray
    new_versor: np.ndarray


# ---------------------------------------------------------------------------
# CorrectionPass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CorrectionResult:
    correction_versor: np.ndarray
    records: tuple[CorrectionRecord, ...]   # one per modified turn
    turns_affected: int
    turns_skipped: int   # below MIN_ALIGNMENT threshold


class CorrectionPass:
    """
    Apply backward conjugate correction from a target turn through the
    session graph.

    Parameters
    ----------
    decay_base    : geometric decay per hop (default 0.6)
    min_alignment : minimum |CGA inner| to apply correction (default 0.05)
    max_depth     : maximum backward walk depth (default 16)
    """

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
        """
        Walk backward from *from_turn* and apply the correction.

        Parameters
        ----------
        graph             : the session's SessionGraph
        correction_versor : the field vector encoding the correction intent
        from_turn         : starting turn index; -1 means the latest turn

        Returns
        -------
        CorrectionResult detailing every modified TurnNode.
        """
        n_turns = len(graph)
        if n_turns == 0:
            return CorrectionResult(
                correction_versor=correction_versor,
                records=(),
                turns_affected=0,
                turns_skipped=0,
            )

        start = from_turn if from_turn >= 0 else n_turns - 1
        start = min(start, n_turns - 1)

        C = np.asarray(correction_versor, dtype=np.float32)

        # Walk backward: start turn + all its backward predecessors
        prior_nodes = graph.backward_walk(start, max_depth=self._max_depth)
        # Include start node itself at distance 0
        start_node = graph.node_at(start)
        nodes_with_distance: list[tuple[int, "TurnNode"]] = [(0, start_node)] + [
            (d + 1, n) for d, n in enumerate(prior_nodes)
        ]

        records: list[CorrectionRecord] = []
        skipped = 0

        for dist, node in nodes_with_distance:
            V = node.output_versor
            raw_alignment = float(cga_inner(V, C))
            alignment = abs(raw_alignment)

            if alignment < self._min_alignment:
                skipped += 1
                continue

            decay = self._decay_base ** dist
            blend = alignment * decay

            # Corrected versor: blend toward C
            new_V = V + blend * (C - V)
            # Renormalise to prevent drift
            norm = float(np.linalg.norm(new_V))
            if norm > 1e-8:
                new_V = new_V / norm * float(np.linalg.norm(V))

            updated_node = graph.update_output(node.turn_idx, new_V)
            record = CorrectionRecord(
                turn_idx=node.turn_idx,
                graph_distance=dist,
                alignment=alignment,
                decay=decay,
                blend_weight=blend,
                old_versor=V.copy(),
                new_versor=updated_node.output_versor.copy(),
            )
            records.append(record)

        return CorrectionResult(
            correction_versor=C,
            records=tuple(records),
            turns_affected=len(records),
            turns_skipped=skipped,
        )
