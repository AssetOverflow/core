"""Seeded surface variation (ADR-0071 R4, extended ADR-0072 R5).

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

ADR-0072 (R5) — :func:`decorate_surface` now returns a
:class:`DecorationResult` that carries the post-decoration surface plus
the chosen ``opening`` / ``closing`` strings and a 12-char
``variant_id`` digest of the selected pair.  This is what
``TurnEvent`` records into the audit stream so operators can ask
"which register variant fired on turn N?" without reading content.
The legacy string-return is preserved via :func:`decorate_surface_str`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from packs.register.loader import RegisterPack


_VARIANT_ID_LEN = 12


@dataclass(frozen=True, slots=True)
class DecorationResult:
    """Result of one seeded discourse-marker decoration.

    ``variant_id`` is the 12-char SHA-256 prefix of
    ``f"{opening}|{closing}"``.  Empty string ⇒ no decoration was
    applied this turn (empty buckets, or empty input surface).  Two
    different turns under the same register that select the same
    ``(opening, closing)`` pair share the same ``variant_id``.
    """

    surface: str
    opening: str
    closing: str
    variant_id: str


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


def _compute_variant_id(opening: str, closing: str) -> str:
    """12-char SHA-256 prefix of the chosen ``(opening, closing)`` pair.

    Empty when both markers are empty — ``""`` is the "no decoration
    applied" sentinel, so ``UNREGISTERED`` / ``default_neutral_v1`` /
    ``terse_v1`` do not pollute the audit stream with a no-op digest.
    """
    if not opening and not closing:
        return ""
    payload = f"{opening}|{closing}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:_VARIANT_ID_LEN]


def decorate_surface(
    surface: str,
    register: RegisterPack,
    *,
    turn_idx: int,
    seed_text: str | None = None,
) -> DecorationResult:
    """Apply seeded discourse-marker decoration to *surface*.

    Returns a :class:`DecorationResult` with the post-decoration
    ``surface`` plus the chosen ``opening`` / ``closing`` markers and
    the 12-char ``variant_id`` digest of that pair.

    Empty buckets ⇒ no-op (the original surface is returned, both
    marker strings empty, ``variant_id=""``).  Order is
    ``"{opening} {surface}{closing}"`` — closing concatenates directly
    so an entry like ``" — make sense?"`` carries its own spacing.
    Empty-string entries in a bucket count as legitimate selections
    (the seed may pick "no marker this turn").

    ``seed_text`` defaults to *surface* — the pre-decoration string is
    the natural seed.  Callers with a stronger deterministic key (e.g.
    a turn-trace hash) may pass it explicitly.

    Transitions are accepted by the schema but NOT consumed at R4;
    they sit until a later phase that owns clause-boundary detection.
    """
    if not surface:
        return DecorationResult(
            surface=surface, opening="", closing="", variant_id=""
        )
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
    return DecorationResult(
        surface=out,
        opening=opening,
        closing=closing,
        variant_id=_compute_variant_id(opening, closing),
    )


def decorate_surface_str(
    surface: str,
    register: RegisterPack,
    *,
    turn_idx: int,
    seed_text: str | None = None,
) -> str:
    """String-only convenience wrapper around :func:`decorate_surface`.

    Preserves the pre-R5 return type for off-runtime callers (tests,
    ad-hoc CLI tools) that only want the post-decoration string.
    """
    return decorate_surface(
        surface, register, turn_idx=turn_idx, seed_text=seed_text
    ).surface


__all__ = ("DecorationResult", "decorate_surface", "decorate_surface_str")
