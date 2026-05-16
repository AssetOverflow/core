from __future__ import annotations

import numpy as np

from field.state import FieldState
from generate.stream import _articulate, generate
from generate.stream import _nearest_next
from persona.motor import PersonaMotor


class _StubVocab:
    def __init__(self, words: list[str]):
        self._words = words
        self.calls: list[tuple[int, frozenset[int]]] = []

    def __len__(self) -> int:
        return len(self._words)

    def nearest(self, F, exclude_idx: int = -1, exclude_indices=None):
        blocked = frozenset(exclude_indices or ())
        self.calls.append((exclude_idx, blocked))
        for idx, word in enumerate(self._words):
            if idx == exclude_idx or idx in blocked:
                continue
            return word, idx
        raise ValueError("No candidate word available after exclusions.")


class _Morphology:
    def __init__(self, surface: str) -> None:
        self.surface = surface


class _MorphVocab(_StubVocab):
    def __init__(self):
        super().__init__(["seed", "אוֹר"])
        self._versors = [np.eye(1, 32, 0, dtype=np.float32)[0], np.eye(1, 32, 0, dtype=np.float32)[0]]

    def morphology_for_word(self, word: str):
        return _Morphology("אוֹר") if word == "אוֹר" else None

    def get_versor_at(self, idx: int):
        return self._versors[idx]

    def index_of(self, word: str) -> int:
        try:
            return self._words.index(word)
        except ValueError:
            raise KeyError(word)

    def get_word_at(self, idx: int) -> str:
        return self._words[idx]


def test_nearest_next_excludes_recent_and_stop_nodes_when_possible():
    vocab = _StubVocab(["seed", "to", "it", "meaning", "truth"])

    word, idx = _nearest_next(
        vocab,
        F_voiced=None,
        current_node=0,
        recent_nodes=(3,),
        stop_nodes=frozenset({1, 2}),
    )

    assert (word, idx) == ("truth", 4)
    assert vocab.calls[0] == (0, frozenset({1, 2, 3}))


def test_nearest_next_relaxes_recent_window_before_stop_tokens():
    vocab = _StubVocab(["seed", "to", "truth"])

    word, idx = _nearest_next(
        vocab,
        F_voiced=None,
        current_node=0,
        recent_nodes=(2,),
        stop_nodes=frozenset({1}),
    )

    assert (word, idx) == ("truth", 2)
    assert vocab.calls == [
        (0, frozenset({1, 2})),
        (0, frozenset({1})),
    ]


def test_articulate_uses_structured_morphology_surface():
    vocab = _MorphVocab()

    assert _articulate(vocab, "אוֹר") == "אוֹר"


def test_generate_emits_morphology_surface():
    vocab = _MorphVocab()
    state = FieldState(F=vocab.get_versor_at(0), node=0)

    result = generate(state, vocab, PersonaMotor.identity(), max_tokens=1)

    assert result.tokens == ("אוֹר",)
