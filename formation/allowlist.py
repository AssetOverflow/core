"""Source allow-list with authority tiers.

The Forge consults this list to decide whether a candidate's source SHAs are
permitted to feed the manifold at all, and whether any single source has
enough authority to graduate a candidate alone.

Two tiers:

    "primary"    — authoritative source (textbook, peer-reviewed paper, etc.)
                   ; a single primary citation suffices to validate a triple.
    "secondary"  — non-authoritative but admissible (e.g. Wikipedia, blog)
                   ; two independent secondary citations are required.

LLM-sourced candidates are always treated as ``"llm"`` regardless of which
model produced them.  They require ≥2 non-LLM corroborators.

Identity-override and adversarial-pattern entries are not part of this list —
those are handled separately in ``formation.forge._identity_axis_collision``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class AllowedSource:
    source_sha: str
    tier: str  # "primary" | "secondary" | "llm"
    label: str = ""


_VALID_TIERS: Final[frozenset[str]] = frozenset({"primary", "secondary", "llm"})


class SourceAllowlist:
    """In-memory allow-list keyed by source SHA."""

    def __init__(self, entries: tuple[AllowedSource, ...] = ()) -> None:
        for entry in entries:
            if entry.tier not in _VALID_TIERS:
                raise ValueError(
                    f"invalid tier {entry.tier!r}; allowed: {sorted(_VALID_TIERS)}"
                )
        self._by_sha: dict[str, AllowedSource] = {e.source_sha: e for e in entries}

    def tier_of(self, source_sha: str) -> str | None:
        entry = self._by_sha.get(source_sha)
        return entry.tier if entry else None

    def contains(self, source_sha: str) -> bool:
        return source_sha in self._by_sha

    def add(self, entry: AllowedSource) -> None:
        if entry.tier not in _VALID_TIERS:
            raise ValueError(f"invalid tier {entry.tier!r}")
        self._by_sha[entry.source_sha] = entry

    def __len__(self) -> int:
        return len(self._by_sha)
