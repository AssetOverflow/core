"""Word-selection tracer for the articulation/realization path.

Captures every nearest-neighbor vocabulary lookup performed during a turn:
  - slot name (subject / predicate / object)
  - input versor (32-d float vector, copied)
  - top-K candidate words by CGA inner product score
  - chosen word
  - any morphology applied

Also records each realization step (subject, predicate, object, tense,
aspect, plural, negation) emitted by ``realize_semantic`` / ``realize_target``.

External instrumentation only — instruments via module-level function
swaps that are reverted in ``finally``.  No edits to generate/, vocab/,
or algebra/ source files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from algebra.backend import _CGA_INNER_METRIC  # diagonal Cl(4,1) metric (±1 per blade)
from chat.runtime import ChatRuntime


@dataclass(frozen=True)
class WordSelectionStep:
    """A single nearest-neighbor lookup observed during articulation."""

    slot: str  # 'subject' | 'predicate' | 'object'
    input_versor: np.ndarray  # shape (32,), copy — safe to retain
    top_candidates: tuple[tuple[str, float], ...]  # (word, cga_inner_score)
    chosen: str
    morphology: dict[str, Any]  # tense/aspect/plural/negation/lemma/surface, if any
    output_language: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "top_candidates": [list(c) for c in self.top_candidates],
            "chosen": self.chosen,
            "morphology": dict(self.morphology),
            "output_language": self.output_language,
        }


@dataclass(frozen=True)
class RealizationStep:
    """A semantic realization step (subject/predicate/object + morphology)."""

    subject: str
    predicate: str
    obj: str | None
    tense: str | None
    aspect: str | None
    negated: bool
    quantifier: str | None
    move: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "obj": self.obj,
            "tense": self.tense,
            "aspect": self.aspect,
            "negated": self.negated,
            "quantifier": self.quantifier,
            "move": self.move,
        }


@dataclass
class RealizationTrace:
    """Full trace from one turn: word selections + realization steps."""

    steps: list[WordSelectionStep] = field(default_factory=list)
    realization_steps: list[RealizationStep] = field(default_factory=list)
    surface: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "steps": [s.as_dict() for s in self.steps],
            "realization_steps": [r.as_dict() for r in self.realization_steps],
            "surface": self.surface,
        }


def _morphology_summary(vocab: Any, word: str) -> dict[str, Any]:
    """Extract morphology fields for a word, returning an empty dict if none."""
    entry = vocab.morphology_for_word(word)
    if entry is None:
        return {}
    summary: dict[str, Any] = {}
    # MorphologyEntry fields vary; collect any present attributes.
    for attr in ("lemma", "surface", "tense", "aspect", "plural", "number", "negation", "person", "gender", "pos"):
        value = getattr(entry, attr, None)
        if value is not None:
            summary[attr] = value
    return summary


def _topk_candidates(
    vocab: Any,
    versor: np.ndarray,
    candidate_indices: np.ndarray,
    k: int = 5,
) -> tuple[tuple[str, float], ...]:
    """Compute top-K candidates by CGA inner product over the candidate set.

    Vectorised via the diagonal Cl(4,1) metric — same kernel as
    ``algebra.backend.vault_recall``.  Exact, deterministic, no approximation.
    Used only for tracing; never fed back into the realizer's surface.
    """
    if len(candidate_indices) == 0:
        return ()
    idx = np.asarray(candidate_indices, dtype=np.int64)
    # Stack candidate versors into one (N, 32) matrix; the vocab stores
    # them as a list of 32-vectors.
    versors_list = [vocab._versors[int(i)] for i in idx]
    M = np.asarray(versors_list, dtype=np.float32)
    q = np.asarray(versor, dtype=np.float32).reshape(-1)
    # Diagonal weighted dot-product, vectorised serial fold (same
    # component order as scalar cga_inner so scores are bit-identical
    # to the per-versor scan we replaced).
    scores = np.zeros(M.shape[0], dtype=np.float32)
    for c in range(M.shape[1]):
        scores += (_CGA_INNER_METRIC[c] * M[:, c]) * q[c]
    k_eff = max(1, min(int(k), scores.shape[0]))
    if k_eff < scores.shape[0]:
        cand = np.argpartition(-scores, k_eff - 1)[:k_eff]
    else:
        cand = np.arange(scores.shape[0])
    order = np.lexsort((cand, -scores[cand]))
    cand = cand[order]
    return tuple(
        (vocab._words[int(idx[int(c)])], float(scores[int(c)]))
        for c in cand
    )


def trace_realization(
    runtime_or_pipeline: Any,
    text: str,
    *,
    top_k: int = 5,
    max_tokens: int | None = None,
) -> RealizationTrace:
    """Run one chat turn (or pipeline turn) while tracing every word lookup.

    Accepts either a ``ChatRuntime`` (calls ``.chat``) or a
    ``CognitiveTurnPipeline`` (calls ``.run``).  A pipeline is preferred
    because the pipeline path invokes ``realize_semantic`` even when the
    runtime's unknown-domain gate fires, so realization steps are captured
    regardless of grounding.

    Instruments ``generate.articulation._resolve_slot`` and
    ``generate.realizer.realize_semantic`` for the duration of this call,
    then restores them.  Does NOT modify the realizer/articulation source.
    """
    trace = RealizationTrace()

    from generate import articulation as articulation_mod
    from generate import realizer as realizer_mod

    orig_resolve_slot = articulation_mod._resolve_slot
    orig_candidate_indices = articulation_mod._candidate_indices
    orig_surface_for_word = articulation_mod._surface_for_word
    orig_realize_semantic = realizer_mod.realize_semantic
    orig_resolve_obj = realizer_mod._resolve_obj

    # Track slot order within a single realize() call.  Reset on every
    # articulation.realize() entry; resolve_slot has no slot label itself,
    # so we synthesize it from invocation order: subject, predicate, object.
    slot_state: dict[str, int] = {"counter": 0}
    _SLOT_ORDER = ("subject", "predicate", "object")

    def traced_resolve_slot(
        versor: np.ndarray | None,
        vocab: Any,
        output_language: str,
    ) -> str | None:
        slot_idx = slot_state["counter"]
        slot_state["counter"] = slot_idx + 1
        slot_name = _SLOT_ORDER[slot_idx] if slot_idx < len(_SLOT_ORDER) else f"slot_{slot_idx}"
        if versor is None:
            return None
        cand = orig_candidate_indices(vocab, output_language)
        chosen_word, _chosen_idx = vocab.nearest(versor, candidate_indices=cand)
        top = _topk_candidates(vocab, versor, cand, k=top_k)
        morph = _morphology_summary(vocab, chosen_word)
        trace.steps.append(
            WordSelectionStep(
                slot=slot_name,
                input_versor=np.asarray(versor, dtype=float).copy(),
                top_candidates=top,
                chosen=chosen_word,
                morphology=morph,
                output_language=output_language,
            )
        )
        return orig_surface_for_word(vocab, chosen_word)

    # Reset slot counter at each realize() entry.  Patch articulation.realize
    # via a wrapper that resets the slot_state counter before delegating.
    orig_realize = articulation_mod.realize

    def traced_realize(*args: Any, **kwargs: Any) -> Any:
        slot_state["counter"] = 0
        return orig_realize(*args, **kwargs)

    def traced_realize_semantic(target: Any, graph: Any = None) -> Any:
        plan = orig_realize_semantic(target, graph)
        # Record the realization steps directly from the target/graph
        # without re-running the realizer.
        if target is not None and target.steps:
            for step in target.steps:
                obj = orig_resolve_obj(step, graph) if graph is not None else None
                trace.realization_steps.append(
                    RealizationStep(
                        subject=step.subject,
                        predicate=step.predicate,
                        obj=obj,
                        tense=step.tense,
                        aspect=step.aspect,
                        negated=step.negated,
                        quantifier=step.quantifier,
                        move=step.move.value,
                    )
                )
        return plan

    articulation_mod._resolve_slot = traced_resolve_slot
    articulation_mod.realize = traced_realize
    realizer_mod.realize_semantic = traced_realize_semantic

    # Also patch the symbol referenced by the pipeline module, since it
    # was imported by name at module load time.
    try:
        from core.cognition import pipeline as pipeline_mod
        orig_pipeline_realize_semantic = pipeline_mod.realize_semantic
        pipeline_mod.realize_semantic = traced_realize_semantic
    except ImportError:
        pipeline_mod = None
        orig_pipeline_realize_semantic = None

    try:
        if hasattr(runtime_or_pipeline, "run") and hasattr(runtime_or_pipeline, "runtime"):
            # CognitiveTurnPipeline
            result = runtime_or_pipeline.run(text, max_tokens=max_tokens)
            trace.surface = result.articulation_surface or result.surface or ""
        else:
            # ChatRuntime
            response = runtime_or_pipeline.chat(text, max_tokens=max_tokens)
            trace.surface = response.articulation_surface or response.surface or ""
    finally:
        articulation_mod._resolve_slot = orig_resolve_slot
        articulation_mod.realize = orig_realize
        realizer_mod.realize_semantic = orig_realize_semantic
        if pipeline_mod is not None and orig_pipeline_realize_semantic is not None:
            pipeline_mod.realize_semantic = orig_pipeline_realize_semantic

    return trace
