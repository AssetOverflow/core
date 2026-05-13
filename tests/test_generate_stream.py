from __future__ import annotations

from generate.stream import _nearest_next


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
