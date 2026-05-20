"""ADR-0077 (R6) — substantive register transforms.

Pure, deterministic post-composer transforms keyed by boolean
``realizer_overrides`` entries on the active register pack.  Sibling to
``chat/register_variation.py`` (which owns R4 seeded marker decoration).

Doctrine
--------

This module is the **substantive register axis**: it operates on the
``register_canonical_surface`` produced by the composer and emits the
``pre_decoration_surface`` consumed by the seeded-marker decorator.

The pipeline hashes ``register_canonical_surface`` (not the post-R6
output) for ``trace_hash``, preserving R5's load-bearing invariant —
the register axis must not move ``trace_hash``.  R6 transforms are
therefore visible to the user-facing surface but invisible to the
truth-path identity field.

Each transform is a pure function of ``(string, register_pack, optional
lemma/semantic_domains)``.  No I/O, no mutation, no globals beyond
module-level closed regex sets.

Knobs
-----

* ``drop_provenance_tag``     (terse) — strip the trailing
  ``" pack-grounded (<id>)."`` clause from DEFINITION/RECALL gloss
  surfaces, and the ``" — pack-grounded (<id>)"`` infix from the
  dotted-disclosure and comparison surfaces.  Lens annotations are
  preserved by remaining in place; only the provenance tag goes.
* ``compress_gloss``          (terse) — rewrite the first
  ``" is a / is an / is the / is "`` of the canonical surface to
  ``": "``, collapsing the "X is a {gloss}." opener into "X: {gloss}.".
* ``drop_articles``           (terse) — remove standalone mid-sentence
  ``a / an / the`` articles whose previous token is not ``not``.
  Safe against C1 R2/R3 because the canonical DEFINITION/RECALL
  surface is affirmative (contains no ``do/does/did not`` or
  ``is/are/was/were not`` segments).
* ``append_semantic_domain_clause`` (convivial) — append a single
  bounded ``" Related: {atom}."`` clause selecting the lexicographically-
  first ``semantic_domains`` atom not already mentioned in the
  canonical surface.  No-op when no atoms are supplied.

All knobs default ``False`` (the ``overrides.get(...)`` lookup returns
``None`` → falsy), so any register without the key — including the
unregistered sentinel and ``default_neutral_v1`` — is byte-identical
to its pre-R6 behavior.
"""

from __future__ import annotations

import re
from typing import Mapping

from packs.register.loader import RegisterPack


# ---------- Compiled patterns ----------


# Trailing provenance, e.g. " pack-grounded (en_core_cognition_v1)."
# Optionally preceded by a comparison em-dash (" — pack-grounded (...) ")
# inside the disclosure/comparison surfaces.  Captures up to (but not
# including) any lens annotation that may follow.
_PROVENANCE_TRAILING_RE = re.compile(
    r"\s+pack-grounded \([^)]+\)\s*(\[lens[^\]]+\])?\s*\.\s*\Z"
)
"""Strip-trailing pattern.  Anchored at end-of-surface (``\\Z``) to
distinguish the gloss DEFINITION form (provenance is the final
sentence) from the dotted-disclosure / comparison forms (provenance
appears mid-surface and ``trailing`` would mismatch).  The replacement
preserves any lens annotation by stitching it back in (see
:func:`_drop_provenance_tag`)."""

_PROVENANCE_INFIX_RE = re.compile(
    r"\s+—\s+pack-grounded \([^)]+\)"
)
"""Strip-infix pattern.  The comparison and disclosure surfaces emit
``... — pack-grounded (<id>): ...`` mid-string; this drops the em-dash
plus provenance phrase, leaving the surrounding content intact."""

_ARTICLE_RE = re.compile(
    r"(?<!\bnot )(?<=\s)(?:a|an|the)(?=\s)",
    re.IGNORECASE,
)
"""Drop-articles pattern.

* Lookbehind ``(?<!\\bnot )`` refuses to match an article whose
  previous word is ``not`` — preserves C1 R3 safety in the rare event
  the canonical surface ever contains ``"is not a/an/the X"``.
* Lookbehind ``(?<=\\s)`` requires a preceding space, refusing to
  match an article at the very start of the string.
* Lookahead ``(?=\\s)`` requires a following space, refusing to match
  a token that ends in ``a / an / the`` (e.g. ``schema``).
"""

# Tokens whose presence in a compress_gloss match would be ambiguous; we
# only collapse the FIRST occurrence and only when the predicate opens
# the surface (handled by `count=1` in re.sub).
_GLOSS_OPENER_PATTERNS: tuple[str, ...] = (
    " is a ", " is an ", " is the ", " is ",
)


# ---------- Transforms ----------


def _drop_provenance_tag(surface: str) -> str:
    """Strip the pack-grounded provenance from *surface*.

    Two patterns are tried in order:
      1. trailing  — ``" pack-grounded (<id>)."`` (optionally followed
         by a lens annotation) at sentence end.
      2. infix     — ``" — pack-grounded (<id>)"`` mid-string.

    Lens annotations remain on the surface — the lens axis is
    orthogonal to the register axis (ADR-0073d).  The trailing pattern
    captures the lens annotation in group 1 and re-emits it before the
    closing period if present.
    """

    def _trailing_repl(match: re.Match[str]) -> str:
        # The canonical gloss surface is ``"<gloss>. pack-grounded (<id>)."``;
        # the matched span is the trailing ``" pack-grounded (<id>)."``
        # (plus optional lens annotation).  The gloss sentence already
        # ends in its own ``.`` before the matched leading space, so
        # the replacement removes the entire match without re-adding
        # any punctuation.  Lens annotation, when present, is re-emitted
        # between the gloss period and the new end-of-string with its
        # own terminal period.
        lens = match.group(1)
        if lens:
            return f" {lens}."
        return ""

    out = _PROVENANCE_TRAILING_RE.sub(_trailing_repl, surface, count=1)
    if out != surface:
        return out
    return _PROVENANCE_INFIX_RE.sub("", surface, count=1)


def _compress_gloss(surface: str) -> str:
    """Replace the first ``" is a / is an / is the / is "`` with ``": "``.

    Only the first occurrence is replaced (``count=1``) to scope the
    rewrite to the opening DEFINITION gloss frame.  Compressing later
    ``is`` tokens would risk mangling unrelated relative clauses.
    """
    for pat in _GLOSS_OPENER_PATTERNS:
        if pat in surface:
            return surface.replace(pat, ": ", 1)
    return surface


def _drop_articles(surface: str) -> str:
    """Drop mid-sentence ``a / an / the`` articles.

    Implemented as a single :data:`_ARTICLE_RE` substitution; the
    regex's lookbehinds and lookaheads enforce all positional
    constraints.  Adjacent double spaces produced by removal are
    collapsed by the trailing whitespace pass.
    """
    out = _ARTICLE_RE.sub("", surface)
    # Collapse the double-space artifacts the article removal leaves
    # behind, but preserve newlines and other whitespace shape.
    out = re.sub(r" {2,}", " ", out)
    return out


def _append_semantic_domain_clause(
    surface: str, semantic_domains: tuple[str, ...],
) -> str:
    """Append ``" Related: <atom>."`` for the first lex-sorted atom not
    already mentioned in *surface*.

    Selection is deterministic — atoms are sorted lexicographically and
    the first whose lowercased form does not appear as a substring of
    the lowercased surface is chosen.  No-op when no atoms remain or
    none are supplied.
    """
    if not semantic_domains:
        return surface
    canon_lower = surface.lower()
    for atom in sorted(semantic_domains):
        if not atom:
            continue
        if atom.lower() not in canon_lower:
            return f"{surface} Related: {atom}."
    return surface


# ---------- Public entrypoint ----------


def apply_substantive_register(
    canonical: str,
    register: RegisterPack,
    *,
    semantic_domains: tuple[str, ...] = (),
) -> str:
    """Apply R6 substantive transforms to a canonical composer surface.

    Args:
        canonical: The composer's pre-substantive surface (what the
            pipeline hashes for ``trace_hash``).
        register: Active :class:`RegisterPack`.  When ``None`` keys
            are present in ``realizer_overrides``, the corresponding
            transform is skipped — the no-op contract.
        semantic_domains: Optional tuple of atoms used by
            ``append_semantic_domain_clause`` (convivial).  Other
            transforms ignore this argument.  Passing an empty tuple
            disables the append even when the knob is True.

    Returns:
        The post-substantive surface.  When every knob is falsy, the
        return value is byte-identical to *canonical*.

    Order of transforms (intentional):

      1. ``compress_gloss``     — must run before provenance drop so
         the ``" is a "`` opener can still be found within the
         canonical sentence frame.
      2. ``drop_provenance_tag``— removes the tail clause.
      3. ``drop_articles``      — operates on the remaining surface.
      4. ``append_semantic_domain_clause`` — final, after everything
         else has settled.
    """
    if not canonical:
        return canonical
    overrides: Mapping[str, object] = register.realizer_overrides
    out = canonical
    if overrides.get("compress_gloss"):
        out = _compress_gloss(out)
    if overrides.get("drop_provenance_tag"):
        out = _drop_provenance_tag(out)
    if overrides.get("drop_articles"):
        out = _drop_articles(out)
    if overrides.get("append_semantic_domain_clause"):
        out = _append_semantic_domain_clause(out, semantic_domains)
    return out


__all__ = ("apply_substantive_register",)
