"""Content-addressed artifact cache for the Formation Pipeline.

Layout::

    .formation_cache/
        <subject_id>/
            <stage>/
                <input_sha>.json

Keys are sanitized — path traversal patterns (``..``, leading ``/``, NUL,
backslashes) are rejected before any filesystem access.  Subject IDs are
restricted to ``[A-Za-z0-9._-]+``.  Stage names are restricted to a fixed
allow-list.  Input SHAs must be 64-character lowercase hex.

Re-running an unchanged stage is a no-op cache hit — that is the speed
mechanism.  All cache hits compare SHA equality only; there is no fuzzy
match.

No pickle.  All cache files are canonical JSON.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

from formation.hashing import canonical_json

_DEFAULT_CACHE_DIRNAME: Final[str] = ".formation_cache"

_SUBJECT_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9._-]+$")
_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")

_ALLOWED_STAGES: Final[frozenset[str]] = frozenset({
    "subject_spec",
    "ore",
    "smelted",
    "validated",
    "course",
    "plan",
    "results",
    "mastery",
})


class CacheKeyError(ValueError):
    """Raised when a cache key fails sanitization (e.g. path traversal)."""


class FormationCache:
    """File-backed cache keyed by ``(subject_id, stage, input_sha)``."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def _validate(self, subject_id: str, stage: str, input_sha: str) -> None:
        if not isinstance(subject_id, str) or not _SUBJECT_ID_RE.fullmatch(subject_id):
            raise CacheKeyError(
                f"invalid subject_id {subject_id!r}; must match [A-Za-z0-9._-]+"
            )
        if subject_id.startswith(".") or ".." in subject_id:
            raise CacheKeyError(f"invalid subject_id {subject_id!r}; path traversal")
        if stage not in _ALLOWED_STAGES:
            raise CacheKeyError(
                f"invalid stage {stage!r}; allowed: {sorted(_ALLOWED_STAGES)}"
            )
        if not isinstance(input_sha, str) or not _SHA_RE.fullmatch(input_sha):
            raise CacheKeyError(
                f"invalid input_sha {input_sha!r}; must be 64-char lowercase hex"
            )

    def path_for(self, subject_id: str, stage: str, input_sha: str) -> Path:
        """Return the resolved cache path for a key, validating components.

        The resolved path is asserted to stay strictly under the cache root —
        a final defense in depth even though the component regexes already
        forbid traversal.
        """
        self._validate(subject_id, stage, input_sha)
        candidate = (self._root / subject_id / stage / f"{input_sha}.json").resolve()
        if not str(candidate).startswith(str(self._root) + "/") and candidate != self._root:
            raise CacheKeyError(
                f"resolved cache path {candidate!s} escapes root {self._root!s}"
            )
        return candidate

    def has(self, subject_id: str, stage: str, input_sha: str) -> bool:
        return self.path_for(subject_id, stage, input_sha).exists()

    def get(self, subject_id: str, stage: str, input_sha: str) -> Any | None:
        path = self.path_for(subject_id, stage, input_sha)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(
        self,
        subject_id: str,
        stage: str,
        input_sha: str,
        payload: Any,
    ) -> Path:
        path = self.path_for(subject_id, stage, input_sha)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json(payload))
        return path


def default_cache(cwd: Path | str | None = None) -> FormationCache:
    """Return a ``FormationCache`` rooted at ``<cwd>/.formation_cache``."""
    base = Path(cwd) if cwd is not None else Path.cwd()
    return FormationCache(base / _DEFAULT_CACHE_DIRNAME)
