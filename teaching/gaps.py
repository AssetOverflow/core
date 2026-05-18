"""teaching/gaps.py — Phase 1.1: aggregate emitted DiscoveryCandidates
into a ranked view of (subject, intent) cells the runtime would have
grounded if the corpus had a chain there.

ADR-0055 Phase B emits ``DiscoveryCandidate`` JSONL lines to an
attached :class:`teaching.discovery_sink.DiscoveryCandidateSink`.
:class:`DiscoveryMonthlyFileSink` persists them under
``<root>/<YYYY>/<YYYY-MM>.jsonl``.  That stream answers "which
prompts couldn't ground today" — but it's append-only and operators
don't grep raw JSONL.

This module is the **reader side** of the flywheel: it walks the
sink's persisted output and groups candidates by ``(subject, intent)``
cell so operators can see at a glance which cells are most-asked
without resorting to ad-hoc shell pipelines.

Design constraints (matching CLAUDE.md doctrine):

  - Pure reader.  No mutation of any sink file.  Aggregation is
    derived state; the sink remains the source of truth.
  - Deterministic ordering: cells are sorted by (count desc, subject,
    intent) so the same input always produces the same view.
  - Date filtering operates on the sink's file naming convention
    (``<YYYY>/<YYYY-MM>.jsonl``) — month-level granularity, no
    timestamp dependency.
  - Malformed lines are skipped silently; the aggregator never raises
    on a single bad line.  The point is a useful summary, not a
    schema validator (use ``teaching audit`` for that).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_DEFAULT_ROOT: Path = Path(__file__).resolve().parent / "discovery_log"

# Sink file naming convention: ``<root>/<YYYY>/<YYYY-MM>.jsonl``.
# Regex anchors to filename only — full path components are not
# matched so the same regex applies to nested-or-flat layouts that
# alternative sinks might use.
_MONTH_FILE_RE = re.compile(r"^(\d{4})-(\d{2})\.jsonl$")
_MONTH_TOKEN_RE = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True, slots=True)
class Gap:
    """One aggregated ``(subject, intent)`` cell.

    Fields:
      - ``subject`` / ``intent``: the cell identity (lower-case).
      - ``count``: total number of candidate emissions whose proposed
        chain referenced this cell, across all aggregated months.
      - ``boundary_clean_count``: subset of ``count`` whose
        ``boundary_clean`` flag was True (refusal/hedge-tainted
        candidates are still counted toward ``count`` but split out
        here so operators can filter).
      - ``sample_candidate_ids``: up to 5 candidate_ids contributing
        to this cell, sorted for determinism — useful for spot-checks.
      - ``months_seen``: sorted ``YYYY-MM`` months where this cell
        appeared at least once.
    """

    subject: str
    intent: str
    count: int
    boundary_clean_count: int
    sample_candidate_ids: tuple[str, ...]
    months_seen: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "intent": self.intent,
            "count": self.count,
            "boundary_clean_count": self.boundary_clean_count,
            "sample_candidate_ids": list(self.sample_candidate_ids),
            "months_seen": list(self.months_seen),
        }


def _normalise_since(since: str | None) -> tuple[int, int] | None:
    """Return ``(year, month)`` for *since*, or None if absent.

    Raises :class:`ValueError` on a malformed token (caller surfaces
    a friendly CLI error).
    """
    if since is None:
        return None
    match = _MONTH_TOKEN_RE.match(since.strip())
    if not match:
        raise ValueError(
            f"--since {since!r} is not a YYYY-MM token (e.g. '2026-05')"
        )
    return int(match.group(1)), int(match.group(2))


def _iter_candidate_files(
    root: Path, *, since: tuple[int, int] | None
) -> Iterable[tuple[str, Path]]:
    """Yield ``(month_token, path)`` for every JSONL file under *root*
    whose filename matches the monthly-sink convention.

    Files outside the ``YYYY-MM.jsonl`` convention are skipped — the
    sink can grow alternative names later without breaking the
    aggregator's behavior on the canonical layout.
    """
    if not root.exists() or not root.is_dir():
        return
    for path in sorted(root.rglob("*.jsonl")):
        m = _MONTH_FILE_RE.match(path.name)
        if not m:
            continue
        year = int(m.group(1))
        month = int(m.group(2))
        if since is not None and (year, month) < since:
            continue
        yield f"{year:04d}-{month:02d}", path


def aggregate_gaps(
    root: Path = _DEFAULT_ROOT,
    *,
    since: str | None = None,
    sample_limit: int = 5,
) -> tuple[Gap, ...]:
    """Aggregate every emitted ``DiscoveryCandidate`` under *root* into
    a ranked tuple of :class:`Gap` records.

    ``since`` accepts a ``YYYY-MM`` token.  When supplied, only
    candidate files whose monthly token is ``>= since`` are read.

    The returned tuple is sorted by ``(count desc, subject asc,
    intent asc)`` so identical inputs produce identical orderings —
    important for deterministic CLI output that operators can diff
    across invocations.
    """
    since_tuple = _normalise_since(since)
    counts: dict[tuple[str, str], int] = {}
    clean_counts: dict[tuple[str, str], int] = {}
    samples: dict[tuple[str, str], list[str]] = {}
    months: dict[tuple[str, str], set[str]] = {}

    for month_token, path in _iter_candidate_files(root, since=since_tuple):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            chain = entry.get("proposed_chain")
            if not isinstance(chain, dict):
                continue
            subject = chain.get("subject")
            intent = chain.get("intent")
            if not isinstance(subject, str) or not isinstance(intent, str):
                continue
            subject = subject.strip().lower()
            intent = intent.strip().lower()
            if not subject or not intent:
                continue
            key = (subject, intent)
            counts[key] = counts.get(key, 0) + 1
            if entry.get("boundary_clean") is True:
                clean_counts[key] = clean_counts.get(key, 0) + 1
            sample_list = samples.setdefault(key, [])
            candidate_id = entry.get("candidate_id")
            if (
                isinstance(candidate_id, str)
                and candidate_id
                and len(sample_list) < sample_limit
                and candidate_id not in sample_list
            ):
                sample_list.append(candidate_id)
            months.setdefault(key, set()).add(month_token)

    rows: list[Gap] = []
    for key, total in counts.items():
        subject, intent = key
        rows.append(
            Gap(
                subject=subject,
                intent=intent,
                count=total,
                boundary_clean_count=clean_counts.get(key, 0),
                sample_candidate_ids=tuple(sorted(samples.get(key, ()))),
                months_seen=tuple(sorted(months.get(key, ()))),
            )
        )
    rows.sort(key=lambda g: (-g.count, g.subject, g.intent))
    return tuple(rows)


__all__ = ["Gap", "aggregate_gaps"]
