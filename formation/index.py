"""``MasteredCoursesIndex`` — content-addressed registry of Ratified courses.

The index is the gate-keeper consulted by every Stage 0 (Subject Spec) when
checking ``requires_courses``: a course may only run if all of its
prerequisites are Ratified.

Backing store: a single JSON file (default ``packs/mastered_courses.json``).
Append-only — entries are never overwritten or deleted by ordinary
operations.  Each entry pins a ``MasteryReport`` by its self-sealing SHA.

This is governance metadata, not runtime state — it does not live in
``vault/`` (exact-recall runtime) and not in ``language_packs/`` (mutable pack
data).  ``packs/mastered_courses.json`` keeps it visible in source control.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from formation.hashing import canonical_json


_INDEX_SCHEMA_VERSION: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class MasteredCourseEntry:
    course_id: str
    report_sha256: str
    issued_at: str
    course_sha256: str
    validated_set_sha: str


class MasteredCoursesIndex:
    """JSON-file-backed, append-only registry of Ratified courses."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path).resolve()
        self._by_course_id: dict[str, MasteredCourseEntry] = {}
        self._by_report_sha: dict[str, MasteredCourseEntry] = {}
        if self._path.exists():
            self._load()

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> None:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for row in raw.get("entries", []):
            entry = MasteredCourseEntry(
                course_id=row["course_id"],
                report_sha256=row["report_sha256"],
                issued_at=row["issued_at"],
                course_sha256=row["course_sha256"],
                validated_set_sha=row["validated_set_sha"],
            )
            self._by_course_id[entry.course_id] = entry
            self._by_report_sha[entry.report_sha256] = entry

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "schema_version": _INDEX_SCHEMA_VERSION,
            "entries": [
                {
                    "course_id": e.course_id,
                    "report_sha256": e.report_sha256,
                    "issued_at": e.issued_at,
                    "course_sha256": e.course_sha256,
                    "validated_set_sha": e.validated_set_sha,
                }
                for e in sorted(
                    self._by_course_id.values(), key=lambda x: x.course_id
                )
            ],
        }
        self._path.write_bytes(canonical_json(payload))

    def contains_course(self, course_id: str) -> bool:
        return course_id in self._by_course_id

    def contains_report(self, report_sha256: str) -> bool:
        return report_sha256 in self._by_report_sha

    def get(self, course_id: str) -> MasteredCourseEntry | None:
        return self._by_course_id.get(course_id)

    def all_courses(self) -> tuple[MasteredCourseEntry, ...]:
        return tuple(sorted(self._by_course_id.values(), key=lambda x: x.course_id))

    def add(self, entry: MasteredCourseEntry) -> None:
        """Register a Ratified course.  Idempotent on ``(course_id, report_sha)``.

        Re-registering a different report SHA for the same course_id raises
        ``ValueError`` — supersede paths are explicit and not handled here.
        """
        existing = self._by_course_id.get(entry.course_id)
        if existing is not None:
            if existing.report_sha256 == entry.report_sha256:
                return  # idempotent
            raise ValueError(
                f"course_id {entry.course_id!r} already mastered under "
                f"different report ({existing.report_sha256} != {entry.report_sha256})"
            )
        self._by_course_id[entry.course_id] = entry
        self._by_report_sha[entry.report_sha256] = entry
        self._persist()
