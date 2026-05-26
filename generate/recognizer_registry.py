"""ADR-0163 Phase D — ratified RecognizerSpec registry projection.

Pure projection over the append-only proposal log
(`teaching/proposals/proposals.jsonl`) into a tuple of
:class:`RatifiedRecognizer` records the candidate-graph admission
surface consults.

Trust boundary
- The projection is a *read* over the proposal log.  Mutation of the
  active corpus or the proposal log itself is out of scope; that path
  is gated by ADR-0057's ``accept_proposal``.
- Only proposals with ``review_state == "accepted"`` AND
  ``source.kind == "exemplar_corpus"`` AND a parseable
  ``proposed_chain.recognizer_spec`` enter the registry.  Pending,
  rejected, withdrawn, and non-exemplar proposals are invisible.
- Malformed accepted proposals raise :class:`RegistryLoadError` with
  the offending ``proposal_id``.  Silent drops are forbidden — the
  operator must see them.

Determinism
- ``load_ratified_registry(log)`` is a pure function of the log
  bytes.  Same log file → byte-identical tuple, sorted by
  ``(review_date, proposal_id)`` ascending.
- A module-level cache keyed on the log's (mtime, sha256) keeps a hot
  in-process invocation cheap.  Cache lives in process; no
  filesystem-level cache is introduced (ADR-0161 §1, ADR-0163
  §Phase C constraint).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from teaching.proposals import ProposalLog


class RegistryLoadError(ValueError):
    """Raised when an accepted proposal carries a malformed recognizer spec."""


@dataclass(frozen=True, slots=True)
class RatifiedRecognizer:
    """One ratified recognizer projected from the proposal log.

    ``canonical_pattern`` carries the per-category bespoke shape the
    Phase C synthesizer produced; consumers MUST branch on
    ``shape_category`` before reading.  ``review_date`` and
    ``ratified_at_revision`` are recorded for audit; matching code
    reads only ``shape_category`` + ``canonical_pattern``.
    """

    proposal_id: str
    shape_category: ShapeCategory
    canonical_pattern: Mapping[str, Any]
    spec_digest: str
    review_date: str
    ratified_at_revision: str


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

# Keyed on (log_path, mtime_ns, sha256_hex).  Value: the projected tuple.
# Cache is in-process and reset by clear_registry_cache() (tests).
_CACHE: dict[tuple[str, int, str], tuple[RatifiedRecognizer, ...]] = {}


def clear_registry_cache() -> None:
    """Reset the in-process registry cache.

    Useful in tests that mutate the proposal log between calls.  In
    production, the cache invalidates automatically when the log's
    (mtime, sha256) changes.
    """
    _CACHE.clear()


def _log_cache_key(log_path: Path) -> tuple[str, int, str]:
    if not log_path.exists():
        return (str(log_path), 0, "")
    stat = log_path.stat()
    digest = hashlib.sha256(log_path.read_bytes()).hexdigest()
    return (str(log_path), stat.st_mtime_ns, digest)


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def _coerce_shape_category(value: Any, proposal_id: str) -> ShapeCategory:
    if not isinstance(value, str):
        raise RegistryLoadError(
            f"proposal {proposal_id!r}: recognizer_spec.shape_category must be "
            f"a string; got {type(value).__name__}"
        )
    for member in ShapeCategory:
        if member.value == value:
            return member
    raise RegistryLoadError(
        f"proposal {proposal_id!r}: shape_category {value!r} is not a "
        f"ShapeCategory member"
    )


def _extract_recognizer(
    proposal: Mapping[str, Any],
) -> tuple[ShapeCategory, Mapping[str, Any], str]:
    """Pull (shape_category, canonical_pattern, spec_digest) out of *proposal*.

    Raises :class:`RegistryLoadError` for any structural break.
    """
    proposal_id = str(proposal.get("proposal_id") or "")
    chain = proposal.get("proposed_chain") or {}
    if not isinstance(chain, Mapping):
        raise RegistryLoadError(
            f"proposal {proposal_id!r}: proposed_chain must be a mapping"
        )
    rec_spec = chain.get("recognizer_spec")
    if not isinstance(rec_spec, Mapping):
        raise RegistryLoadError(
            f"proposal {proposal_id!r}: proposed_chain.recognizer_spec is "
            "missing or non-mapping (ADR-0163 §Phase C contract)"
        )
    shape_category = _coerce_shape_category(
        rec_spec.get("shape_category"), proposal_id
    )
    canonical_pattern = rec_spec.get("canonical_pattern")
    if not isinstance(canonical_pattern, Mapping):
        raise RegistryLoadError(
            f"proposal {proposal_id!r}: canonical_pattern must be a mapping"
        )
    spec_digest = str(chain.get("object") or "")
    if not spec_digest:
        raise RegistryLoadError(
            f"proposal {proposal_id!r}: proposed_chain.object (spec_digest) "
            "must be non-empty"
        )
    return shape_category, canonical_pattern, spec_digest


def _accepted_review_dates(
    events: list[dict[str, Any]],
) -> dict[str, tuple[str, str]]:
    """Walk the log events and return {proposal_id: (review_date, note)}.

    The accept review_date is parsed out of the transition note: the
    accept_proposal() helper passes the date via operator_note; ADR-0057
    encodes the same date in the corpus-append event's provenance.
    Both shapes are tolerated here.
    """
    out: dict[str, tuple[str, str]] = {}
    for ev in events:
        kind = ev.get("event")
        if kind != "transition" or ev.get("to") != "accepted":
            continue
        pid = str(ev.get("proposal_id") or "")
        note = str(ev.get("note") or "")
        # Best-effort: pull a YYYY-MM-DD from the note; fall back to "".
        review_date = ""
        for token in note.replace(":", " ").replace(",", " ").split():
            if len(token) == 10 and token[4] == "-" and token[7] == "-":
                review_date = token
                break
        out[pid] = (review_date, note)
    # Walk corpus_append events too — their provenance.review_date is
    # the authoritative source when present.
    for ev in events:
        if ev.get("event") != "accepted_corpus_append":
            continue
        pid = str(ev.get("proposal_id") or "")
        prov = ev.get("provenance") or {}
        if isinstance(prov, Mapping):
            rd = str(prov.get("review_date") or "")
            if rd and pid in out:
                out[pid] = (rd, out[pid][1])
    return out


def load_ratified_registry(
    log: ProposalLog | None = None,
) -> tuple[RatifiedRecognizer, ...]:
    """Project the proposal log into a tuple of ratified recognizers.

    Only proposals whose ``review_state`` is ``"accepted"`` AND whose
    ``source.kind`` is ``"exemplar_corpus"`` AND whose
    ``proposed_chain.recognizer_spec`` parses as a Phase C
    :class:`teaching.recognizer_synthesis.RecognizerSpec` (validated by
    :func:`_extract_recognizer`) enter the tuple.

    Returned tuple is sorted by ``(review_date, proposal_id)``
    ascending — stable across runs.

    The cache is keyed on the proposal log's (mtime, sha256) so writes
    to the log between calls invalidate transparently.
    """
    proposal_log = log if log is not None else ProposalLog()
    log_path = proposal_log.path
    cache_key = _log_cache_key(log_path)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    state = proposal_log.current_state()
    events = proposal_log.events()
    accept_review_dates = _accepted_review_dates(events)

    out: list[RatifiedRecognizer] = []
    for proposal_id, record in state.items():
        if record.get("state") != "accepted":
            continue
        source = record.get("source") or {}
        if not isinstance(source, Mapping):
            continue
        if source.get("kind") != "exemplar_corpus":
            continue
        proposal_payload = record.get("proposal") or {}
        if not isinstance(proposal_payload, Mapping):
            raise RegistryLoadError(
                f"proposal {proposal_id!r}: missing 'proposal' payload in "
                "log view"
            )
        try:
            shape_category, canonical_pattern, spec_digest = _extract_recognizer(
                proposal_payload
            )
        except RegistryLoadError:
            raise
        review_date, _note = accept_review_dates.get(proposal_id, ("", ""))
        ratified_at_revision = str(
            source.get("emitted_at_revision") or ""
        )
        out.append(
            RatifiedRecognizer(
                proposal_id=proposal_id,
                shape_category=shape_category,
                canonical_pattern=dict(canonical_pattern),
                spec_digest=spec_digest,
                review_date=review_date,
                ratified_at_revision=ratified_at_revision,
            )
        )

    out.sort(key=lambda r: (r.review_date, r.proposal_id))
    result = tuple(out)
    _CACHE[cache_key] = result
    return result


__all__ = [
    "RatifiedRecognizer",
    "RegistryLoadError",
    "clear_registry_cache",
    "load_ratified_registry",
]
