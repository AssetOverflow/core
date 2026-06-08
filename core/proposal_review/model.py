"""Typed records for the read-only proposal review reporter (RPT-a).

A ``PendingProposal`` is the parsed view of one ``teaching/proposals/comprehension_failures/
<hash>.json`` artifact (emitted by the contemplation pass, N5). A ``MalformedArtifact`` is a file
that could not be parsed into one. Pure value data — the reporter never mutates the sink.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PendingProposal:
    """A parsed proposal artifact awaiting human review. ``content_hash`` is the filename stem
    (the content address). Safety fields (``status`` / ``mounted`` / ``requires_review``) are
    carried verbatim so the dry-check (RPT-c) can verify them independently of the emitter."""

    path: str
    content_hash: str
    failure_family: str
    status: str
    mounted: bool
    requires_review: bool
    problem_text_sha256: str
    observed_attempts: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class MalformedArtifact:
    """A file under the sink that is not a parseable proposal (bad JSON / missing or mistyped
    fields). Surfaced so a human notices corruption rather than the reporter silently skipping it."""

    path: str
    reason: str


__all__ = ["MalformedArtifact", "PendingProposal"]
