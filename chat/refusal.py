"""ADR-0036 + ADR-0037 — typed refusal surface.

ADR-0036 introduced typed refusal driven by safety violations only.
ADR-0037 extends the trigger surface to ethics commitments that the
pack explicitly opts into via ``EthicsPack.refusal_commitments`` —
keeping the default audit-only stance and forcing pack authors to opt
specific commitments into refusal one at a time.

The refusal surface remains:

* **Deterministic.** Same set of violated boundary/commitment ids →
  same surface bytes.  Replayability is preserved.
* **Typed.** A constant prefix (``TYPED_REFUSAL_PREFIX``) plus
  source-tagged, lex-ordered ids (``safety:<id>`` /
  ``ethics:<id>``).  Audit consumers detect refusals by prefix and
  disambiguate source by tag — not by NLP.
* **Predicate-evidenced.** Only ``runtime_checkable=True, upheld=False``
  results contribute.  No-evidence predicates never refuse.
* **Opt-in for ethics.** Ethics commitments must appear in
  ``refusal_commitments`` to count.  Safety is always in scope; the
  pack-layer doctrine in ADR-0029 prohibits opting safety out.

See `docs/decisions/ADR-0036-safety-refusal-policy.md` and
`docs/decisions/ADR-0037-per-predicate-ethics-refusal.md`.
"""

from __future__ import annotations

from typing import Iterable

TYPED_REFUSAL_PREFIX = "I cannot proceed — boundary violated: "
_SAFETY_TAG = "safety:"
_ETHICS_TAG = "ethics:"


def violated_runtime_checkable(verdict) -> tuple[str, ...]:
    """Lex-sorted tuple of runtime-checkable violated boundary ids from a SafetyVerdict.

    Used by safety; safety is always in scope for refusal.
    """
    if verdict is None:
        return ()
    return tuple(sorted(_iter_violated_ids(verdict, attr="boundary_id")))


def violated_runtime_checkable_ethics(
    verdict, refusal_commitments: Iterable[str] | None,
) -> tuple[str, ...]:
    """Lex-sorted tuple of runtime-checkable violated commitment ids that opted into refusal.

    ADR-0037 — ethics commitments do NOT trigger refusal by default.
    A commitment must be present in the pack's ``refusal_commitments``
    set AND fail runtime-checkably for it to contribute.
    """
    if verdict is None:
        return ()
    opt_in: frozenset[str] = (
        frozenset(refusal_commitments) if refusal_commitments else frozenset()
    )
    if not opt_in:
        return ()
    return tuple(
        sorted(
            cid
            for cid in _iter_violated_ids(verdict, attr="commitment_id")
            if cid in opt_in
        )
    )


def build_refusal_surface(
    safety_verdict,
    ethics_verdict=None,
    ethics_pack=None,
) -> str | None:
    """Build a deterministic typed refusal surface, or ``None`` if no refusal.

    Contract:

    * Returns ``None`` when no runtime-checkable violation is in scope.
    * Returns ``TYPED_REFUSAL_PREFIX`` followed by a comma-joined,
      lex-sorted list of source-tagged ids
      (``safety:<id>`` / ``ethics:<id>``).
    * Ethics ids are included only when present in
      ``ethics_pack.refusal_commitments`` (ADR-0037).
    * Same verdict + pack → byte-identical surface.

    The historical (ADR-0036) single-argument call
    ``build_refusal_surface(safety_verdict)`` remains valid: with no
    ethics pack supplied, ethics contributes nothing.
    """
    safety_ids = violated_runtime_checkable(safety_verdict)
    ethics_ids = violated_runtime_checkable_ethics(
        ethics_verdict,
        getattr(ethics_pack, "refusal_commitments", None),
    )
    if not safety_ids and not ethics_ids:
        return None
    tagged = [f"{_SAFETY_TAG}{s}" for s in safety_ids] + [
        f"{_ETHICS_TAG}{e}" for e in ethics_ids
    ]
    return _format_refusal(sorted(tagged))


def _iter_violated_ids(verdict, *, attr: str) -> Iterable[str]:
    for result in getattr(verdict, "results", ()) or ():
        if getattr(result, "runtime_checkable", False) and not getattr(
            result, "upheld", True
        ):
            yield str(getattr(result, attr))


def _format_refusal(tagged_ids: Iterable[str]) -> str:
    return TYPED_REFUSAL_PREFIX + ", ".join(tagged_ids)


def is_typed_refusal(surface: str) -> bool:
    """Audit helper: does this surface look like a typed refusal?"""
    return bool(surface) and surface.startswith(TYPED_REFUSAL_PREFIX)


# ---------- ADR-0038 — hedge injection ----------


def should_inject_hedge(ethics_verdict, ethics_pack) -> bool:
    """ADR-0038 — does the pack want a hedge prepended this turn?

    True iff a commitment in ``ethics_pack.hedge_commitments`` fired
    with ``runtime_checkable=True, upheld=False``.  Mutually
    exclusive with refusal at the pack-schema level (validated at
    load time): a commitment cannot be in both
    ``refusal_commitments`` and ``hedge_commitments``.
    """
    if ethics_verdict is None or ethics_pack is None:
        return False
    opt_in = getattr(ethics_pack, "hedge_commitments", None)
    if not opt_in:
        return False
    opt_in = frozenset(opt_in)
    for cid in _iter_violated_ids(ethics_verdict, attr="commitment_id"):
        if cid in opt_in:
            return True
    return False


def build_hedge_prefix(identity_manifold) -> str:
    """Return the manifold's preferred hedge phrase, or empty string.

    Prefers ``preferred_hedge_soft`` (the lighter touch) over
    ``preferred_hedge_strong``.  Empty string when no hedges are
    configured — the runtime then skips injection because there is
    nothing to inject.
    """
    prefs = getattr(identity_manifold, "surface_preferences", None)
    if prefs is None:
        return ""
    soft = getattr(prefs, "preferred_hedge_soft", "") or ""
    if soft:
        return soft
    return getattr(prefs, "preferred_hedge_strong", "") or ""


def inject_hedge(surface: str, hedge_prefix: str) -> str:
    """Prepend ``hedge_prefix`` to ``surface`` with a single space.

    Deterministic and idempotent-on-prefix: if ``surface`` already
    begins with the hedge phrase (case-insensitive), do nothing.
    Preserves the runtime's "evidence preservation" discipline at
    the caller level — only the user-facing ``ChatResponse.surface``
    is mutated; ``walk_surface`` and ``articulation_surface`` remain
    untouched.
    """
    if not hedge_prefix or not surface:
        return surface
    if surface.casefold().startswith(hedge_prefix.casefold()):
        return surface
    return f"{hedge_prefix} {surface}"
