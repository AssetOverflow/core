"""Centralised safe-display sanitiser for user-controlled text.

Many surfaces in CORE need to echo a user-controlled fragment into an error
message, log line, or report (e.g. an out-of-vocabulary token, an unknown
pack id, a refused identity-override attempt).  Doing this naively lets a
caller inject ANSI control sequences, newlines that break log parsers,
null bytes, or arbitrarily long strings that obscure surrounding evidence.

This module exposes a single helper, :func:`safe_display`, which all such
sites should route user-controlled text through *before* it is concatenated
into an error string or written to a log sink.

Doctrine alignment
------------------
- This file is the canonical *sanitiser*, not a normaliser.  It belongs to
  the logging/display trust boundary, not to the algebra or generation
  paths.  It must never be imported by ``algebra/``, ``generate/``,
  ``field/``, or ``vault/`` runtime code paths.
- The transformation is **deterministic**: identical input produces
  identical output.  No randomness, no clock, no environment.
- The transformation is **lossy on purpose**: it is a display helper, not
  a round-trip codec.  Callers must not rely on being able to recover the
  original token from the sanitised form.

ADR: ADR-0051 (trust-boundary hardening pass).
"""

from __future__ import annotations

# A conservative cap.  Long enough to retain useful evidence (e.g. a short
# OOV token, an unknown pack id), short enough that a maliciously long
# user-controlled string cannot push surrounding context off a log line.
_DEFAULT_MAX_LEN = 64

# Sentinel used when the input is None or empty.  Keeps log lines parseable
# and avoids the surface "..." which is reserved for truncation.
_EMPTY_MARK = "<empty>"


def safe_display(value: object, *, max_len: int = _DEFAULT_MAX_LEN) -> str:
    """Return a log/error-safe rendering of a user-controlled fragment.

    Rules applied in order:

    1. ``None`` and empty strings collapse to the sentinel ``"<empty>"``.
    2. Non-strings are coerced via :class:`repr` so callers cannot smuggle
       a custom ``__str__`` into a log line.
    3. Control characters (``\\x00``-``\\x1f`` plus DEL, plus the C1 range
       ``\\x80``-``\\x9f``) are replaced with the literal ``"?"``.  This
       neutralises ANSI escape sequences (which require ``\\x1b``) and
       embedded newlines / carriage returns that would break log parsers.
    4. The result is truncated to ``max_len`` characters; truncation is
       signalled by a trailing ``"..."``.

    The function is intentionally simple, pure, and easy to audit.
    """
    if value is None:
        return _EMPTY_MARK
    if isinstance(value, str):
        text = value
    else:
        text = repr(value)
    if text == "":
        return _EMPTY_MARK

    cleaned_chars: list[str] = []
    for ch in text:
        code = ord(ch)
        if code < 0x20 or code == 0x7F or 0x80 <= code <= 0x9F:
            cleaned_chars.append("?")
        else:
            cleaned_chars.append(ch)
    cleaned = "".join(cleaned_chars)

    if max_len <= 0:
        return ""
    if len(cleaned) > max_len:
        # Reserve room for the "..." truncation marker.
        keep = max(1, max_len - 3)
        cleaned = cleaned[:keep] + "..."
    return cleaned


def safe_pack_id(value: object) -> str:
    """Sanitise a pack-id-shaped fragment for error messages.

    Pack ids are a narrower display category than free text: callers
    typically only want to see ASCII letters, digits, hyphens, and
    underscores.  Anything outside that set is replaced with ``"?"`` and
    the result is truncated to a conservative 48 characters.

    This helper does NOT validate the pack id for filesystem use — that is
    the job of the loader's own ``_find_pack`` / ``_safe_pack_id`` guard.
    """
    if value is None:
        return _EMPTY_MARK
    text = value if isinstance(value, str) else repr(value)
    if text == "":
        return _EMPTY_MARK
    cleaned = "".join(
        ch if (ch.isascii() and (ch.isalnum() or ch in {"-", "_", "."})) else "?"
        for ch in text
    )
    if len(cleaned) > 48:
        cleaned = cleaned[:45] + "..."
    return cleaned


__all__ = ("safe_display", "safe_pack_id")
