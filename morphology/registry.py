"""
Morphology registry — reconstructive root and inflection structure.

The registry is deliberately pure schema + stdlib. It does not compile
versors, import algebra, or participate in propagation. Its job is to make
LexicalEntry.morphology_id resolve to ordered morphological structure.
"""

from __future__ import annotations

import json
from pathlib import Path

from language_packs.schema import MorphologyEntry

_DATA_DIR = Path(__file__).parent.parent / "language_packs" / "data"


class MorphologyRegistry:
    """Immutable morphology lookup table for one language pack."""

    def __init__(self, entries: list[MorphologyEntry]) -> None:
        self._entries: tuple[MorphologyEntry, ...] = tuple(entries)
        self._by_id: dict[str, MorphologyEntry] = {}
        self._by_surface: dict[str, MorphologyEntry] = {}
        for entry in self._entries:
            if entry.morphology_id in self._by_id:
                raise ValueError(f"Duplicate morphology_id: {entry.morphology_id}")
            self._by_id[entry.morphology_id] = entry
            self._by_surface[entry.surface] = entry

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> tuple[MorphologyEntry, ...]:
        return self._entries

    def get(self, morphology_id: str) -> MorphologyEntry | None:
        """Return an entry by morphology_id, or None if absent."""
        return self._by_id.get(morphology_id)

    def for_surface(self, surface: str) -> MorphologyEntry | None:
        """Return an entry by surface form, or None if absent."""
        return self._by_surface.get(surface)

    def require(self, morphology_id: str) -> MorphologyEntry:
        """Return an entry by morphology_id, raising if the link is broken."""
        entry = self.get(morphology_id)
        if entry is None:
            raise KeyError(f"Morphology id '{morphology_id}' not in registry.")
        return entry


def _parse_entry(payload: dict) -> MorphologyEntry:
    return MorphologyEntry(
        morphology_id=payload["morphology_id"],
        surface=payload["surface"],
        lemma=payload["lemma"],
        language=payload["language"],
        root=payload.get("root"),
        prefix_chain=tuple(payload.get("prefix_chain", [])),
        stem=payload.get("stem"),
        inflection=dict(payload.get("inflection", {})),
        suffix_chain=tuple(payload.get("suffix_chain", [])),
    )


def load_morphology(
    pack_id: str, *, data_root: Path | None = None
) -> MorphologyRegistry:
    """
    Load MorphologyEntry records from <data_root>/<pack_id>/morphology.jsonl.

    ``data_root`` defaults to the committed ``language_packs/data`` tree; pass
    an alternate root (e.g. a test-fixture copy) to read packs from elsewhere
    without forking the parser.

    Packs without morphology data return an empty registry; packs that set
    LexicalEntry.morphology_id are validated by the compiler against this
    registry.
    """
    morphology_path = (data_root or _DATA_DIR) / pack_id / "morphology.jsonl"
    if not morphology_path.exists():
        return MorphologyRegistry([])

    entries: list[MorphologyEntry] = []
    for line in morphology_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(_parse_entry(json.loads(line)))
    return MorphologyRegistry(entries)
