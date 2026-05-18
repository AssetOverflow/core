"""ADR-0036 — typed refusal surface for runtime-checkable safety violations.

The refusal surface is the runtime's response to a SafetyVerdict that
reports at least one ``runtime_checkable=True, upheld=False`` result.
It is deliberately:

* **Deterministic.** Same set of violated boundaries → same surface
  bytes.  Replayability is preserved.
* **Typed.** A constant prefix (``TYPED_REFUSAL_PREFIX``) plus
  lex-ordered boundary ids.  Audit consumers detect refusals by prefix,
  not by NLP.
* **Safety-only.** Ethics violations are observational at v1
  (ADR-0035) and do not trigger refusal.  Refusing on swappable
  deployment commitments would let pack-swappers silently change
  refusal behavior — the wrong coupling.

See `docs/decisions/ADR-0036-safety-refusal-policy.md`.
"""

from __future__ import annotations

from typing import Iterable

TYPED_REFUSAL_PREFIX = "I cannot proceed — safety boundary violated: "


def violated_runtime_checkable(verdict) -> tuple[str, ...]:
    """Return the lex-sorted tuple of runtime-checkable violated boundary ids.

    A boundary is reported as violated only when the predicate had
    enough evidence to make a real claim (``runtime_checkable=True``)
    AND determined the turn breached the boundary (``upheld=False``).
    Predicates that report ``runtime_checkable=False`` are honest
    about lack of evidence and never trigger refusal.
    """
    if verdict is None:
        return ()
    boundary_ids: list[str] = []
    for result in getattr(verdict, "results", ()) or ():
        if getattr(result, "runtime_checkable", False) and not getattr(
            result, "upheld", True
        ):
            boundary_ids.append(str(result.boundary_id))
    return tuple(sorted(boundary_ids))


def build_refusal_surface(verdict) -> str | None:
    """Build a deterministic typed refusal surface, or ``None`` if no refusal.

    The contract:

    * Returns ``None`` when no runtime-checkable safety violation is
      present.  The caller keeps the originally-articulated surface.
    * Returns ``TYPED_REFUSAL_PREFIX + ", ".join(lex_sorted_ids)`` when
      one or more runtime-checkable boundaries were violated.

    The same verdict always produces the same string.
    """
    violated = violated_runtime_checkable(verdict)
    if not violated:
        return None
    return _format_refusal(violated)


def _format_refusal(boundary_ids: Iterable[str]) -> str:
    return TYPED_REFUSAL_PREFIX + ", ".join(boundary_ids)


def is_typed_refusal(surface: str) -> bool:
    """Audit helper: does this surface look like a typed refusal?"""
    return bool(surface) and surface.startswith(TYPED_REFUSAL_PREFIX)
