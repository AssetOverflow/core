"""Read-only scanner over the comprehension-failure proposal sink (RPT-a).

Reads ``teaching/proposals/comprehension_failures/*.json`` into typed ``PendingProposal`` records;
any file that does not parse into one is reported as a ``MalformedArtifact`` (never silently
dropped). **Pure read** — opens files, never writes/moves/deletes. Deterministic: results are
sorted by filename. The sink location is computed here independently of the emitter, so the
reporter verifies the artifact contract without importing the writer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.proposal_review.model import MalformedArtifact, PendingProposal

#: The proposal sink the contemplation pass (N5) writes to — known independently of the emitter.
DEFAULT_SINK = (
    Path(__file__).resolve().parents[2] / "teaching" / "proposals" / "comprehension_failures"
)

#: Required fields and their JSON types for a well-formed proposal artifact.
_REQUIRED: tuple[tuple[str, type | tuple[type, ...]], ...] = (
    ("status", str),
    ("failure_family", str),
    ("problem_text_sha256", str),
    ("mounted", bool),
    ("requires_review", bool),
    ("observed_attempts", list),
)


def default_sink() -> Path:
    return DEFAULT_SINK


def _parse(path: Path) -> PendingProposal | MalformedArtifact:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return MalformedArtifact(str(path), f"invalid_json: {exc}")
    if not isinstance(raw, dict):
        return MalformedArtifact(str(path), "not_a_json_object")
    for key, typ in _REQUIRED:
        if key not in raw:
            return MalformedArtifact(str(path), f"missing_field: {key}")
        # bool is a subclass of int; check bools explicitly so 0/1 don't pass as bool.
        if typ is bool and not isinstance(raw[key], bool):
            return MalformedArtifact(str(path), f"bad_type: {key}")
        if typ is not bool and not isinstance(raw[key], typ):
            return MalformedArtifact(str(path), f"bad_type: {key}")
    attempts: tuple[dict[str, Any], ...] = tuple(
        a for a in raw["observed_attempts"] if isinstance(a, dict)
    )
    return PendingProposal(
        path=str(path),
        content_hash=path.stem,
        failure_family=raw["failure_family"],
        status=raw["status"],
        mounted=raw["mounted"],
        requires_review=raw["requires_review"],
        problem_text_sha256=raw["problem_text_sha256"],
        observed_attempts=attempts,
    )


def scan(root: Path | None = None) -> tuple[list[PendingProposal], list[MalformedArtifact]]:
    """Scan the sink (default: the comprehension-failure sink). Returns ``(proposals, malformed)``,
    each sorted by path. A missing sink yields two empty lists (nothing to review yet)."""
    base = root if root is not None else DEFAULT_SINK
    if not base.exists():
        return [], []
    proposals: list[PendingProposal] = []
    malformed: list[MalformedArtifact] = []
    for path in sorted(base.glob("*.json")):
        parsed = _parse(path)
        if isinstance(parsed, PendingProposal):
            proposals.append(parsed)
        else:
            malformed.append(parsed)
    return proposals, malformed


__all__ = ["DEFAULT_SINK", "default_sink", "scan"]
