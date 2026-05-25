"""RecognizerRegistry -- per-teaching-set recognizer store (ADR-0146).

Holds DerivedRecognizer instances keyed by teaching_set_id. Wired into
EngineStateStore for Shape B persistence. Empty registry is the valid
initial state (no teaching examples yet).
"""

from __future__ import annotations

from recognition.anti_unifier import DerivedRecognizer


class RecognizerRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, DerivedRecognizer] = {}

    def register(self, recognizer: DerivedRecognizer) -> None:
        self._registry[recognizer.teaching_set_id] = recognizer

    def get(self, teaching_set_id: str) -> DerivedRecognizer | None:
        return self._registry.get(teaching_set_id)

    def all(self) -> list[DerivedRecognizer]:
        return list(self._registry.values())

    def first_admitted(self) -> DerivedRecognizer | None:
        """Return the first registered recognizer, or None if registry is empty."""
        if not self._registry:
            return None
        return next(iter(self._registry.values()))

    def __len__(self) -> int:
        return len(self._registry)

    @classmethod
    def from_recognizers(
        cls,
        recognizers: list[DerivedRecognizer],
    ) -> "RecognizerRegistry":
        reg = cls()
        for recognizer in recognizers:
            reg.register(recognizer)
        return reg


__all__ = ["RecognizerRegistry"]
