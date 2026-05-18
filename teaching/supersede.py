"""ADR-0057 follow-up — operator-driven supersession of an active corpus chain.

Supersession is the **second** mutation surface on the reviewed
teaching corpus (alongside ``teaching.proposals.accept_proposal``).
It is *not* a proposal: there is no replay-equivalence gate and no
``ProposalLog`` round-trip.  It is a direct operator action that
records: "this active chain is replaced by this new one."

Trust boundary:

  - Append-only at the disk level.  The earlier chain stays on disk;
    the audit report and the runtime loader both honour the
    ``superseded_by`` field to drop it from the active view.
  - The single write surface remains ``proposals.append_chain_to_corpus``.
    This module composes around it; it does not write its own JSONL.
  - Validation gates (pack-consistency, intent whitelist, complete
    fields, no double-supersede, not self-supersede) all run before
    the append.  Any gate failure raises ``SupersessionError`` and
    leaves the corpus byte-identical.
  - No clock-time read.  ``review_date`` is operator-provided.

This is distinct from ``TeachingChainProposal``: supersession is an
operator's deliberate replacement of a hand-authored or previously
discovery-promoted chain.  It does not need a replay gate because
the operator is explicitly accepting any metric movement.
"""

from __future__ import annotations

import re
from pathlib import Path

from teaching.audit import audit_corpus
from teaching.proposals import append_chain_to_corpus
from teaching.provenance import Provenance

# Reused from chat.teaching_grounding to keep one definition.
from chat.teaching_grounding import _VALID_INTENTS

_REVIEW_DATE_RE: re.Pattern[str] = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SupersessionError(ValueError):
    """Raised when a supersession action fails a pre-condition gate."""


def _validate_review_date(value: str) -> str:
    value = (value or "").strip()
    if not _REVIEW_DATE_RE.match(value):
        raise SupersessionError(
            f"review_date must be YYYY-MM-DD; got {value!r}"
        )
    return value


def _validate_chain_fields(
    subject: str, intent: str, connective: str, obj: str
) -> tuple[str, str, str, str]:
    s = (subject or "").strip().lower()
    i = (intent or "").strip().lower()
    c = (connective or "").strip()
    o = (obj or "").strip().lower()
    if not s or not i or not c or not o:
        raise SupersessionError(
            "subject/intent/connective/object are all required"
        )
    if i not in _VALID_INTENTS:
        raise SupersessionError(
            f"intent {i!r} is not in the supported whitelist "
            f"({sorted(_VALID_INTENTS)})"
        )
    return s, i, c, o


def supersede_chain(
    *,
    old_chain_id: str,
    subject: str,
    intent: str,
    connective: str,
    object_: str,
    review_date: str,
    corpus_path: Path,
    adr_id: str = "adr-0057",
    operator_note: str = "",
    new_chain_id: str | None = None,
) -> str:
    """Retire ``old_chain_id`` by appending a new chain that supersedes it.

    Returns the ``chain_id`` of the new active entry.  Raises
    ``SupersessionError`` on any pre-condition violation; in that
    case the corpus on disk is unchanged.

    Pre-conditions (run in this order — cheapest first):
      1. ``review_date`` matches ``YYYY-MM-DD``.
      2. New chain fields are non-empty and ``intent`` is in
         ``_VALID_INTENTS``.
      3. ``old_chain_id`` is currently *active* in the audit report
         (it must exist and not already be superseded).
      4. The new chain itself passes the same audit gates that the
         runtime loader applies (pack-consistency on subject/object,
         non-self-supersede).  This is verified by re-running
         ``audit_corpus`` after the append and asserting the active
         set has shifted exactly as expected; on any drift the
         appended line is rolled back by truncation.

    Step 4 is the safety net: it makes silent introduction of a
    pack-missing or otherwise invalid replacement impossible.
    """
    _ = operator_note  # reserved for future audit-log wiring; CLI surfaces it today
    old_id = (old_chain_id or "").strip()
    if not old_id:
        raise SupersessionError("old_chain_id is required")

    _validate_review_date(review_date)
    s, i, c, o = _validate_chain_fields(subject, intent, connective, object_)

    resolved_new_id = (new_chain_id or "").strip() or f"{i}_{s}_{c}_{o}"
    if resolved_new_id == old_id:
        raise SupersessionError(
            "new chain_id is identical to old_chain_id — supersession "
            "must produce a distinct active chain"
        )

    # -- Pre-append audit: old_chain_id must currently be active.
    pre = audit_corpus(corpus_path)
    active_chain_ids = {entry.chain_id for entry in pre.loaded}
    if old_id not in active_chain_ids:
        # Either the chain does not exist or it is already superseded.
        if any(d.chain_id == old_id for d in pre.dropped):
            raise SupersessionError(
                f"old_chain_id {old_id!r} is already inactive "
                f"(dropped by audit) — refusing to double-supersede"
            )
        raise SupersessionError(
            f"old_chain_id {old_id!r} is not in the active corpus"
        )
    if resolved_new_id in active_chain_ids:
        raise SupersessionError(
            f"new chain_id {resolved_new_id!r} is already active; "
            "choose a distinct connective/object or pass --new-chain-id"
        )

    chain = {
        "subject": s,
        "intent": i,
        "connective": c,
        "object": o,
    }
    review_date_clean = review_date.strip()
    provenance = Provenance(
        adr_id=adr_id,
        source="hand_authored",
        review_date=review_date_clean,
        raw=f"{adr_id}:hand_authored:{review_date_clean}:supersede({old_id})",
    )

    # Snapshot bytes so we can roll back if the post-audit invariant
    # is violated (defence in depth: should be impossible given the
    # pre-checks, but corpus correctness is load-bearing).
    bytes_before = corpus_path.read_bytes() if corpus_path.exists() else b""

    written_chain_id = append_chain_to_corpus(
        chain,
        corpus_path=corpus_path,
        provenance=provenance,
        chain_id=resolved_new_id,
        superseded_by=old_id,
    )

    # -- Post-append audit: confirm the active set shifted.
    post = audit_corpus(corpus_path)
    post_active = {entry.chain_id for entry in post.loaded}
    expected_dropped = (
        f"superseded_by:{old_id}" in {d.reason for d in post.dropped}
    )
    if (
        written_chain_id not in post_active
        or old_id in post_active
        or not expected_dropped
    ):
        # Roll back: truncate to bytes_before.
        corpus_path.write_bytes(bytes_before)
        raise SupersessionError(
            f"post-append audit rejected the supersession "
            f"(new={written_chain_id!r} active={written_chain_id in post_active}, "
            f"old_still_active={old_id in post_active}); corpus rolled back"
        )

    return written_chain_id


__all__ = [
    "SupersessionError",
    "supersede_chain",
]
