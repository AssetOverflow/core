"""Epistemic carrier for recognized propositions — ADR-0144.

EpistemicNode wraps a RecognitionOutcome with an append-only provenance
chain of state transitions.  EpistemicGraph holds one or more nodes for
a single turn plus the recognizer identity used to produce them.

Both types are frozen and serialisable to/from JSON so the carrier
participates in the determinism guarantee inherited from ADR-0143.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from recognition.outcome import RecognitionOutcome


@dataclass(frozen=True, slots=True)
class EpistemicTransition:
    """A single epistemic state transition with its provenance.

    ``from_state`` and ``to_state`` are values from the ADR-0142 taxonomy.
    ``source`` identifies the subsystem that caused the transition (e.g.
    ``"verifier"``, ``"vault"``).  ``reason`` is human-readable audit text
    and is not load-bearing for replay.
    """

    from_state: str
    to_state: str
    source: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class EpistemicNode:
    """One recognized proposition with full provenance chain.

    ``node_id`` is deterministic: the teaching_set_id of the DerivedRecognizer
    used, suffixed with ``:<turn_index>`` — byte-identical across runs on the
    same recognizer and input.

    ``recognition_outcome`` is the frozen ADR-0143 output carrying the
    FeatureBundle (or refusal reason) and RecognitionProvenance.

    ``transitions`` accumulates provenance as subsystems transition the state.
    Empty on construction — the recognizer's emission state is authoritative
    until a subsystem appends a transition.
    """

    node_id: str
    recognition_outcome: RecognitionOutcome
    transitions: tuple[EpistemicTransition, ...] = ()

    @property
    def epistemic_state(self) -> str:
        """Current state: last transition's to_state if any, else outcome.state."""
        if self.transitions:
            return self.transitions[-1].to_state
        return self.recognition_outcome.state

    def with_transition(self, transition: EpistemicTransition) -> "EpistemicNode":
        """Return a new node with the transition appended (immutable update)."""
        return EpistemicNode(
            node_id=self.node_id,
            recognition_outcome=self.recognition_outcome,
            transitions=(*self.transitions, transition),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "epistemic_state": self.epistemic_state,
            "node_id": self.node_id,
            "recognition_outcome": self.recognition_outcome.as_dict(),
            "transitions": [t.as_dict() for t in self.transitions],
        }


@dataclass(frozen=True, slots=True)
class EpistemicGraph:
    """Per-turn epistemic carrier for recognized propositions.

    ``nodes`` is a tuple of EpistemicNodes in recognition order.
    ADR-0144 Phase 1 emits exactly one node per admitted turn.

    ``recognizer_id`` is the ``teaching_set_id`` of the DerivedRecognizer
    used — byte-identical across runs on the same recognizer and input,
    carrying replay identity.

    ``to_json()`` must be byte-identical across runs on the same input and
    recognizer (determinism guarantee from ADR-0143).
    """

    nodes: tuple[EpistemicNode, ...]
    recognizer_id: str

    def get(self, node_id: str) -> EpistemicNode | None:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.as_dict() for n in self.nodes],
            "recognizer_id": self.recognizer_id,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )


__all__ = [
    "EpistemicGraph",
    "EpistemicNode",
    "EpistemicTransition",
]
