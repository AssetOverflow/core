"""
Structured proposition generation.

A proposition is the first structured assertion above the surface walk:
prompt and field form a grade-2 relation blade; a frame is selected by exact
CGA inner product against that relation; vocabulary points then instantiate
the frame slots.

No normalization happens here. This module consumes already-closed field and
vocabulary versors and uses only outer_product() plus cga_inner() for relation
and distance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from algebra.cga import cga_inner, outer_product
from field.state import FieldState
from generate.stream import _articulate

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

    def __post_init__(self) -> None:
        subject_versor = np.asarray(self.subject_versor, dtype=np.float32).copy()
        predicate_versor = np.asarray(self.predicate_versor, dtype=np.float32).copy()
        object.__setattr__(self, "subject_versor", subject_versor)
        object.__setattr__(self, "predicate_versor", predicate_versor)
        if self.object_versor is not None:
            object_versor = np.asarray(self.object_versor, dtype=np.float32).copy()
            object.__setattr__(self, "object_versor", object_versor)
        object.__setattr__(self, "relation", np.asarray(self.relation, dtype=np.float32).copy())


class FrameRegistry:
    """Exact frame selection over precompiled frame relation blades."""

    def __init__(self, frames: Iterable[PropositionFrame]) -> None:
        self._frames = tuple(frames)
        if not self._frames:
            raise ValueError("FrameRegistry requires at least one frame.")

    @classmethod
    def from_pack(cls, pack: str, vocab) -> "FrameRegistry":
        """
        Load frames from packs/<pack>/frames.jsonl.

        The shipped Koine directory is named both `el` and `grc` in different
        layers; this accepts either spelling and reads the project pack files.
        """
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

    def __iter__(self):
        return iter(self._frames)

    def __len__(self) -> int:
        return len(self._frames)


def propose(field_state: FieldState, vault, vocab, frame_registry: FrameRegistry) -> Proposition:
    """
    Generate one structured proposition from the live field.

    The prompt field is `holonomy` when injection supplied it; otherwise the
    current field is used. The selected subject is nearest the prompt. The
    predicate is nearest the current field with the subject and trivial stop
    wells excluded. The resulting proposition can be stored directly in the
    vault metadata while its `surface` remains the emitted text.
    """
    prompt = _prompt_versor(field_state)
    relation = outer_product(prompt, field_state.F)
    frame = frame_registry.select(relation)

    subject_word, subject_idx = _nearest_content_word(
        vocab,
        prompt,
        exclude_indices=frozenset(),
        preferred_pos=frozenset({"noun", "pronoun"}),
    )
    predicate_word, predicate_idx = _nearest_content_word(
        vocab,
        field_state.F,
        exclude_indices=frozenset({subject_idx}),
    )

    object_word: str | None = None
    object_versor: np.ndarray | None = None
    if _frame_wants_object(frame):
        object_word, object_idx = _nearest_content_word(
            vocab,
            relation,
            exclude_indices=frozenset({subject_idx, predicate_idx}),
            preferred_pos=frozenset({"noun", "pronoun"}),
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
        subject_versor=vocab.get_versor_at(subject_idx),
        predicate_versor=vocab.get_versor_at(predicate_idx),
        object_versor=object_versor,
        relation=relation,
    )
    if vault is not None:
        vault.store(field_state.F, {"kind": "proposition", "proposition": proposition})
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
    return field_state.holonomy if field_state.holonomy is not None else field_state.F


def _nearest_content_word(
    vocab,
    query: np.ndarray,
    exclude_indices: frozenset[int],
    preferred_pos: frozenset[str] = frozenset(),
) -> tuple[str, int]:
    stop_indices = {
        vocab.index_of(surface)
        for surface in _STOP_SURFACES
        if _has_word(vocab, surface)
    }
    blocked = set(exclude_indices) | stop_indices
    if preferred_pos:
        selected = _nearest_by_pos(vocab, query, blocked, preferred_pos)
        if selected is not None:
            return selected
    try:
        return vocab.nearest(query, exclude_indices=blocked)
    except ValueError:
        return vocab.nearest(query, exclude_indices=set(exclude_indices))


def _nearest_by_pos(
    vocab,
    query: np.ndarray,
    blocked: set[int],
    preferred_pos: frozenset[str],
) -> tuple[str, int] | None:
    best_score = -np.inf
    best: tuple[str, int] | None = None
    for idx in range(len(vocab)):
        if idx in blocked:
            continue
        word = vocab.get_word_at(idx)
        morphology_for_word = getattr(vocab, "morphology_for_word", None)
        morphology = morphology_for_word(word) if morphology_for_word is not None else None
        pos = None if morphology is None else dict(morphology.inflection).get("pos")
        if pos not in preferred_pos:
            continue
        score = cga_inner(query, vocab.get_versor_at(idx))
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
    if object_surface is not None:
        return f"{subject} {predicate} {object_surface}"
    if frame.predicate_type.startswith("copular"):
        return f"{subject} {predicate}"
    return f"{subject} {predicate}"
