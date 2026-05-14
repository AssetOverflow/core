from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from generate.proposition import Proposition
from vocab.manifold import VocabManifold


@dataclass(frozen=True, slots=True)
class ArticulationPlan:
    subject: str
    predicate: str
    object: str | None
    surface: str
    output_language: str
    frame_id: str


def _candidate_indices(vocab: VocabManifold, output_language: str) -> np.ndarray:
    indices = vocab.indices_for_language(output_language)
    if len(indices) == 0:
        raise ValueError(f"No articulation candidates for output language {output_language!r}.")
    return indices


def _surface_for_word(vocab: VocabManifold, word: str) -> str:
    morphology = vocab.morphology_for_word(word)
    if morphology is None:
        return word
    return morphology.lemma or morphology.surface


def _resolve_slot(
    versor: np.ndarray | None,
    vocab: VocabManifold,
    output_language: str,
) -> str | None:
    if versor is None:
        return None
    word, _ = vocab.nearest(
        versor,
        candidate_indices=_candidate_indices(vocab, output_language),
    )
    return _surface_for_word(vocab, word)


def _assemble(subject: str, predicate: str, object_: str | None, output_language: str) -> str:
    if output_language == "he":
        parts = [predicate, subject]
        if object_ is not None:
            parts.append(object_)
        return " ".join(part for part in parts if part)
    if output_language == "grc":
        parts = [subject]
        if object_ is not None:
            parts.append(object_)
        parts.append(predicate)
        return " ".join(part for part in parts if part)
    parts = [subject, predicate]
    if object_ is not None:
        parts.append(object_)
    return " ".join(part for part in parts if part)


def realize(
    proposition: Proposition,
    vocab: VocabManifold,
    output_language: str = "en",
) -> ArticulationPlan:
    """
    Map proposition frame slots to morphology-backed target-language surface forms.

    Slot resolution is purely geometric:
      1. take the slot versor from Proposition
      2. restrict candidates to the configured output language
      3. choose nearest manifold point by CGA inner product through VocabManifold
      4. return MorphologyEntry.lemma when available, else surface
    """
    subject = _resolve_slot(proposition.subject_versor, vocab, output_language)
    predicate = _resolve_slot(proposition.predicate_versor, vocab, output_language)
    object_ = _resolve_slot(proposition.object_versor, vocab, output_language)

    if subject is None or predicate is None:
        raise ValueError("Articulation requires subject and predicate slot versors.")

    return ArticulationPlan(
        subject=subject,
        predicate=predicate,
        object=object_,
        surface=_assemble(subject, predicate, object_, output_language),
        output_language=output_language,
        frame_id=proposition.frame_id,
    )
