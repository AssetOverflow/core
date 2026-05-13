"""
generate/render.py — Default TextRenderer (ADR-0011)

The renderer is the last thing that happens before output leaves the system.
Nothing after the renderer touches the field.

Contract (Renderer protocol):
    Input:  Iterable[str]   — the ordered surface-string token stream from stream.py
    Output: str             — the realized surface text
    Stateless:              — holds no field state, modifies nothing
    Deterministic:          — identical token sequences produce identical output

Modality-specific renderers (markdown, Hebrew RTL, Koine Greek polytonic,
audio phoneme stream) implement the same Renderer protocol and are provided
by the caller. The engine never selects a renderer.

Design note:
    stream.py yields word strings — the .surface form resolved by vocab.nearest().
    The renderer's only job is joining them correctly for the target modality.
    Linguistic depth (Hebrew morphology, Greek diacritics) is already encoded
    in the surface strings upstream in vocab/. The renderer transcribes; it
    does not interpret.
"""

from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable


@runtime_checkable
class Renderer(Protocol):
    """
    Protocol for all surface renderers.

    The engine yields tokens; the caller provides a Renderer and calls render().
    The engine has no concept of deployment context.
    """

    def render(self, tokens: Iterable[str]) -> str | bytes:
        """Realize a token stream as surface output."""
        ...


class TextRenderer:
    """
    Default renderer: joins tokens into a UTF-8 string.

    Separator logic:
        - Tokens that begin with standard punctuation (.,;:!?'\')
          are attached to the preceding token without a space.
        - All other tokens are separated by a single space.
        - Leading and trailing whitespace is stripped.

    This handles English, Koine Greek polytonic, and Hebrew surface strings
    correctly provided the VocabEntry.surface fields are well-formed upstream.
    Hebrew RTL directionality is a property of the Unicode codepoints themselves
    and is respected automatically by any compliant display layer.
    """

    # Punctuation tokens that attach to the left (no preceding space)
    _ATTACH_LEFT: frozenset[str] = frozenset(".,;:!?'\")-]}’”;·")

    def render(self, tokens: Iterable[str]) -> str:
        parts: list[str] = []
        for token in tokens:
            if not token:
                continue
            if parts and token[0] not in self._ATTACH_LEFT:
                parts.append(" ")
            parts.append(token)
        return "".join(parts).strip()


class MarkdownRenderer:
    """
    Renderer for markdown surface output.

    Identical join logic to TextRenderer. Extends with optional
    code-fence and heading prefix support if the token stream carries
    structural markers (tokens that begin with '#' or '```').

    This is a thin wrapper — it does not parse or validate markdown.
    It writes what the field produced.
    """

    _text = TextRenderer()

    def render(self, tokens: Iterable[str]) -> str:
        return self._text.render(tokens)


# Module-level default — usable directly without instantiation
default_renderer = TextRenderer()


def render(tokens: Iterable[str], renderer: Renderer | None = None) -> str:
    """
    Convenience function: render a token stream using the provided renderer.
    Falls back to the default TextRenderer if none is given.

    Usage:
        from generate.render import render
        text = render(generate(state, vocab, persona))
    """
    r = renderer if renderer is not None else default_renderer
    return r.render(tokens)
