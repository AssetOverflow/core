"""
Structured proposition generation.

A proposition is the first structured assertion above the surface walk:
prompt and field form a relation blade; a frame is selected by exact CGA
inner product against that relation; vocabulary points then instantiate the
frame slots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from algebra.cga import cga_inner, outer_product
from field.state import FieldState
from generate.admissibility import AdmissibilityRegion, filter_candidates
from generate.stream import _articulate
from teaching.epistemic import EpistemicStatus

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_STOP_SURFACES = frozenset({"what", "who", "how", "why", "when", "which", "it", "to"})


@dataclass(frozen=True, slots=True)
class FrameSlot:
    name: str
    required: bool
    semantic_role: str | None = None
    agreement_target: str | None = None


@dataclass(frozen=True, slots=True)
class PropositionFrame:
    frame_id: str
    language: str
    predicate_type: str
    dialogue_role: str
    slots: tuple[FrameSlot, ...]
    constraints: tuple[str, ...] = field(default_factory=tuple)
    relation: np.ndarray = field(default_factory=lambda: np.zeros(32, dtype=np.float32))

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", tuple(self.slots))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "relation", np.asarray(self.relation, dtype=np.float32).copy())


@dataclass(frozen=True, slots=True)
class Proposition:
    subject: str
    predicate: str
    object_: str | None
    surface: str
    frame_id: str
    subject_versor: np.ndarray
    predicate_versor: np.ndarray
    object_versor: np.ndarray | None = None
    relation: np.ndarray = field(default_factory=lambda: np.zeros(32, dtype=np.float32))
    relation_norm: float = 0.0

    def __post_init__(self) -> None:
        subject_versor = np.asarray(self.subject_versor, dtype=np.float32).copy()
        predicate_versor = np.asarray(self.predicate_versor, dtype=np.float32).copy()
        relation = np.asarray(self.relation, dtype=np.float32).copy()
        object.__setattr__(self, "subject_versor", subject_versor)
        object.__setattr__(self, "predicate_versor", predicate_versor)
        if self.object_versor is not None:
            object_versor = np.asarray(self.object_versor, dtype=np.float32).copy()
            object.__setattr__(self, "object_versor", object_versor)
        object.__setattr__(self, "relation", relation)
        object.__setattr__(self, "relation_norm", float(np.linalg.norm(relation)))


class FrameRegistry:
    """Exact frame selection over precompiled frame relation blades."""

    def __init__(self, frames: Iterable[PropositionFrame]) -> None:
        self._frames = tuple(frames)
        if not self._frames:
            raise ValueError("FrameRegistry requires at least one frame.")

    @classmethod
    def from_pack(cls, pack: str, vocab) -> "FrameRegistry":
        pack_dir = _PROJECT_ROOT / "packs" / pack
        if not pack_dir.exists() and pack == "el":
            pack_dir = _PROJECT_ROOT / "packs" / "grc"
        if not pack_dir.exists() and pack == "grc":
            pack_dir = _PROJECT_ROOT / "packs" / "el"
        return cls.from_jsonl(pack_dir / "frames.jsonl", vocab)

    @classmethod
    def from_jsonl(cls, path: str | Path, vocab) -> "FrameRegistry":
        path = Path(path)
        frames: list[PropositionFrame] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            frame = _parse_frame(payload, vocab)
            frames.append(frame)
        return cls(frames)

    def select(self, relation: np.ndarray) -> PropositionFrame:
        relation = np.asarray(relation, dtype=np.float32)
        return max(self._frames, key=lambda frame: cga_inner(relation, frame.relation))

    def select_dialogue(self, relation: np.ndarray, dialogue_role: str) -> PropositionFrame:
        relation = np.asarray(relation, dtype=np.float32)
        candidates = tuple(frame for frame in self._frames if frame.dialogue_role == dialogue_role)
        if not candidates:
            candidates = self._frames
        return max(candidates, key=lambda frame: cga_inner(relation, frame.relation))

    def __iter__(self):
        return iter(self._frames)

    def __len__(self) -> int:
        return len(self._frames)


def _candidate_indices_for_language(vocab, output_lang: str | None) -> np.ndarray | None:
    if output_lang is None:
        return None
    indices_for_language = getattr(vocab, "indices_for_language", None)
    if indices_for_language is None:
        return None
    indices = indices_for_language(output_lang)
    if len(indices) == 0:
        raise ValueError(f"No proposition candidates for output language {output_lang!r}.")
    return indices


def propose(
    field_state: FieldState,
    vault,
    vocab,
    frame_registry: FrameRegistry,
    output_lang: str | None = None,
    region: AdmissibilityRegion | None = None,
) -> Proposition:
    """Generate one structured proposition from the live field.

    ``region`` is the ADR-0022 admissibility region.  Default ``None``
    preserves existing behavior during the transition window
    (ADR-0022 §TBD-3).  When supplied, its allowed-index set is
    intersected with the language candidate set before subject /
    predicate / object selection.
    """
    prompt = _prompt_versor(field_state)
    frame_relation = _frame_query_relation(field_state)
    frame = frame_registry.select(frame_relation)
    candidate_indices = _candidate_indices_for_language(vocab, output_lang)
    if region is not None and not region.is_unconstrained():
        candidate_indices = filter_candidates(region, candidate_indices)
        if candidate_indices is not None and len(candidate_indices) == 0:
            # ADR-0022 §2: an empty admissible set must fail honestly,
            # not be silently relaxed.  Re-raise as ValueError so the
            # call site can route through the existing unknown-domain
            # surface (_UNKNOWN_DOMAIN_SURFACE).
            raise ValueError(
                f"AdmissibilityRegion[{region.label}] left no proposition candidates."
            )

    subject_word, subject_idx = _nearest_content_word(
        vocab,
        prompt,
        exclude_indices=frozenset(),
        preferred_pos=frozenset({"noun", "pronoun"}),
        candidate_indices=candidate_indices,
    )
    predicate_word, predicate_idx = _nearest_content_word(
        vocab,
        prompt,
        exclude_indices=frozenset({subject_idx}),
        candidate_indices=candidate_indices,
    )

    subject_versor = vocab.get_versor_at(subject_idx)
    predicate_versor = vocab.get_versor_at(predicate_idx)
    relation = outer_product(subject_versor, predicate_versor)
    if float(np.linalg.norm(relation)) < 1e-8:
        relation = frame_relation

    object_word: str | None = None
    object_versor: np.ndarray | None = None
    if _frame_wants_object(frame):
        object_word, object_idx = _nearest_content_word(
            vocab,
            relation,
            exclude_indices=frozenset({subject_idx, predicate_idx}),
            preferred_pos=frozenset({"noun", "pronoun"}),
            candidate_indices=candidate_indices,
        )
        object_versor = vocab.get_versor_at(object_idx)

    subject = _articulate(vocab, subject_word)
    predicate = _articulate(vocab, predicate_word)
    object_surface = _articulate(vocab, object_word) if object_word is not None else None
    surface = _render_surface(frame, subject, predicate, object_surface)

    proposition = Proposition(
        subject=subject,
        predicate=predicate,
        object_=object_surface,
        surface=surface,
        frame_id=frame.frame_id,
        subject_versor=subject_versor,
        predicate_versor=predicate_versor,
        object_versor=object_versor,
        relation=relation,
    )
    if vault is not None:
        # SPECULATIVE per ADR-0021 §3: the system's own articulated
        # output has not passed coherence judgment.  Storing it as
        # COHERENT would create a self-reinforcing fabrication loop
        # (Leak C from the 2026-05-17 epistemic audit) — propose,
        # store, recall own output as evidence, propose again.  The
        # SPECULATIVE stamp keeps the entry retrievable for session
        # context while excluding it from inference paths that pass
        # min_status=COHERENT.
        vault.store(
            proposition.subject_versor,
            {"kind": "proposition", "proposition": proposition},
            epistemic_status=EpistemicStatus.SPECULATIVE,
        )
    return proposition


def _parse_frame(payload: dict, vocab) -> PropositionFrame:
    slots = tuple(
        FrameSlot(
            name=slot["name"],
            required=bool(slot["required"]),
            semantic_role=slot.get("semantic_role"),
            agreement_target=slot.get("agreement_target"),
        )
        for slot in payload.get("slots", ())
    )
    relation = _frame_relation(payload, vocab)
    return PropositionFrame(
        frame_id=payload["frame_id"],
        language=payload["language"],
        predicate_type=payload["predicate_type"],
        dialogue_role=payload.get("dialogue_role", "assert"),
        slots=slots,
        constraints=tuple(payload.get("constraints", ())),
        relation=relation,
    )


def _frame_relation(payload: dict, vocab) -> np.ndarray:
    left = _first_existing(vocab, _role_anchor_candidates(payload))
    right = _first_existing(vocab, _predicate_anchor_candidates(payload))
    if left is None or right is None:
        left = vocab.get_word_at(0)
        right = vocab.get_word_at(1 if len(vocab) > 1 else 0)
    return outer_product(vocab.get_versor(left), vocab.get_versor(right))


def _role_anchor_candidates(payload: dict) -> tuple[str, ...]:
    text = " ".join(
        [payload.get("predicate_type", "")]
        + [
            " ".join(str(slot.get(k, "")) for k in ("name", "semantic_role"))
            for slot in payload.get("slots", ())
        ]
    ).lower()
    if "creation" in text or "agent" in text:
        return ("create", "κτίζω", "ברא", "λόγος", "דבר", "word")
    if "pros" in text or "direction" in text or "accompan" in text:
        return ("with", "λόγος", "דבר", "word")
    return (
        "light",
        "φῶς",
        "אוֹר",
        "אור",
        "truth",
        "ἀλήθεια",
        "אמת",
        "word",
        "λόγος",
        "דבר",
    )


def _predicate_anchor_candidates(payload: dict) -> tuple[str, ...]:
    predicate_type = payload.get("predicate_type", "").lower()
    if "existential" in predicate_type:
        return ("exist", "is", "was", "ζωή", "חיים")
    if "relational" in predicate_type or "prepositional" in predicate_type:
        return ("with", "to", "λόγος", "דבר")
    if "creation" in predicate_type or "verbal" in predicate_type:
        return ("create", "κτίζω", "ברא")
    return ("is", "was", "true", "real", "ἀλήθεια", "אמת", "truth")


def _first_existing(vocab, candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        try:
            vocab.get_versor(candidate)
        except KeyError:
            continue
        return candidate
    return None


def _prompt_versor(field_state: FieldState) -> np.ndarray:
    return field_state.F


def _frame_query_relation(field_state: FieldState) -> np.ndarray:
    left = field_state.holonomy if field_state.holonomy is not None else field_state.F
    relation = outer_product(left, field_state.F)
    if float(np.linalg.norm(relation)) >= 1e-8:
        return relation
    shifted = np.roll(np.asarray(field_state.F, dtype=np.float32), 1)
    return outer_product(field_state.F, shifted)


def _nearest_content_word(
    vocab,
    query: np.ndarray,
    exclude_indices: frozenset[int],
    preferred_pos: frozenset[str] = frozenset(),
    candidate_indices: np.ndarray | None = None,
) -> tuple[str, int]:
    stop_indices = {
        vocab.index_of(surface)
        for surface in _STOP_SURFACES
        if _has_word(vocab, surface)
    }
    blocked = set(exclude_indices) | stop_indices
    candidates = range(len(vocab)) if candidate_indices is None else [int(idx) for idx in candidate_indices]
    if preferred_pos:
        selected = _nearest_by_pos(vocab, query, blocked, preferred_pos, candidate_indices)
        if selected is not None:
            return selected
    return _nearest_by_cga(vocab, query, blocked, candidates)


def _nearest_by_cga(vocab, query: np.ndarray, blocked: set[int], candidates) -> tuple[str, int]:
    best_score = -np.inf
    best_idx = -1
    query_arr = np.asarray(query, dtype=np.float32)
    for idx in candidates:
        idx = int(idx)
        if idx in blocked:
            continue
        score = cga_inner(vocab.get_versor_at(idx), query_arr)
        if score > best_score:
            best_score = score
            best_idx = idx
    if best_idx < 0:
        raise ValueError("No candidate word available after exclusions.")
    return vocab.get_word_at(best_idx), best_idx


def _nearest_by_pos(
    vocab,
    query: np.ndarray,
    blocked: set[int],
    preferred_pos: frozenset[str],
    candidate_indices: np.ndarray | None = None,
) -> tuple[str, int] | None:
    best_score = -np.inf
    best: tuple[str, int] | None = None
    candidates = range(len(vocab)) if candidate_indices is None else [int(idx) for idx in candidate_indices]
    query_arr = np.asarray(query, dtype=np.float32)
    for idx in candidates:
        if idx in blocked:
            continue
        word = vocab.get_word_at(idx)
        morphology_for_word = getattr(vocab, "morphology_for_word", None)
        morphology = morphology_for_word(word) if morphology_for_word is not None else None
        pos = None if morphology is None else dict(morphology.inflection).get("pos")
        if pos not in preferred_pos:
            continue
        score = cga_inner(vocab.get_versor_at(idx), query_arr)
        if score > best_score:
            best_score = score
            best = (word, idx)
    return best


def _has_word(vocab, word: str) -> bool:
    try:
        vocab.index_of(word)
    except KeyError:
        return False
    return True


def _frame_wants_object(frame: PropositionFrame) -> bool:
    object_names = {"object", "ground", "locus", "location", "genitive", "created"}
    return any(slot.required and slot.name in object_names for slot in frame.slots)


def _render_surface(
    frame: PropositionFrame,
    subject: str,
    predicate: str,
    object_surface: str | None,
) -> str:
    if frame.language == "he" and frame.predicate_type == "copular":
        return f"{subject} {predicate}"
    if frame.predicate_type == "copular-qualitative":
        return f"{predicate} {subject}"
    if object_surface is not None:
        return f"{subject} {predicate} {object_surface}"
    if frame.predicate_type.startswith("copular"):
        return f"{subject} {predicate}"
    return f"{subject} {predicate}"
