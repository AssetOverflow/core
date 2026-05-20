from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class ContemplationSubstrate:
    """Explicit read-only substrate contemplated by ADR-0080.

    Phase 1 intentionally records identifiers and report hashes only.  It does
    not crawl mutable runtime state and does not treat ambient files as hidden
    evidence.
    """

    pack_ids: tuple[str, ...] = ()
    report_hashes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    substrate_hash: str = field(default="")

    def __post_init__(self) -> None:
        object.__setattr__(self, "pack_ids", tuple(sorted(set(self.pack_ids))))
        object.__setattr__(self, "report_hashes", tuple(sorted(set(self.report_hashes))))
        object.__setattr__(self, "notes", tuple(self.notes))
        if not self.substrate_hash:
            object.__setattr__(self, "substrate_hash", _sha256(_canonical_json(self._identity_dict())))

    def _identity_dict(self) -> dict[str, Any]:
        return {
            "pack_ids": list(self.pack_ids),
            "report_hashes": list(self.report_hashes),
            "notes": list(self.notes),
        }

    def as_dict(self) -> dict[str, Any]:
        payload = self._identity_dict()
        payload["substrate_hash"] = self.substrate_hash
        return payload

    @classmethod
    def from_report_paths(
        cls,
        report_paths: Iterable[str | Path],
        *,
        pack_ids: Iterable[str] = (),
        notes: Iterable[str] = (),
    ) -> "ContemplationSubstrate":
        paths = tuple(Path(p) for p in report_paths)
        report_hashes = tuple(_file_digest(path) for path in paths)
        return cls(
            pack_ids=tuple(pack_ids),
            report_hashes=report_hashes,
            notes=tuple(notes),
        )


__all__ = ["ContemplationSubstrate"]
