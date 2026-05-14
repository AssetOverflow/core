"""
Dialogue move selection from proposition relation blades.

The proposition layer constructs X_prompt ^ X_field. Dialogue reads that
grade-2 relation against the prior relation blade and chooses the next move
kind: assertion, elaboration, question/contrast, or refutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from algebra.cga import cga_inner, outer_product
from field.state import FieldState
from generate.proposition import FrameRegistry, Proposition, propose

DialogueRole = Literal["assert", "elaborate", "question", "refute"]

_PARALLEL_THRESHOLD = 0.35
_ANTI_PARALLEL_THRESHOLD = -0.35
_ORTHOGONAL_THRESHOLD = 0.20


@dataclass(frozen=True, slots=True)
class DialogueTurn:
    proposition: Proposition
    outer_product_blade: np.ndarray = field(repr=False)

    def __post_init__(self) -> None:
        blade = np.asarray(self.outer_product_blade, dtype=np.float32).copy()
        object.__setattr__(self, "outer_product_blade", blade)


def blade_alignment(blade: np.ndarray, reference: np.ndarray) -> float:
    """
    Return signed orientation of two relation blades.

    Positive values mean same plane orientation, near-zero values mean
    orthogonal relation, and negative values mean the same relation reversed.
    The scalar is derived from CORE's algebraic inner product, not an external
    approximate metric.
    """
    blade = np.asarray(blade, dtype=np.float32)
    reference = np.asarray(reference, dtype=np.float32)
    blade_norm = abs(cga_inner(blade, blade)) ** 0.5
    reference_norm = abs(cga_inner(reference, reference)) ** 0.5
    if blade_norm < 1e-8 or reference_norm < 1e-8:
        return 0.0
    return float(-cga_inner(blade, reference) / (blade_norm * reference_norm))


def classify_dialogue_blade(
    blade: np.ndarray,
    reference_blade: np.ndarray | None = None,
) -> DialogueRole:
    """
    Classify a relation blade as the next dialogue move.

    With no prior relation the engine has no contrastive plane yet, so the
    first move is an assertion. After that:
      same orientation -> elaboration
      near-orthogonal -> question/contrast
      reversed orientation -> refutation
    """
    if reference_blade is None:
        return "assert"

    alignment = blade_alignment(blade, reference_blade)
    if alignment >= _PARALLEL_THRESHOLD:
        return "elaborate"
    if alignment <= _ANTI_PARALLEL_THRESHOLD:
        return "refute"
    if abs(alignment) <= _ORTHOGONAL_THRESHOLD:
        return "question"
    return "question"


def trajectory_blade(blades: tuple[np.ndarray, ...] | list[np.ndarray]) -> np.ndarray | None:
    """Fold a dialogue path into the running outer product of its blades."""
    if not blades:
        return None
    running = np.asarray(blades[0], dtype=np.float32).copy()
    for blade in blades[1:]:
        running = outer_product(running, blade)
    return running


def propose_dialogue(
    field_state: FieldState,
    vault,
    vocab,
    frame_registry: FrameRegistry,
    reference_blade: np.ndarray | None = None,
    output_lang: str | None = None,
) -> Proposition:
    """
    Generate a proposition through a dialogue-role constrained frame choice.
    """
    base = propose(field_state, None, vocab, frame_registry, output_lang=output_lang)
    role = classify_dialogue_blade(base.relation, reference_blade)
    frame = frame_registry.select_dialogue(base.relation, role)
    role_registry = FrameRegistry((frame,))
    proposition = propose(field_state, vault, vocab, role_registry, output_lang=output_lang)
    if reference_blade is not None and blade_alignment(proposition.relation, reference_blade) < 0.0:
        proposition = Proposition(
            subject=proposition.subject,
            predicate=proposition.predicate,
            object_=proposition.object_,
            surface=proposition.surface,
            frame_id=proposition.frame_id,
            subject_versor=proposition.subject_versor,
            predicate_versor=proposition.predicate_versor,
            object_versor=proposition.object_versor,
            relation=-proposition.relation,
        )
    return proposition
