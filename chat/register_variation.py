"""Seeded surface variation (ADR-0071, Plan Phase R4).

Deterministic discourse-marker selection from bounded register-pack
buckets, keyed on ``(seed_text, register_id, turn_idx, bucket_name)``.

The ADR specifies ``trace_hash`` as the primary seed input.  The
implementation passes the *pre-decoration surface* as ``seed_text``
instead, for pragmatic reasons:

* The pre-decoration surface is a deterministic downstream projection
  of the truth path (intent → proposition graph → realizer → surface).
* It is already available at the decoration call site without
  threading ``trace_hash`` through ``TurnEvent`` / ``ChatResponse``.
* There is no cycle: decoration reads the pre-decoration string and
  writes a post-decoration string; the seed never sees its own output.
* Replay equivalence holds: same input sequence ⇒ same pre-decoration
  surfaces ⇒ same decoration choices.

Trust boundary
--------------
This module READS surface text to seed marker selection.  It MUST NOT
feed back into the truth path (intent / proposition graph / trace
hash).  ADR-0069 invariant C and ADR-0070
``register_invariant_grounding`` continue to hold; the seam test
(``tests/test_register_pack_seam.py``) keeps truth-path modules free of
imports from ``packs.register`` and from this module.

The selector is uniform-mod-len: every entry in a bucket is equally
likely across the seed space.  Frequency shaping (weighted entries) is
deferred per ADR-0071 §Open questions.
"""

from __future__ import annotations

import hashlib

from packs.register.loader import RegisterPack


def _select_bucket_entry(
    bucket: tuple[str, ...],
    *,
    seed_text: str,
    register_id: str,
    turn_idx: int,
    bucket_name: str,
) -> str:
    """Deterministically select one entry from *bucket*, or ``''``.

    Same inputs ⇒ same output, forever.  Different ``turn_idx`` against
    the same seed_text + register typically picks a different entry
    (uniform across the seed space).
    """
    if not bucket:
        return ""
    seed_bytes = (
        f"{seed_text}|{register_id}|{turn_idx}|{bucket_name}"
    ).encode("utf-8")
    digest = hashlib.sha256(seed_bytes).digest()
    idx = int.from_bytes(digest[:8], "big") % len(bucket)
    return bucket[idx]


def decorate_surface(
    surface: str,
    register: RegisterPack,
    *,
    turn_idx: int,
    seed_text: str | None = None,
) -> str:
    """Apply seeded discourse-marker decoration to *surface*.

    Empty buckets ⇒ no-op (the original surface is returned).  Order
    is ``"{opening} {surface}{closing}"`` — closing concatenates
    directly so an entry like ``" — make sense?"`` carries its own
    spacing.  Empty-string entries in a bucket count as legitimate
    selections (the seed may pick "no marker this turn").

    ``seed_text`` defaults to *surface* — the pre-decoration string is
    the natural seed.  Callers with a stronger deterministic key (e.g.
    a turn-trace hash) may pass it explicitly.

    Transitions are accepted by the schema but NOT consumed at R4;
    they sit until a later phase that owns clause-boundary detection.
    """
    if not surface:
        return surface
    if seed_text is None:
        seed_text = surface
    markers = register.discourse_markers
    opening = _select_bucket_entry(
        markers.openings,
        seed_text=seed_text,
        register_id=register.register_id,
        turn_idx=turn_idx,
        bucket_name="openings",
    )
    closing = _select_bucket_entry(
        markers.closings,
        seed_text=seed_text,
        register_id=register.register_id,
        turn_idx=turn_idx,
        bucket_name="closings",
    )
    out = surface
    if opening:
        out = f"{opening} {out}"
    if closing:
        out = f"{out}{closing}"
    return out


__all__ = ("decorate_surface",)
