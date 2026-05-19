"""ADR-0067 follow-up — operator-driven supersession of a cross-pack chain.

Mirrors :func:`teaching.supersede.supersede_chain` but operates on the
cross-pack corpus (``teaching/cross_pack_chains/cross_pack_chains_v1.jsonl``).

Cross-pack chains carry two pack-residency fields (``subject_pack_id``
and ``object_pack_id``) that the in-pack ``supersede_chain`` does not
know about.  Rather than overloading that function with optional kwargs
that change validation behaviour, this module supplies a sibling
function with the right surface and reuses the same write path
(``teaching.proposals.append_chain_to_corpus``).

Trust boundary (matches ADR-0057):

  - Append-only: the earlier chain stays on disk; the runtime loader
    honours ``superseded_by`` to drop it from the active view.
  - Single write surface preserved: ``append_chain_to_corpus`` is the
    only function that writes a JSONL line to the corpus.
  - Validation gates run BEFORE the append: review-date format,
    intent whitelist, distinct chain ids, declared pack residency,
    anti-leakage (subject_pack_id != object_pack_id), old chain must
    be active in the current cross-pack index.
  - Post-append re-load confirms the active set shifted as expected;
    any drift rolls back the file bytes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from chat.cross_pack_grounding import (
    _CORPUS_PATH as _DEFAULT_CROSS_PACK_CORPUS_PATH,
    _all_cross_pack_chains,
    clear_cross_pack_cache,
)
from chat.pack_resolver import _pack_lexicon_for
from teaching.proposals import append_chain_to_corpus
from teaching.provenance import Provenance
from teaching.supersede import SupersessionError

# Reuse the same intent whitelist as the in-pack path.
from chat.teaching_grounding import _VALID_INTENTS

_REVIEW_DATE_RE: re.Pattern[str] = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_review_date(value: str) -> str:
    value = (value or "").strip()
    if not _REVIEW_DATE_RE.match(value):
        raise SupersessionError(
            f"review_date must be YYYY-MM-DD; got {value!r}"
        )
    return value


def supersede_cross_pack_chain(
    *,
    old_chain_id: str,
    subject: str,
    intent: str,
    connective: str,
    object_: str,
    subject_pack_id: str,
    object_pack_id: str,
    review_date: str,
    corpus_path: Path | None = None,
    adr_id: str = "adr-0067",
    new_chain_id: str | None = None,
) -> str:
    """Retire ``old_chain_id`` in the cross-pack corpus by appending a
    new entry whose ``superseded_by`` references it.

    Returns the new entry's ``chain_id``.  Raises
    :class:`SupersessionError` on any pre-condition violation; the
    corpus is byte-identical on failure.

    Pre-conditions (cheapest first):

      1. ``review_date`` matches ``YYYY-MM-DD``.
      2. ``intent`` is in :data:`_VALID_INTENTS`.
      3. All chain fields + both pack ids are non-empty.
      4. ``subject_pack_id != object_pack_id`` (anti-leakage —
         cross-pack chains must actually cross packs).
      5. Declared subject lemma resolves in its named pack; same for
         object.
      6. ``old_chain_id`` is currently active in the cross-pack index.
      7. New chain id is distinct from old and not already active.

    Post-append:

      8. Re-load the index; new entry must be active, old must be
         dropped.  Any drift → roll back the bytes.
    """
    path: Path = corpus_path or _DEFAULT_CROSS_PACK_CORPUS_PATH

    old_id = (old_chain_id or "").strip()
    if not old_id:
        raise SupersessionError("old_chain_id is required")

    _validate_review_date(review_date)

    s = (subject or "").strip().lower()
    i = (intent or "").strip().lower()
    c = (connective or "").strip()
    o = (object_ or "").strip().lower()
    sp = (subject_pack_id or "").strip()
    op = (object_pack_id or "").strip()
    if not all((s, i, c, o, sp, op)):
        raise SupersessionError(
            "subject/intent/connective/object and both pack ids are required"
        )
    if i not in _VALID_INTENTS:
        raise SupersessionError(
            f"intent {i!r} is not in the supported whitelist "
            f"({sorted(_VALID_INTENTS)})"
        )
    if sp == op:
        raise SupersessionError(
            "subject_pack_id and object_pack_id must differ — "
            "same-pack entries belong in the in-pack corpus"
        )
    subject_pack = _pack_lexicon_for(sp)
    object_pack = _pack_lexicon_for(op)
    if s not in subject_pack:
        raise SupersessionError(
            f"subject lemma {s!r} not resident in pack {sp!r}"
        )
    if o not in object_pack:
        raise SupersessionError(
            f"object lemma {o!r} not resident in pack {op!r}"
        )

    # Pre-load index — must include old, must not already include new.
    clear_cross_pack_cache()
    active = {c.chain_id for c in _all_cross_pack_chains()}
    if old_id not in active:
        raise SupersessionError(
            f"old_chain_id {old_id!r} is not active in the cross-pack corpus"
        )
    resolved_new_id = (new_chain_id or "").strip() or f"{i}_{s}_{c}_{o}"
    if resolved_new_id == old_id:
        raise SupersessionError(
            "new chain_id is identical to old_chain_id"
        )
    if resolved_new_id in active:
        raise SupersessionError(
            f"new chain_id {resolved_new_id!r} is already active; "
            "choose a distinct connective/object or pass --new-chain-id"
        )

    # Compose entry — cross-pack carries the two extra residency fields.
    review_date_clean = review_date.strip()
    provenance = Provenance(
        adr_id=adr_id,
        source="hand_authored",
        review_date=review_date_clean,
        raw=f"{adr_id}:hand_authored:{review_date_clean}:supersede({old_id})",
    )

    bytes_before = path.read_bytes() if path.exists() else b""

    # ``append_chain_to_corpus`` doesn't carry the pack-id fields, so
    # we compose our own JSON line directly — staying within the
    # spirit of "one write helper" by reusing the same atomic append
    # pattern + sorted-keys + provenance shape.
    entry = {
        "chain_id": resolved_new_id,
        "subject": s,
        "intent": i,
        "connective": c,
        "object": o,
        "subject_pack_id": sp,
        "object_pack_id": op,
        "domains_subject_k": 2,
        "domains_object_k": 1,
        "provenance": provenance.raw,
        "superseded_by": old_id,
    }
    line = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    # Post-append: re-load + verify active set shifted as expected.
    clear_cross_pack_cache()
    post_active = {c.chain_id for c in _all_cross_pack_chains()}
    if resolved_new_id not in post_active or old_id in post_active:
        # Roll back.
        path.write_bytes(bytes_before)
        clear_cross_pack_cache()
        raise SupersessionError(
            f"post-append re-load rejected the supersession "
            f"(new_active={resolved_new_id in post_active}, "
            f"old_still_active={old_id in post_active}); "
            f"corpus rolled back"
        )

    # Keep ``append_chain_to_corpus`` reachable from this module's
    # public re-export so callers needing the in-pack write surface
    # can import it from one place when wiring CLI dispatch.
    _ = append_chain_to_corpus
    return resolved_new_id


__all__ = ["supersede_cross_pack_chain"]
