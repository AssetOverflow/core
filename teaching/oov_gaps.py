"""teaching/oov_gaps.py — Phase 2.3: aggregate emitted OOVCandidates
into a ranked view of unknown tokens.

Sibling to :mod:`teaching.gaps`.  Where discovery candidates point at
gaps in the *teaching corpus* (a chain would have helped), OOV
candidates point at gaps in the *lexicon* (a vocabulary entry would
have helped).  Both flow through the same operator workflow: rank
by frequency, auto-promote at threshold, surface to an operator who
authors a reviewed mutation.

Design constraints (matching :mod:`teaching.gaps`):

  - Pure reader.  No mutation of any sink file.
  - Deterministic ordering: highest-count tokens first, ties broken
    by token then intent set.
  - Date filtering via the sink's file naming convention
    (``<YYYY>/<YYYY-MM>.jsonl``) — month-level granularity.
  - Malformed lines are skipped silently.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_DEFAULT_ROOT: Path = Path(__file__).resolve().parent / "oov_log"

_MONTH_FILE_RE = re.compile(r"^(\d{4})-(\d{2})\.jsonl$")
_MONTH_TOKEN_RE = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True, slots=True)
class OOVGap:
    """One aggregated OOV token.

    Fields:
      - ``token``: the unknown vocabulary item (lower-case).
      - ``intents``: sorted tuple of intent shapes that hit this
        token at least once.  A token asked about under multiple
        intent shapes is a stronger curriculum signal than one asked
        only via ``DEFINITION``.
      - ``count``: total emissions.
      - ``boundary_clean_count``: subset whose ``boundary_clean=True``.
      - ``sample_candidate_ids``: up to N retained ids.
      - ``months_seen``: sorted ``YYYY-MM`` months.
    """

    token: str
    intents: tuple[str, ...]
    count: int
    boundary_clean_count: int
    sample_candidate_ids: tuple[str, ...]
    months_seen: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "token": self.token,
            "intents": list(self.intents),
            "count": self.count,
            "boundary_clean_count": self.boundary_clean_count,
            "sample_candidate_ids": list(self.sample_candidate_ids),
            "months_seen": list(self.months_seen),
        }


def _normalise_since(since: str | None) -> tuple[int, int] | None:
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


def aggregate_oov_gaps(
    root: Path = _DEFAULT_ROOT,
    *,
    since: str | None = None,
    sample_limit: int = 5,
) -> tuple[OOVGap, ...]:
    """Aggregate every emitted ``OOVCandidate`` under *root* into a
    ranked tuple of :class:`OOVGap` records.

    Returned tuple is sorted by ``(count desc, token asc)`` so
    identical inputs produce identical orderings.
    """
    since_tuple = _normalise_since(since)
    counts: dict[str, int] = {}
    clean_counts: dict[str, int] = {}
    samples: dict[str, list[str]] = {}
    months: dict[str, set[str]] = {}
    intents_by_token: dict[str, set[str]] = {}

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
            token = entry.get("token")
            intent = entry.get("intent")
            if not isinstance(token, str) or not isinstance(intent, str):
                continue
            token = token.strip().lower()
            intent = intent.strip().lower()
            if not token or not intent:
                continue
            counts[token] = counts.get(token, 0) + 1
            if entry.get("boundary_clean") is True:
                clean_counts[token] = clean_counts.get(token, 0) + 1
            intents_by_token.setdefault(token, set()).add(intent)
            sample_list = samples.setdefault(token, [])
            candidate_id = entry.get("candidate_id")
            if (
                isinstance(candidate_id, str)
                and candidate_id
                and len(sample_list) < sample_limit
                and candidate_id not in sample_list
            ):
                sample_list.append(candidate_id)
            months.setdefault(token, set()).add(month_token)

    rows: list[OOVGap] = []
    for token, total in counts.items():
        rows.append(
            OOVGap(
                token=token,
                intents=tuple(sorted(intents_by_token.get(token, ()))),
                count=total,
                boundary_clean_count=clean_counts.get(token, 0),
                sample_candidate_ids=tuple(sorted(samples.get(token, ()))),
                months_seen=tuple(sorted(months.get(token, ()))),
            )
        )
    rows.sort(key=lambda g: (-g.count, g.token))
    return tuple(rows)


__all__ = ["OOVGap", "aggregate_oov_gaps"]
